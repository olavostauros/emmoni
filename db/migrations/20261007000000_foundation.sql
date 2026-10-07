-- migrate:up

-- Extensões ficam num esquema próprio, visível a todos os papéis.
create schema ext;
grant usage on schema ext to public;
create extension unaccent with schema ext;
create extension pg_trgm  with schema ext;
create extension ltree    with schema ext;
create extension pgcrypto with schema ext;

do $$
begin
  execute format('alter database %I set search_path = public, ext', current_database());
end
$$;

-- public: tabelas internas. crawl: estado do crawler. api: contrato com o front-end.
create schema api;
create schema crawl;

revoke all on schema public from public;
grant usage on schema public to emmoni_ingest;
grant usage on schema crawl  to emmoni_ingest;
grant usage on schema api    to emmoni_ingest, emmoni_web;

-- Funções não são executáveis por qualquer papel; cada esquema concede explicitamente.
alter default privileges for role emmoni_owner revoke execute on functions from public;

alter default privileges for role emmoni_owner in schema public
  grant select, insert, update, delete on tables to emmoni_ingest;
alter default privileges for role emmoni_owner in schema public
  grant usage, select on sequences to emmoni_ingest;
alter default privileges for role emmoni_owner in schema public
  grant execute on functions to emmoni_ingest;

alter default privileges for role emmoni_owner in schema crawl
  grant select, insert, update, delete on tables to emmoni_ingest;
alter default privileges for role emmoni_owner in schema crawl
  grant usage, select on sequences to emmoni_ingest;
alter default privileges for role emmoni_owner in schema crawl
  grant execute on functions to emmoni_ingest;

alter default privileges for role emmoni_owner in schema api
  grant select on tables to emmoni_ingest, emmoni_web;
alter default privileges for role emmoni_owner in schema api
  grant execute on functions to emmoni_ingest, emmoni_web;

-- migrate:down

alter default privileges for role emmoni_owner in schema api
  revoke execute on functions from emmoni_ingest, emmoni_web;
alter default privileges for role emmoni_owner in schema api
  revoke select on tables from emmoni_ingest, emmoni_web;

alter default privileges for role emmoni_owner in schema crawl
  revoke execute on functions from emmoni_ingest;
alter default privileges for role emmoni_owner in schema crawl
  revoke usage, select on sequences from emmoni_ingest;
alter default privileges for role emmoni_owner in schema crawl
  revoke select, insert, update, delete on tables from emmoni_ingest;

alter default privileges for role emmoni_owner in schema public
  revoke execute on functions from emmoni_ingest;
alter default privileges for role emmoni_owner in schema public
  revoke usage, select on sequences from emmoni_ingest;
alter default privileges for role emmoni_owner in schema public
  revoke select, insert, update, delete on tables from emmoni_ingest;

alter default privileges for role emmoni_owner grant execute on functions to public;

revoke usage on schema public from emmoni_ingest;
grant usage on schema public to public;

drop schema crawl;
drop schema api;

do $$
begin
  execute format('alter database %I reset search_path', current_database());
end
$$;

drop extension pgcrypto;
drop extension ltree;
drop extension pg_trgm;
drop extension unaccent;
drop schema ext;
