-- migrate:up
set local search_path = public, ext;

create table setting (
  key   text primary key,
  value text not null
);
insert into setting (key, value) values ('asset_base_url', '/assets/');

-- Questões visíveis no site: publicadas, de prova publicada, que não são duplicata de outra.
create view published_question as
select q.*
  from question q
  join exam e on e.id = q.exam_id
 where q.publish_status = 'published'
   and e.publish_status = 'published'
   and q.duplicate_of is null;

------------------------------------------------------------------------------------------------
-- Views do contrato (docs/contract.md). Rodam com as permissões do dono; emmoni_web só lê.
------------------------------------------------------------------------------------------------

create view api.question as
select
  q.id,
  q.number,
  q.type::text           as type,
  q.statement_md,
  q.passage_id,
  p.body_md              as passage_md,
  coalesce((select jsonb_agg(jsonb_build_object('letter', o.letter, 'body_md', o.body_md)
                             order by o.letter)
              from question_option o where o.question_id = q.id), '[]') as options,
  q.answer_final         as answer,
  q.answer_preliminary,
  q.answer_status::text  as answer_status,
  b.slug                 as exam_board_slug,
  b.name                 as exam_board_name,
  b.short_name           as exam_board_short_name,
  a.slug                 as agency_slug,
  a.name                 as agency_name,
  a.short_name           as agency_short_name,
  a.career::text         as career,
  a.level::text          as government_level,
  a.state,
  c.slug                 as contest_slug,
  c.name                 as contest_name,
  c.year,
  e.slug                 as exam_slug,
  e.name                 as exam_name,
  e.applied_on,
  coalesce((select jsonb_agg(jsonb_build_object('slug', po.slug, 'name', po.name)
                             order by po.name)
              from exam_position ep join position po on po.id = ep.position_id
             where ep.exam_id = e.id), '[]') as positions,
  s.slug                 as subject_slug,
  s.name                 as subject_name,
  coalesce((select jsonb_agg(jsonb_build_object('path', t.path::text, 'name', t.name)
                             order by t.path)
              from question_topic qt join topic t on t.id = qt.topic_id
             where qt.question_id = q.id), '[]') as topics,
  coalesce((select jsonb_agg(jsonb_build_object(
                     'sha256', x.sha256,
                     'url', (select value from setting where key = 'asset_base_url') || x.storage_key,
                     'mime_type', x.mime_type,
                     'width', x.width,
                     'height', x.height,
                     'alt_text', x.alt_text) order by x.sha256)
              from asset x
             where x.id in (select qa.asset_id from question_asset qa where qa.question_id = q.id
                            union
                            select pa.asset_id from passage_asset pa where pa.passage_id = q.passage_id)),
           '[]') as assets,
  d.url                  as source_url,
  q.source_page
from published_question q
join exam e         on e.id = q.exam_id
join contest c      on c.id = e.contest_id
join agency a       on a.id = c.agency_id
join exam_board b   on b.id = c.exam_board_id
join subject s      on s.id = q.subject_id
left join passage p on p.id = q.passage_id
left join source_document d on d.id = e.exam_document_id;

create view api.passage as
select p.id,
       p.body_md,
       coalesce((select jsonb_agg(jsonb_build_object(
                          'sha256', x.sha256,
                          'url', (select value from setting where key = 'asset_base_url') || x.storage_key,
                          'mime_type', x.mime_type,
                          'width', x.width,
                          'height', x.height,
                          'alt_text', x.alt_text) order by x.sha256)
                   from passage_asset pa join asset x on x.id = pa.asset_id
                  where pa.passage_id = p.id), '[]') as assets
  from passage p
 where exists (select 1 from published_question q where q.passage_id = p.id);

create view api.exam_board as
select b.slug, b.name, b.short_name,
       (select count(*) from published_question q
          join exam e on e.id = q.exam_id
          join contest c on c.id = e.contest_id
         where c.exam_board_id = b.id) as question_count
  from exam_board b;

create view api.agency as
select a.slug, a.name, a.short_name, a.career::text as career, a.level::text as government_level,
       a.state,
       (select count(*) from published_question q
          join exam e on e.id = q.exam_id
          join contest c on c.id = e.contest_id
         where c.agency_id = a.id) as question_count
  from agency a;

create view api.position as
select a.slug as agency_slug, po.slug, po.name, po.education_level::text as education_level,
       (select count(*) from published_question q
          join exam_position ep on ep.exam_id = q.exam_id
         where ep.position_id = po.id) as question_count
  from position po
  join agency a on a.id = po.agency_id;

create view api.subject as
select s.slug, s.name,
       (select count(*) from published_question q where q.subject_id = s.id) as question_count
  from subject s;

create view api.topic as
select t.path::text as path,
       t.name,
       s.slug as subject_slug,
       nlevel(t.path) - 1 as depth,
       case when nlevel(t.path) > 2 then subpath(t.path, 0, nlevel(t.path) - 1)::text end as parent_path,
       (select count(distinct qt.question_id)
          from topic_ancestor ta
          join question_topic qt on qt.topic_id = ta.topic_id
          join published_question q on q.id = qt.question_id
         where ta.ancestor_id = t.id) as question_count
  from topic t
  join subject s on s.id = t.subject_id;

create view api.exam as
select c.slug  as contest_slug,
       c.name  as contest_name,
       c.year,
       c.notice_number,
       a.slug  as agency_slug,
       b.slug  as exam_board_slug,
       e.slug  as exam_slug,
       e.name  as exam_name,
       e.applied_on,
       coalesce((select jsonb_agg(jsonb_build_object('slug', po.slug, 'name', po.name)
                                  order by po.name)
                   from exam_position ep join position po on po.id = ep.position_id
                  where ep.exam_id = e.id), '[]') as positions,
       (select count(*) from published_question q where q.exam_id = e.id) as question_count,
       d.url   as source_url
  from exam e
  join contest c    on c.id = e.contest_id
  join agency a     on a.id = c.agency_id
  join exam_board b on b.id = c.exam_board_id
  left join source_document d on d.id = e.exam_document_id
 where e.publish_status = 'published';

------------------------------------------------------------------------------------------------
-- Busca. Funções internas (public) montam o SQL; as do esquema api são SECURITY DEFINER e
-- validam toda entrada antes de chegar aqui. Valores do usuário só entram via %L.
------------------------------------------------------------------------------------------------

create function search_from() returns text
language sql immutable set search_path = public, ext, pg_temp as $$
  select 'question q
            join exam e       on e.id = q.exam_id
            join contest c    on c.id = e.contest_id
            join agency a     on a.id = c.agency_id
            join exam_board b on b.id = c.exam_board_id
            join subject s    on s.id = q.subject_id'
$$;

-- Condição SQL para `filters` + `query`. `skip` omite um filtro (contagem de facetas).
create function search_condition(filters jsonb, query text, skip text default null) returns text
language plpgsql stable set search_path = public, ext, pg_temp as $$
declare
  list_keys constant text[] :=
    array['exam_board', 'agency', 'position', 'career', 'subject', 'topic', 'type'];
  all_keys constant text[] := list_keys || array['year', 'include_annulled'];
  -- Mesmo critério de published_question.
  conds text[] := array[
    'q.publish_status = ''published''', 'e.publish_status = ''published''', 'q.duplicate_of is null'];
  k text;
  vals text[];
  year_filter jsonb;
begin
  filters := coalesce(filters, '{}');
  if jsonb_typeof(filters) <> 'object' then
    raise exception 'filters deve ser um objeto JSON' using errcode = 'invalid_parameter_value';
  end if;
  for k in select jsonb_object_keys(filters) loop
    if not k = any(all_keys) then
      raise exception 'filtro desconhecido: %', k using errcode = 'invalid_parameter_value',
        hint = 'filtros válidos: ' || array_to_string(all_keys, ', ');
    end if;
  end loop;

  foreach k in array list_keys loop
    continue when not filters ? k;
    if jsonb_typeof(filters -> k) <> 'array'
       or exists (select 1 from jsonb_array_elements(filters -> k) v where jsonb_typeof(v) <> 'string') then
      raise exception 'filtro % deve ser uma lista de textos', k using errcode = 'invalid_parameter_value';
    end if;
    vals := array(select jsonb_array_elements_text(filters -> k));
    begin
      case k
        when 'career' then perform vals::career[];
        when 'type'   then perform vals::question_type[];
        when 'topic'  then perform vals::ext.ltree[];
        else null;
      end case;
    exception when invalid_text_representation or syntax_error then
      raise exception 'valor inválido no filtro %: %', k, filters -> k
        using errcode = 'invalid_parameter_value';
    end;
    continue when k = skip or cardinality(vals) = 0;
    conds := conds || case k
      when 'exam_board' then format('b.slug = any(%L::text[])', vals)
      when 'agency'     then format('a.slug = any(%L::text[])', vals)
      when 'career'     then format('a.career::text = any(%L::text[])', vals)
      when 'subject'    then format('s.slug = any(%L::text[])', vals)
      when 'type'       then format('q.type::text = any(%L::text[])', vals)
      when 'position'   then format(
        'exists (select 1 from exam_position ep join position po on po.id = ep.position_id'
        ' where ep.exam_id = q.exam_id and po.slug = any(%L::text[]))', vals)
      when 'topic'      then format(
        'exists (select 1 from question_topic qt join topic t on t.id = qt.topic_id'
        ' where qt.question_id = q.id and t.path <@ any(%L::ext.ltree[]))', vals)
    end;
  end loop;

  if filters ? 'year' then
    year_filter := filters -> 'year';
    if jsonb_typeof(year_filter) <> 'object'
       or exists (select 1 from jsonb_each(year_filter) y
                   where y.key not in ('from', 'to') or jsonb_typeof(y.value) <> 'number'
                      or y.value::text !~ '^\d{4}$') then
      raise exception 'filtro year deve ser {"from": ano, "to": ano}'
        using errcode = 'invalid_parameter_value';
    end if;
    if skip is distinct from 'year' then
      if year_filter ? 'from' then
        conds := conds || format('c.year >= %s', (year_filter ->> 'from')::int);
      end if;
      if year_filter ? 'to' then
        conds := conds || format('c.year <= %s', (year_filter ->> 'to')::int);
      end if;
    end if;
  end if;

  if filters ? 'include_annulled' and jsonb_typeof(filters -> 'include_annulled') <> 'boolean' then
    raise exception 'filtro include_annulled deve ser true ou false'
      using errcode = 'invalid_parameter_value';
  end if;
  if not coalesce((filters ->> 'include_annulled')::boolean, false) then
    conds := array_append(conds, 'q.answer_status <> ''annulled''');
  end if;

  if nullif(btrim(query), '') is not null then
    conds := conds || format('q.search_vector @@ websearch_to_tsquery(''ext.pt_unaccent'', %L)', query);
  end if;

  return array_to_string(conds, ' and ');
end
$$;

-- Documentos JSON das questões, na ordem dos ids.
create function question_docs(ids uuid[]) returns jsonb
language sql stable set search_path = public, ext, pg_temp as $$
  select coalesce(jsonb_agg(to_jsonb(v) order by array_position(ids, v.id)), '[]')
    from api.question v
   where v.id = any(ids)
$$;

create function api.search_questions(
  filters jsonb default '{}',
  query text default null,
  page_size integer default 20,
  cursor text default null
) returns jsonb
language plpgsql stable security definer set search_path = public, ext, pg_temp as $$
declare
  cond text := search_condition(filters, query);
  keyset text := 'true';
  after jsonb;
  r record;
  ids uuid[] := '{}';
  total bigint;
  next_cursor text;
begin
  if page_size is null or page_size not between 1 and 100 then
    raise exception 'page_size deve estar entre 1 e 100' using errcode = 'invalid_parameter_value';
  end if;

  if cursor is not null then
    begin
      after := convert_from(decode(cursor, 'base64'), 'utf8')::jsonb;
      keyset := format('(-c.year, c.slug, e.slug, q.number) > (%s, %L, %L, %s)',
                       -(after ->> 'y')::int, after ->> 'c', after ->> 'e', (after ->> 'n')::int);
    exception when others then
      after := null;
    end;
    if after is null or after ->> 'y' is null or after ->> 'c' is null
       or after ->> 'e' is null or after ->> 'n' is null then
      raise exception 'cursor inválido' using errcode = 'invalid_parameter_value';
    end if;
  end if;

  execute format('select count(*) from %s where %s', search_from(), cond) into total;

  for r in execute format(
    'select q.id, c.year, c.slug as contest_slug, e.slug as exam_slug, q.number from %s where %s and %s'
    ' order by -c.year, c.slug, e.slug, q.number limit %s',
    search_from(), cond, keyset, page_size + 1)
  loop
    if cardinality(ids) = page_size then
      -- Há mais uma linha: o cursor aponta para a última da página.
      next_cursor := replace(encode(convert_to(after::text, 'utf8'), 'base64'), E'\n', '');
      exit;
    end if;
    ids := ids || r.id;
    after := jsonb_build_object('y', r.year, 'c', r.contest_slug, 'e', r.exam_slug, 'n', r.number);
  end loop;

  return jsonb_build_object('total', total, 'items', question_docs(ids), 'next_cursor', next_cursor);
end
$$;

create function api.facet_counts(filters jsonb default '{}', query text default null) returns jsonb
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

create function api.get_question(id uuid) returns jsonb
language sql stable security definer set search_path = public, ext, pg_temp as $$
  select question_docs(array[get_question.id]) -> 0
$$;

create function api.asset_url(sha256 text) returns text
language sql stable security definer set search_path = public, ext, pg_temp as $$
  select (select value from setting where key = 'asset_base_url') || a.storage_key
    from asset a
   where a.sha256 = asset_url.sha256
$$;

-- migrate:down
set local search_path = public, ext;

drop function api.asset_url(text);
drop function api.get_question(uuid);
drop function api.facet_counts(jsonb, text);
drop function api.search_questions(jsonb, text, integer, text);
drop function question_docs(uuid[]);
drop function search_condition(jsonb, text, text);
drop function search_from();
drop view api.exam;
drop view api.topic;
drop view api.subject;
drop view api.position;
drop view api.agency;
drop view api.exam_board;
drop view api.passage;
drop view api.question;
drop view published_question;
drop table setting;
