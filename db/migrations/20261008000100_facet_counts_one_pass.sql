-- migrate:up
-- facet_counts numa passada (decisão 0016; prevista na decisão 0002): as linhas que atendem a todos
-- os filtros são materializadas uma vez, e cada faceta cujo filtro não está ativo é contada sobre
-- elas. Só as facetas com filtro ativo (contagem disjuntiva) leem as tabelas de novo.
set local search_path = public, ext;

-- Agregação de uma faceta sobre `rel`, que tem as colunas de facet_columns(). Agrega pelos ids e
-- só depois junta os nomes, nas poucas linhas do resultado.
create function facet_sql(facet text, rel text) returns text
language sql immutable set search_path = public, ext, pg_temp as $$
  select case facet
    when 'exam_board' then format($q$
      select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.slug), '[]') from (
        select b.slug, b.name, b.short_name, n.count
          from (select exam_board_id, count(*) as count from %s group by 1) n
          join exam_board b on b.id = n.exam_board_id) x$q$, rel)
    when 'agency' then format($q$
      select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.slug), '[]') from (
        select a.slug, a.name, a.short_name, n.count
          from (select agency_id, count(*) as count from %s group by 1) n
          join agency a on a.id = n.agency_id) x$q$, rel)
    when 'career' then format($q$
      select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.value), '[]') from (
        select a.career::text as value, sum(n.count)::bigint as count
          from (select agency_id, count(*) as count from %s group by 1) n
          join agency a on a.id = n.agency_id
         group by 1) x$q$, rel)
    -- Conta por prova primeiro: numa prova cada slug de cargo aparece uma vez só.
    when 'position' then format($q$
      select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.slug), '[]') from (
        select po.slug, min(po.name) as name, sum(per_exam.n)::bigint as count
          from (select exam_id, count(*) as n from %s group by exam_id) per_exam
          join exam_position ep on ep.exam_id = per_exam.exam_id
          join position po on po.id = ep.position_id
         group by po.slug) x$q$, rel)
    when 'year' then format($q$
      select coalesce(jsonb_agg(to_jsonb(x) order by x.value desc), '[]') from (
        select year as value, count(*) as count from %s group by 1) x$q$, rel)
    when 'subject' then format($q$
      select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.slug), '[]') from (
        select s.slug, s.name, n.count
          from (select subject_id, count(*) as count from %s group by 1) n
          join subject s on s.id = n.subject_id) x$q$, rel)
    when 'topic' then format($q$
      select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.path), '[]') from (
        select anc.path::text as path, anc.name, n.count
          from (select pair.ancestor_id, count(*) as count
                  from (select distinct qt.question_id, ta.ancestor_id
                          from %s r
                          join question_topic qt on qt.question_id = r.id
                          join topic_ancestor ta on ta.topic_id = qt.topic_id) pair
                 group by 1) n
          join topic anc on anc.id = n.ancestor_id) x$q$, rel)
    when 'type' then format($q$
      select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.value), '[]') from (
        select type::text as value, count(*) as count from %s group by 1) x$q$, rel)
  end
$$;

create function facet_columns() returns text
language sql immutable set search_path = public, ext, pg_temp as $$
  select 'q.id, q.exam_id, c.exam_board_id, c.agency_id, c.year, q.subject_id, q.type'
$$;

create or replace function api.facet_counts(filters jsonb default '{}', query text default null)
returns jsonb
language plpgsql stable security definer set search_path = public, ext, pg_temp as $$
declare
  facets constant text[] :=
    array['exam_board', 'agency', 'career', 'position', 'year', 'subject', 'topic', 'type'];
  ctes text[];
  parts text[] := array['''total'', (select count(*) from base)'];
  k text;
  rel text;
  active boolean;
  result jsonb;
begin
  -- search_condition valida os filtros (e levanta erro) antes de qualquer outra coisa.
  ctes := array[format('base as materialized (select %s from %s where %s)',
                       facet_columns(), search_from(), search_condition(filters, query))];
  filters := coalesce(filters, '{}');
  foreach k in array facets loop
    if k = 'year' then
      active := filters ? 'year' and (filters -> 'year' ? 'from' or filters -> 'year' ? 'to');
    else
      active := filters ? k and jsonb_array_length(filters -> k) > 0;
    end if;
    rel := 'base';
    if active then
      rel := 'without_' || k;
      ctes := ctes || format('%s as (select %s from %s where %s)', rel, facet_columns(),
                             search_from(), search_condition(filters, query, k));
    end if;
    parts := parts || format('%L, (%s)', k, facet_sql(k, rel));
  end loop;
  execute format('with %s select jsonb_build_object(%s)',
                 array_to_string(ctes, ', '), array_to_string(parts, ', ')) into result;
  return result;
end
$$;

-- migrate:down
set local search_path = public, ext;

create or replace function api.facet_counts(filters jsonb default '{}', query text default null) returns jsonb
language plpgsql stable security definer set search_path = public, ext, pg_temp as $$
declare
  src constant text := search_from();
  result jsonb;
  facet jsonb;
  total bigint;
begin
  execute format('select count(*) from %s where %s', src, search_condition(filters, query)) into total;
  result := jsonb_build_object('total', total);

  execute format($q$
    select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.slug), '[]') from (
      select b.slug, b.name, b.short_name, count(*) as count from %s where %s
       group by b.slug, b.name, b.short_name) x$q$,
    src, search_condition(filters, query, 'exam_board')) into facet;
  result := result || jsonb_build_object('exam_board', facet);

  execute format($q$
    select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.slug), '[]') from (
      select a.slug, a.name, a.short_name, count(*) as count from %s where %s
       group by a.slug, a.name, a.short_name) x$q$,
    src, search_condition(filters, query, 'agency')) into facet;
  result := result || jsonb_build_object('agency', facet);

  execute format($q$
    select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.value), '[]') from (
      select a.career::text as value, count(*) as count from %s where %s group by 1) x$q$,
    src, search_condition(filters, query, 'career')) into facet;
  result := result || jsonb_build_object('career', facet);

  -- Conta por prova primeiro: numa prova cada slug de cargo aparece uma vez só.
  execute format($q$
    select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.slug), '[]') from (
      select po.slug, min(po.name) as name, sum(per_exam.n)::bigint as count
        from (select q.exam_id, count(*) as n from %s where %s group by q.exam_id) per_exam
        join exam_position ep on ep.exam_id = per_exam.exam_id
        join position po on po.id = ep.position_id
       group by po.slug) x$q$,
    src, search_condition(filters, query, 'position')) into facet;
  result := result || jsonb_build_object('position', facet);

  execute format($q$
    select coalesce(jsonb_agg(to_jsonb(x) order by x.value desc), '[]') from (
      select c.year as value, count(*) as count from %s where %s group by 1) x$q$,
    src, search_condition(filters, query, 'year')) into facet;
  result := result || jsonb_build_object('year', facet);

  execute format($q$
    select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.slug), '[]') from (
      select s.slug, s.name, count(*) as count from %s where %s group by s.slug, s.name) x$q$,
    src, search_condition(filters, query, 'subject')) into facet;
  result := result || jsonb_build_object('subject', facet);

  execute format($q$
    select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.path), '[]') from (
      select anc.path::text as path, anc.name, count(*) as count
        from (select distinct qt.question_id, ta.ancestor_id
                from %s
                join question_topic qt on qt.question_id = q.id
                join topic_ancestor ta on ta.topic_id = qt.topic_id
               where %s) pair
        join topic anc on anc.id = pair.ancestor_id
       group by anc.path, anc.name) x$q$,
    src, search_condition(filters, query, 'topic')) into facet;
  result := result || jsonb_build_object('topic', facet);

  execute format($q$
    select coalesce(jsonb_agg(to_jsonb(x) order by x.count desc, x.value), '[]') from (
      select q.type::text as value, count(*) as count from %s where %s group by 1) x$q$,
    src, search_condition(filters, query, 'type')) into facet;
  result := result || jsonb_build_object('type', facet);

  return result;
end
$$;

drop function facet_columns();
drop function facet_sql(text, text);
