-- migrate:up
set local search_path = public, ext;

create table subject (
  id         bigint generated always as identity primary key,
  slug       slug not null unique,
  name       text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- O identificador público de um assunto é o `path`: o primeiro rótulo é o slug da disciplina
-- (com '-' trocado por '_'), os seguintes descem na hierarquia.
create table topic (
  id         bigint generated always as identity primary key,
  subject_id bigint not null references subject,
  path       ext.ltree not null unique check (ext.nlevel(path) >= 2),
  name       text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index topic_path_gist on topic using gist (path);
create index topic_subject_idx on topic (subject_id);

create function topic_guard() returns trigger
language plpgsql set search_path = public, ext, pg_temp as $$
declare
  subject_label text;
begin
  if tg_op = 'UPDATE' and new.path <> old.path then
    raise exception 'o caminho de um assunto não muda (%): ele é o identificador público', old.path
      using errcode = 'check_violation';
  end if;
  if tg_op = 'DELETE' then
    if exists (select 1 from topic where path <@ old.path and id <> old.id) then
      raise exception 'assunto % tem subassuntos', old.path using errcode = 'foreign_key_violation';
    end if;
    return old;
  end if;

  select replace(slug, '-', '_') into subject_label from subject where id = new.subject_id;
  if subpath(new.path, 0, 1)::text <> subject_label then
    raise exception 'assunto % deve começar pelo rótulo da disciplina (%)', new.path, subject_label
      using errcode = 'check_violation';
  end if;
  if nlevel(new.path) > 2
     and not exists (select 1 from topic where path = subpath(new.path, 0, nlevel(new.path) - 1)) then
    raise exception 'assunto pai de % não existe', new.path using errcode = 'foreign_key_violation';
  end if;
  return new;
end
$$;

create trigger topic_guard before insert or update or delete on topic
  for each row execute function topic_guard();

-- Fecho transitivo: cada assunto e todos os seus ancestrais (inclusive ele mesmo).
-- Mantido por trigger; serve às contagens que incluem subassuntos.
create table topic_ancestor (
  topic_id    bigint not null references topic on delete cascade,
  ancestor_id bigint not null references topic on delete cascade,
  primary key (topic_id, ancestor_id)
);
create index topic_ancestor_ancestor_idx on topic_ancestor (ancestor_id);

create function topic_ancestor_fill() returns trigger
language plpgsql set search_path = public, ext, pg_temp as $$
begin
  insert into topic_ancestor (topic_id, ancestor_id)
  select new.id, a.id from topic a where a.path @> new.path;
  return null;
end
$$;

create trigger topic_ancestor_fill after insert on topic
  for each row execute function topic_ancestor_fill();
create trigger subject_updated_at before update on subject
  for each row execute function set_updated_at();
create trigger topic_updated_at before update on topic
  for each row execute function set_updated_at();

-- migrate:down
set local search_path = public, ext;

drop table topic_ancestor;
drop table topic;
drop function topic_ancestor_fill();
drop function topic_guard();
drop table subject;
