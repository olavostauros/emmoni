-- migrate:up
set local search_path = public, ext;

create domain slug as text check (value ~ '^[a-z0-9]+(-[a-z0-9]+)*$');

create function set_updated_at() returns trigger
language plpgsql set search_path = public, ext, pg_temp as $$
begin
  new.updated_at := now();
  return new;
end
$$;

create type career as enum (
  'pf', 'prf', 'policia_civil', 'policia_militar', 'bombeiro_militar',
  'policia_penal', 'policia_legislativa', 'guarda_municipal', 'outra'
);
create type government_level as enum ('federal', 'estadual', 'distrital', 'municipal');
create type education_level as enum ('fundamental', 'medio', 'superior');

create table exam_board (
  id         bigint generated always as identity primary key,
  slug       slug not null unique,
  name       text not null,
  short_name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table agency (
  id         bigint generated always as identity primary key,
  slug       slug not null unique,
  name       text not null,
  short_name text not null,
  career     career not null,
  level      government_level not null,
  state      text check (state ~ '^[A-Z]{2}$'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint agency_state_by_level check ((level = 'federal') = (state is null))
);

create table position (
  id              bigint generated always as identity primary key,
  agency_id       bigint not null references agency,
  slug            slug not null,
  name            text not null,
  education_level education_level,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (agency_id, slug)
);
create index position_slug_idx on position (slug);

create trigger exam_board_updated_at before update on exam_board
  for each row execute function set_updated_at();
create trigger agency_updated_at before update on agency
  for each row execute function set_updated_at();
create trigger position_updated_at before update on position
  for each row execute function set_updated_at();

-- migrate:down
set local search_path = public, ext;

drop table position;
drop table agency;
drop table exam_board;
drop type education_level;
drop type government_level;
drop type career;
drop function set_updated_at();
drop domain slug;
