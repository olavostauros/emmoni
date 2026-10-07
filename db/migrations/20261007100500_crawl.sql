-- migrate:up
set local search_path = public, ext;

create type crawl.discovery_status as enum
  ('pending', 'proposed', 'approved', 'rejected', 'out_of_scope', 'ingested');

create table crawl.page (
  url             text primary key,
  source_slug     slug not null,
  last_fetched_at timestamptz,
  http_status     smallint,
  etag            text,
  last_modified   text,
  content_sha256  text check (content_sha256 ~ '^[0-9a-f]{64}$'),
  next_fetch_at   timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index page_source_next_fetch_idx on crawl.page (source_slug, next_fetch_at);

create table crawl.discovered_document (
  id                   bigint generated always as identity primary key,
  url                  text not null unique,
  source_slug          slug not null,
  found_on_url         text not null,
  link_text            text,
  guessed_kind         document_kind,
  guessed_contest_slug slug,
  guessed              jsonb not null default '{}',
  status               crawl.discovery_status not null default 'pending',
  status_reason        text,
  first_seen_at        timestamptz not null default now(),
  last_seen_at         timestamptz not null default now(),
  constraint discovered_document_reason check (
    status not in ('rejected', 'out_of_scope') or status_reason is not null)
);
create index discovered_document_status_idx on crawl.discovered_document (status);

create trigger page_updated_at before update on crawl.page
  for each row execute function set_updated_at();

-- migrate:down
set local search_path = public, ext;

drop table crawl.discovered_document;
drop table crawl.page;
drop type crawl.discovery_status;
