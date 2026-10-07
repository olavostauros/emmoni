-- migrate:up
set local search_path = public, ext;

create type question_type as enum ('multiple_choice', 'true_false', 'essay');
create type answer_status as enum ('valid', 'changed', 'annulled');

create table passage (
  id          uuid primary key default gen_random_uuid(),
  exam_id     bigint not null references exam on delete cascade,
  body_md     text not null check (body_md <> ''),
  source_page smallint not null check (source_page > 0),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (id, exam_id)
);

create table question (
  id                 uuid primary key default gen_random_uuid(),
  exam_id            bigint not null references exam on delete cascade,
  number             smallint not null check (number > 0),
  type               question_type not null,
  subject_id         bigint references subject,
  passage_id         uuid,
  statement_md       text not null check (statement_md <> ''),
  answer_preliminary text,
  answer_final       text,
  answer_status      answer_status not null default 'valid',
  statement_hash     text not null check (statement_hash ~ '^[0-9a-f]{64}$'),
  duplicate_of       uuid references question on delete set null,
  source_page        smallint not null check (source_page > 0),
  extracted_by       text not null,
  publish_status     publish_status not null default 'draft',
  search_vector      tsvector not null default '',
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (exam_id, number),
  -- O texto-base precisa ser da mesma prova.
  foreign key (passage_id, exam_id) references passage (id, exam_id),
  constraint question_not_own_duplicate check (duplicate_of <> id),
  constraint question_answer_format check (
    case type
      when 'true_false' then
        coalesce(answer_preliminary, 'C') in ('C', 'E') and coalesce(answer_final, 'C') in ('C', 'E')
      when 'multiple_choice' then
        coalesce(answer_preliminary, 'A') ~ '^[A-E]$' and coalesce(answer_final, 'A') ~ '^[A-E]$'
      else answer_preliminary is null and answer_final is null
    end),
  constraint question_answer_status check (
    case answer_status
      when 'annulled' then answer_final is null
      when 'changed' then answer_preliminary is not null and answer_final is not null
                          and answer_final <> answer_preliminary
      else answer_preliminary is null or answer_final is null or answer_final = answer_preliminary
    end),
  constraint question_publishable check (
    publish_status <> 'published'
    or (subject_id is not null
        and (type = 'essay' or answer_final is not null or answer_status = 'annulled')))
);
create index question_subject_idx on question (subject_id);
create index question_passage_idx on question (passage_id);
create index question_statement_hash_idx on question (statement_hash);
create index question_duplicate_of_idx on question (duplicate_of);

create table question_option (
  question_id uuid not null references question on delete cascade,
  letter      text not null check (letter ~ '^[A-E]$'),
  body_md     text not null check (body_md <> ''),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  primary key (question_id, letter)
);

create table question_topic (
  question_id uuid not null references question on delete cascade,
  topic_id    bigint not null references topic,
  origin      text not null check (origin in ('manual', 'llm', 'rule')),
  confidence  real check (confidence between 0 and 1),
  created_at  timestamptz not null default now(),
  primary key (question_id, topic_id)
);
create index question_topic_topic_idx on question_topic (topic_id);

create table asset (
  id          bigint generated always as identity primary key,
  sha256      text not null unique check (sha256 ~ '^[0-9a-f]{64}$'),
  mime_type   text not null
              check (mime_type in ('image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/svg+xml')),
  width       integer check (width > 0),
  height      integer check (height > 0),
  alt_text    text,
  storage_key text not null unique,
  created_at  timestamptz not null default now()
);

create table question_asset (
  question_id uuid not null references question on delete cascade,
  asset_id    bigint not null references asset,
  position    smallint not null default 0,
  primary key (question_id, asset_id)
);

create table passage_asset (
  passage_id uuid not null references passage on delete cascade,
  asset_id   bigint not null references asset,
  position   smallint not null default 0,
  primary key (passage_id, asset_id)
);

-- Cadernos que não são o canônico: número original → questão canônica.
create table booklet_mapping (
  exam_id         bigint not null references exam on delete cascade,
  booklet         text not null,
  original_number smallint not null check (original_number > 0),
  question_id     uuid not null references question on delete cascade,
  primary key (exam_id, booklet, original_number)
);

-- Alternativas × tipo × gabarito. Diferido: a questão e as alternativas entram na mesma transação.
create function check_question_options(qid uuid) returns void
language plpgsql set search_path = public, ext, pg_temp as $$
declare
  q question;
  letters text[];
begin
  select * into q from question where id = qid;
  if not found then
    return;
  end if;
  select coalesce(array_agg(letter), '{}') into letters from question_option where question_id = qid;
  if q.type <> 'multiple_choice' then
    if cardinality(letters) > 0 then
      raise exception 'questão % (%) não pode ter alternativas', qid, q.type
        using errcode = 'check_violation';
    end if;
    return;
  end if;
  if q.answer_preliminary is not null and not q.answer_preliminary = any(letters) then
    raise exception 'gabarito preliminar % da questão % não é uma alternativa', q.answer_preliminary, qid
      using errcode = 'check_violation';
  end if;
  if q.answer_final is not null and not q.answer_final = any(letters) then
    raise exception 'gabarito definitivo % da questão % não é uma alternativa', q.answer_final, qid
      using errcode = 'check_violation';
  end if;
end
$$;

create function question_options_guard() returns trigger
language plpgsql set search_path = public, ext, pg_temp as $$
begin
  if tg_table_name = 'question' then
    perform check_question_options(new.id);
  else
    if tg_op in ('INSERT', 'UPDATE') then
      perform check_question_options(new.question_id);
    end if;
    if tg_op in ('UPDATE', 'DELETE') then
      perform check_question_options(old.question_id);
    end if;
  end if;
  return null;
end
$$;

create constraint trigger question_options_check
  after insert or update on question deferrable initially deferred
  for each row execute function question_options_guard();
create constraint trigger question_option_options_check
  after insert or update or delete on question_option deferrable initially deferred
  for each row execute function question_options_guard();

create trigger passage_updated_at before update on passage
  for each row execute function set_updated_at();
create trigger question_updated_at before update on question
  for each row execute function set_updated_at();
create trigger question_option_updated_at before update on question_option
  for each row execute function set_updated_at();

-- migrate:down
set local search_path = public, ext;

drop table booklet_mapping;
drop table passage_asset;
drop table question_asset;
drop table asset;
drop table question_topic;
drop table question_option;
drop table question;
drop function question_options_guard();
drop function check_question_options(uuid);
drop table passage;
drop type answer_status;
drop type question_type;
