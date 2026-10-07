-- migrate:up
set local search_path = public, ext;

create type document_kind as enum
  ('exam', 'answer_key_preliminary', 'answer_key_final', 'notice', 'appeal_result');
create type publish_status as enum ('draft', 'review', 'published');

create table source_document (
  id          bigint generated always as identity primary key,
  kind        document_kind not null,
  url         text not null,
  sha256      text not null unique check (sha256 ~ '^[0-9a-f]{64}$'),
  local_path  text,
  page_count  integer check (page_count > 0),
  fetched_at  timestamptz not null,
  ocr_applied boolean not null default false,
  created_at  timestamptz not null default now()
);

create table contest (
  id            bigint generated always as identity primary key,
  slug          slug not null unique,
  agency_id     bigint not null references agency,
  exam_board_id bigint not null references exam_board,
  year          smallint not null check (year between 1980 and 2100),
  notice_number text,
  name          text not null,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index contest_agency_idx on contest (agency_id);
create index contest_exam_board_idx on contest (exam_board_id);

create table exam (
  id                     bigint generated always as identity primary key,
  contest_id             bigint not null references contest on delete cascade,
  slug                   slug not null,
  name                   text not null,
  applied_on             date,
  shift                  text,
  canonical_booklet      text,
  exam_document_id       bigint references source_document,
  answer_key_preliminary_document_id bigint references source_document,
  answer_key_final_document_id       bigint references source_document,
  publish_status         publish_status not null default 'draft',
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),
  unique (contest_id, slug)
);

create table exam_position (
  exam_id     bigint not null references exam on delete cascade,
  position_id bigint not null references position,
  primary key (exam_id, position_id)
);
create index exam_position_position_idx on exam_position (position_id);

create trigger contest_updated_at before update on contest
  for each row execute function set_updated_at();
create trigger exam_updated_at before update on exam
  for each row execute function set_updated_at();

-- migrate:down
set local search_path = public, ext;

drop table exam_position;
drop table exam;
drop table contest;
drop table source_document;
drop type publish_status;
drop type document_kind;
