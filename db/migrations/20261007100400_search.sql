-- migrate:up
set local search_path = public, ext;

-- Busca em português sem acento. Fica em `ext` para ser visível a todos os papéis.
create text search configuration ext.pt_unaccent (copy = pg_catalog.portuguese);
alter text search configuration ext.pt_unaccent
  alter mapping for hword, hword_part, word with ext.unaccent, portuguese_stem;

-- Markdown restrito (docs/content-format.md) → texto para indexar.
create function md_plain(md text) returns text
language sql immutable parallel safe set search_path = public, ext, pg_temp as $$
  select regexp_replace(
           regexp_replace(
             regexp_replace(
               regexp_replace(md, '!\[([^\]]*)\]\([^)]*\)', '\1', 'g'),
               '</?u>', ' ', 'g'),
             '-{3,}', ' ', 'g'),
           '[*_|$`~\\]+', ' ', 'g')
$$;

create function question_search_vector(statement_md text, question_id uuid, passage_id uuid)
returns tsvector
language sql stable set search_path = public, ext, pg_temp as $$
  select setweight(to_tsvector('ext.pt_unaccent', md_plain($1)), 'A')
      || setweight(to_tsvector('ext.pt_unaccent', coalesce(
           (select string_agg(md_plain(o.body_md), ' ' order by o.letter)
              from question_option o where o.question_id = $2), '')), 'B')
      || setweight(to_tsvector('ext.pt_unaccent', coalesce(
           (select md_plain(p.body_md) from passage p where p.id = $3), '')), 'B')
$$;

create function question_search_refresh() returns trigger
language plpgsql set search_path = public, ext, pg_temp as $$
begin
  new.search_vector := question_search_vector(new.statement_md, new.id, new.passage_id);
  return new;
end
$$;

-- Alternativas e texto-base moram em outras tabelas: uma mudança nelas reescreve a questão,
-- e o trigger da questão recalcula o vetor.
create function question_search_touch() returns trigger
language plpgsql set search_path = public, ext, pg_temp as $$
begin
  if tg_table_name = 'question_option' then
    update question set search_vector = search_vector
     where id in (new.question_id, old.question_id);
  else
    update question set search_vector = search_vector where passage_id = new.id;
  end if;
  return null;
end
$$;

create trigger question_search_refresh before insert or update on question
  for each row execute function question_search_refresh();
create trigger question_option_search_touch after insert or update or delete on question_option
  for each row execute function question_search_touch();
create trigger passage_search_touch after update of body_md on passage
  for each row execute function question_search_touch();

create index question_search_idx on question using gin (search_vector);
create index question_statement_trgm_idx on question using gin (statement_md ext.gin_trgm_ops);

-- migrate:down
set local search_path = public, ext;

drop index question_statement_trgm_idx;
drop index question_search_idx;
drop trigger passage_search_touch on passage;
drop trigger question_option_search_touch on question_option;
drop trigger question_search_refresh on question;
drop function question_search_touch();
drop function question_search_refresh();
drop function question_search_vector(text, uuid, uuid);
drop function md_plain(text);
drop text search configuration ext.pt_unaccent;
