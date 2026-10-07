\restrict dbmate

-- Dumped from database version 17.11 (Debian 17.11-1.pgdg13+2)
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: api; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA api;


--
-- Name: crawl; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA crawl;


--
-- Name: ext; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA ext;


--
-- Name: ltree; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS ltree WITH SCHEMA ext;


--
-- Name: EXTENSION ltree; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION ltree IS 'data type for hierarchical tree-like structures';


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA ext;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA ext;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: unaccent; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA ext;


--
-- Name: EXTENSION unaccent; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION unaccent IS 'text search dictionary that removes accents';


--
-- Name: discovery_status; Type: TYPE; Schema: crawl; Owner: -
--

CREATE TYPE crawl.discovery_status AS ENUM (
    'pending',
    'proposed',
    'approved',
    'rejected',
    'out_of_scope',
    'ingested'
);


--
-- Name: answer_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.answer_status AS ENUM (
    'valid',
    'changed',
    'annulled'
);


--
-- Name: career; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.career AS ENUM (
    'pf',
    'prf',
    'policia_civil',
    'policia_militar',
    'bombeiro_militar',
    'policia_penal',
    'policia_legislativa',
    'guarda_municipal',
    'outra'
);


--
-- Name: document_kind; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.document_kind AS ENUM (
    'exam',
    'answer_key_preliminary',
    'answer_key_final',
    'notice',
    'appeal_result'
);


--
-- Name: education_level; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.education_level AS ENUM (
    'fundamental',
    'medio',
    'superior'
);


--
-- Name: government_level; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.government_level AS ENUM (
    'federal',
    'estadual',
    'distrital',
    'municipal'
);


--
-- Name: publish_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.publish_status AS ENUM (
    'draft',
    'review',
    'published'
);


--
-- Name: question_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.question_type AS ENUM (
    'multiple_choice',
    'true_false',
    'essay'
);


--
-- Name: slug; Type: DOMAIN; Schema: public; Owner: -
--

CREATE DOMAIN public.slug AS text
	CONSTRAINT slug_check CHECK ((VALUE ~ '^[a-z0-9]+(-[a-z0-9]+)*$'::text));


--
-- Name: asset_url(text); Type: FUNCTION; Schema: api; Owner: -
--

CREATE FUNCTION api.asset_url(sha256 text) RETURNS text
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $$
  select (select value from setting where key = 'asset_base_url') || a.storage_key
    from asset a
   where a.sha256 = asset_url.sha256
$$;


--
-- Name: facet_counts(jsonb, text); Type: FUNCTION; Schema: api; Owner: -
--

CREATE FUNCTION api.facet_counts(filters jsonb DEFAULT '{}'::jsonb, query text DEFAULT NULL::text) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $_$
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
$_$;


--
-- Name: get_question(uuid); Type: FUNCTION; Schema: api; Owner: -
--

CREATE FUNCTION api.get_question(id uuid) RETURNS jsonb
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $$
  select question_docs(array[get_question.id]) -> 0
$$;


--
-- Name: search_questions(jsonb, text, integer, text); Type: FUNCTION; Schema: api; Owner: -
--

CREATE FUNCTION api.search_questions(filters jsonb DEFAULT '{}'::jsonb, query text DEFAULT NULL::text, page_size integer DEFAULT 20, cursor text DEFAULT NULL::text) RETURNS jsonb
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $$
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


--
-- Name: check_question_options(uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.check_question_options(qid uuid) RETURNS void
    LANGUAGE plpgsql
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $$
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


--
-- Name: md_plain(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.md_plain(md text) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $_$
  select regexp_replace(
           regexp_replace(
             regexp_replace(
               regexp_replace(md, '!\[([^\]]*)\]\([^)]*\)', '\1', 'g'),
               '</?u>', ' ', 'g'),
             '-{3,}', ' ', 'g'),
           '[*_|$`~\\]+', ' ', 'g')
$_$;


--
-- Name: question_docs(uuid[]); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.question_docs(ids uuid[]) RETURNS jsonb
    LANGUAGE sql STABLE
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $$
  select coalesce(jsonb_agg(to_jsonb(v) order by array_position(ids, v.id)), '[]')
    from api.question v
   where v.id = any(ids)
$$;


--
-- Name: question_options_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.question_options_guard() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $$
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


--
-- Name: question_search_refresh(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.question_search_refresh() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $$
begin
  new.search_vector := question_search_vector(new.statement_md, new.id, new.passage_id);
  return new;
end
$$;


--
-- Name: question_search_touch(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.question_search_touch() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $$
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


--
-- Name: question_search_vector(text, uuid, uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.question_search_vector(statement_md text, question_id uuid, passage_id uuid) RETURNS tsvector
    LANGUAGE sql STABLE
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $_$
  select setweight(to_tsvector('ext.pt_unaccent', md_plain($1)), 'A')
      || setweight(to_tsvector('ext.pt_unaccent', coalesce(
           (select string_agg(md_plain(o.body_md), ' ' order by o.letter)
              from question_option o where o.question_id = $2), '')), 'B')
      || setweight(to_tsvector('ext.pt_unaccent', coalesce(
           (select md_plain(p.body_md) from passage p where p.id = $3), '')), 'B')
$_$;


--
-- Name: search_condition(jsonb, text, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.search_condition(filters jsonb, query text, skip text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql STABLE
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $_$
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
$_$;


--
-- Name: search_from(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.search_from() RETURNS text
    LANGUAGE sql IMMUTABLE
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $$
  select 'question q
            join exam e       on e.id = q.exam_id
            join contest c    on c.id = e.contest_id
            join agency a     on a.id = c.agency_id
            join exam_board b on b.id = c.exam_board_id
            join subject s    on s.id = q.subject_id'
$$;


--
-- Name: set_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $$
begin
  new.updated_at := now();
  return new;
end
$$;


--
-- Name: topic_ancestor_fill(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.topic_ancestor_fill() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $$
begin
  insert into topic_ancestor (topic_id, ancestor_id)
  select new.id, a.id from topic a where a.path @> new.path;
  return null;
end
$$;


--
-- Name: topic_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.topic_guard() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'public', 'ext', 'pg_temp'
    AS $$
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


--
-- Name: pt_unaccent; Type: TEXT SEARCH CONFIGURATION; Schema: ext; Owner: -
--

CREATE TEXT SEARCH CONFIGURATION ext.pt_unaccent (
    PARSER = pg_catalog."default" );

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR asciiword WITH portuguese_stem;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR word WITH ext.unaccent, portuguese_stem;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR numword WITH simple;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR email WITH simple;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR url WITH simple;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR host WITH simple;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR sfloat WITH simple;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR version WITH simple;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR hword_numpart WITH simple;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR hword_part WITH ext.unaccent, portuguese_stem;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR hword_asciipart WITH portuguese_stem;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR numhword WITH simple;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR asciihword WITH portuguese_stem;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR hword WITH ext.unaccent, portuguese_stem;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR url_path WITH simple;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR file WITH simple;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR "float" WITH simple;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR "int" WITH simple;

ALTER TEXT SEARCH CONFIGURATION ext.pt_unaccent
    ADD MAPPING FOR uint WITH simple;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agency; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agency (
    id bigint NOT NULL,
    slug public.slug NOT NULL,
    name text NOT NULL,
    short_name text NOT NULL,
    career public.career NOT NULL,
    level public.government_level NOT NULL,
    state text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT agency_state_by_level CHECK (((level = 'federal'::public.government_level) = (state IS NULL))),
    CONSTRAINT agency_state_check CHECK ((state ~ '^[A-Z]{2}$'::text))
);


--
-- Name: contest; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contest (
    id bigint NOT NULL,
    slug public.slug NOT NULL,
    agency_id bigint NOT NULL,
    exam_board_id bigint NOT NULL,
    year smallint NOT NULL,
    notice_number text,
    name text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT contest_year_check CHECK (((year >= 1980) AND (year <= 2100)))
);


--
-- Name: exam; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exam (
    id bigint NOT NULL,
    contest_id bigint NOT NULL,
    slug public.slug NOT NULL,
    name text NOT NULL,
    applied_on date,
    shift text,
    canonical_booklet text,
    exam_document_id bigint,
    answer_key_preliminary_document_id bigint,
    answer_key_final_document_id bigint,
    publish_status public.publish_status DEFAULT 'draft'::public.publish_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: question; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.question (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    exam_id bigint NOT NULL,
    number smallint NOT NULL,
    type public.question_type NOT NULL,
    subject_id bigint,
    passage_id uuid,
    statement_md text NOT NULL,
    answer_preliminary text,
    answer_final text,
    answer_status public.answer_status DEFAULT 'valid'::public.answer_status NOT NULL,
    statement_hash text NOT NULL,
    duplicate_of uuid,
    source_page smallint NOT NULL,
    extracted_by text NOT NULL,
    publish_status public.publish_status DEFAULT 'draft'::public.publish_status NOT NULL,
    search_vector tsvector DEFAULT ''::tsvector NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    review_reasons text[] DEFAULT '{}'::text[] NOT NULL,
    CONSTRAINT question_answer_format CHECK (
CASE type
    WHEN 'true_false'::public.question_type THEN ((COALESCE(answer_preliminary, 'C'::text) = ANY (ARRAY['C'::text, 'E'::text])) AND (COALESCE(answer_final, 'C'::text) = ANY (ARRAY['C'::text, 'E'::text])))
    WHEN 'multiple_choice'::public.question_type THEN ((COALESCE(answer_preliminary, 'A'::text) ~ '^[A-E]$'::text) AND (COALESCE(answer_final, 'A'::text) ~ '^[A-E]$'::text))
    ELSE ((answer_preliminary IS NULL) AND (answer_final IS NULL))
END),
    CONSTRAINT question_answer_status CHECK (
CASE answer_status
    WHEN 'annulled'::public.answer_status THEN (answer_final IS NULL)
    WHEN 'changed'::public.answer_status THEN ((answer_preliminary IS NOT NULL) AND (answer_final IS NOT NULL) AND (answer_final <> answer_preliminary))
    ELSE ((answer_preliminary IS NULL) OR (answer_final IS NULL) OR (answer_final = answer_preliminary))
END),
    CONSTRAINT question_not_own_duplicate CHECK ((duplicate_of <> id)),
    CONSTRAINT question_number_check CHECK ((number > 0)),
    CONSTRAINT question_publishable CHECK (((publish_status <> 'published'::public.publish_status) OR ((subject_id IS NOT NULL) AND ((type = 'essay'::public.question_type) OR (answer_final IS NOT NULL) OR (answer_status = 'annulled'::public.answer_status))))),
    CONSTRAINT question_source_page_check CHECK ((source_page > 0)),
    CONSTRAINT question_statement_hash_check CHECK ((statement_hash ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT question_statement_md_check CHECK ((statement_md <> ''::text))
);


--
-- Name: COLUMN question.review_reasons; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.question.review_reasons IS 'Motivos da etapa validate para a questão ficar em review (vazio = sem pendências).';


--
-- Name: published_question; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.published_question AS
 SELECT q.id,
    q.exam_id,
    q.number,
    q.type,
    q.subject_id,
    q.passage_id,
    q.statement_md,
    q.answer_preliminary,
    q.answer_final,
    q.answer_status,
    q.statement_hash,
    q.duplicate_of,
    q.source_page,
    q.extracted_by,
    q.publish_status,
    q.search_vector,
    q.created_at,
    q.updated_at
   FROM (public.question q
     JOIN public.exam e ON ((e.id = q.exam_id)))
  WHERE ((q.publish_status = 'published'::public.publish_status) AND (e.publish_status = 'published'::public.publish_status) AND (q.duplicate_of IS NULL));


--
-- Name: agency; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.agency AS
 SELECT slug,
    name,
    short_name,
    (career)::text AS career,
    (level)::text AS government_level,
    state,
    ( SELECT count(*) AS count
           FROM ((public.published_question q
             JOIN public.exam e ON ((e.id = q.exam_id)))
             JOIN public.contest c ON ((c.id = e.contest_id)))
          WHERE (c.agency_id = a.id)) AS question_count
   FROM public.agency a;


--
-- Name: exam_board; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exam_board (
    id bigint NOT NULL,
    slug public.slug NOT NULL,
    name text NOT NULL,
    short_name text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: exam_position; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exam_position (
    exam_id bigint NOT NULL,
    position_id bigint NOT NULL
);


--
-- Name: position; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."position" (
    id bigint NOT NULL,
    agency_id bigint NOT NULL,
    slug public.slug NOT NULL,
    name text NOT NULL,
    education_level public.education_level,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: source_document; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_document (
    id bigint NOT NULL,
    kind public.document_kind NOT NULL,
    url text NOT NULL,
    sha256 text NOT NULL,
    local_path text,
    page_count integer,
    fetched_at timestamp with time zone NOT NULL,
    ocr_applied boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT source_document_page_count_check CHECK ((page_count > 0)),
    CONSTRAINT source_document_sha256_check CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text))
);


--
-- Name: exam; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.exam AS
 SELECT c.slug AS contest_slug,
    c.name AS contest_name,
    c.year,
    c.notice_number,
    a.slug AS agency_slug,
    b.slug AS exam_board_slug,
    e.slug AS exam_slug,
    e.name AS exam_name,
    e.applied_on,
    COALESCE(( SELECT jsonb_agg(jsonb_build_object('slug', po.slug, 'name', po.name) ORDER BY po.name) AS jsonb_agg
           FROM (public.exam_position ep
             JOIN public."position" po ON ((po.id = ep.position_id)))
          WHERE (ep.exam_id = e.id)), '[]'::jsonb) AS positions,
    ( SELECT count(*) AS count
           FROM public.published_question q
          WHERE (q.exam_id = e.id)) AS question_count,
    d.url AS source_url
   FROM ((((public.exam e
     JOIN public.contest c ON ((c.id = e.contest_id)))
     JOIN public.agency a ON ((a.id = c.agency_id)))
     JOIN public.exam_board b ON ((b.id = c.exam_board_id)))
     LEFT JOIN public.source_document d ON ((d.id = e.exam_document_id)))
  WHERE (e.publish_status = 'published'::public.publish_status);


--
-- Name: exam_board; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.exam_board AS
 SELECT slug,
    name,
    short_name,
    ( SELECT count(*) AS count
           FROM ((public.published_question q
             JOIN public.exam e ON ((e.id = q.exam_id)))
             JOIN public.contest c ON ((c.id = e.contest_id)))
          WHERE (c.exam_board_id = b.id)) AS question_count
   FROM public.exam_board b;


--
-- Name: asset; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asset (
    id bigint NOT NULL,
    sha256 text NOT NULL,
    mime_type text NOT NULL,
    width integer,
    height integer,
    alt_text text,
    storage_key text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT asset_height_check CHECK ((height > 0)),
    CONSTRAINT asset_mime_type_check CHECK ((mime_type = ANY (ARRAY['image/png'::text, 'image/jpeg'::text, 'image/gif'::text, 'image/webp'::text, 'image/svg+xml'::text]))),
    CONSTRAINT asset_sha256_check CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT asset_width_check CHECK ((width > 0))
);


--
-- Name: passage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passage (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    exam_id bigint NOT NULL,
    body_md text NOT NULL,
    source_page smallint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    source_key text,
    CONSTRAINT passage_body_md_check CHECK ((body_md <> ''::text)),
    CONSTRAINT passage_source_key_check CHECK ((source_key <> ''::text)),
    CONSTRAINT passage_source_page_check CHECK ((source_page > 0))
);


--
-- Name: passage_asset; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passage_asset (
    passage_id uuid NOT NULL,
    asset_id bigint NOT NULL,
    "position" smallint DEFAULT 0 NOT NULL
);


--
-- Name: setting; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.setting (
    key text NOT NULL,
    value text NOT NULL
);


--
-- Name: passage; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.passage AS
 SELECT id,
    body_md,
    COALESCE(( SELECT jsonb_agg(jsonb_build_object('sha256', x.sha256, 'url', (( SELECT setting.value
                   FROM public.setting
                  WHERE (setting.key = 'asset_base_url'::text)) || x.storage_key), 'mime_type', x.mime_type, 'width', x.width, 'height', x.height, 'alt_text', x.alt_text) ORDER BY x.sha256) AS jsonb_agg
           FROM (public.passage_asset pa
             JOIN public.asset x ON ((x.id = pa.asset_id)))
          WHERE (pa.passage_id = p.id)), '[]'::jsonb) AS assets
   FROM public.passage p
  WHERE (EXISTS ( SELECT 1
           FROM public.published_question q
          WHERE (q.passage_id = p.id)));


--
-- Name: position; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api."position" AS
 SELECT a.slug AS agency_slug,
    po.slug,
    po.name,
    (po.education_level)::text AS education_level,
    ( SELECT count(*) AS count
           FROM (public.published_question q
             JOIN public.exam_position ep ON ((ep.exam_id = q.exam_id)))
          WHERE (ep.position_id = po.id)) AS question_count
   FROM (public."position" po
     JOIN public.agency a ON ((a.id = po.agency_id)));


--
-- Name: question_asset; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.question_asset (
    question_id uuid NOT NULL,
    asset_id bigint NOT NULL,
    "position" smallint DEFAULT 0 NOT NULL
);


--
-- Name: question_option; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.question_option (
    question_id uuid NOT NULL,
    letter text NOT NULL,
    body_md text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT question_option_body_md_check CHECK ((body_md <> ''::text)),
    CONSTRAINT question_option_letter_check CHECK ((letter ~ '^[A-E]$'::text))
);


--
-- Name: question_topic; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.question_topic (
    question_id uuid NOT NULL,
    topic_id bigint NOT NULL,
    origin text NOT NULL,
    confidence real,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT question_topic_confidence_check CHECK (((confidence >= (0)::double precision) AND (confidence <= (1)::double precision))),
    CONSTRAINT question_topic_origin_check CHECK ((origin = ANY (ARRAY['manual'::text, 'llm'::text, 'rule'::text])))
);


--
-- Name: subject; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subject (
    id bigint NOT NULL,
    slug public.slug NOT NULL,
    name text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: topic; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.topic (
    id bigint NOT NULL,
    subject_id bigint NOT NULL,
    path ext.ltree NOT NULL,
    name text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT topic_path_check CHECK ((ext.nlevel(path) >= 2))
);


--
-- Name: question; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.question AS
 SELECT q.id,
    q.number,
    (q.type)::text AS type,
    q.statement_md,
    q.passage_id,
    p.body_md AS passage_md,
    COALESCE(( SELECT jsonb_agg(jsonb_build_object('letter', o.letter, 'body_md', o.body_md) ORDER BY o.letter) AS jsonb_agg
           FROM public.question_option o
          WHERE (o.question_id = q.id)), '[]'::jsonb) AS options,
    q.answer_final AS answer,
    q.answer_preliminary,
    (q.answer_status)::text AS answer_status,
    b.slug AS exam_board_slug,
    b.name AS exam_board_name,
    b.short_name AS exam_board_short_name,
    a.slug AS agency_slug,
    a.name AS agency_name,
    a.short_name AS agency_short_name,
    (a.career)::text AS career,
    (a.level)::text AS government_level,
    a.state,
    c.slug AS contest_slug,
    c.name AS contest_name,
    c.year,
    e.slug AS exam_slug,
    e.name AS exam_name,
    e.applied_on,
    COALESCE(( SELECT jsonb_agg(jsonb_build_object('slug', po.slug, 'name', po.name) ORDER BY po.name) AS jsonb_agg
           FROM (public.exam_position ep
             JOIN public."position" po ON ((po.id = ep.position_id)))
          WHERE (ep.exam_id = e.id)), '[]'::jsonb) AS positions,
    s.slug AS subject_slug,
    s.name AS subject_name,
    COALESCE(( SELECT jsonb_agg(jsonb_build_object('path', (t.path)::text, 'name', t.name) ORDER BY t.path) AS jsonb_agg
           FROM (public.question_topic qt
             JOIN public.topic t ON ((t.id = qt.topic_id)))
          WHERE (qt.question_id = q.id)), '[]'::jsonb) AS topics,
    COALESCE(( SELECT jsonb_agg(jsonb_build_object('sha256', x.sha256, 'url', (( SELECT setting.value
                   FROM public.setting
                  WHERE (setting.key = 'asset_base_url'::text)) || x.storage_key), 'mime_type', x.mime_type, 'width', x.width, 'height', x.height, 'alt_text', x.alt_text) ORDER BY x.sha256) AS jsonb_agg
           FROM public.asset x
          WHERE (x.id IN ( SELECT qa.asset_id
                   FROM public.question_asset qa
                  WHERE (qa.question_id = q.id)
                UNION
                 SELECT pa.asset_id
                   FROM public.passage_asset pa
                  WHERE (pa.passage_id = q.passage_id)))), '[]'::jsonb) AS assets,
    d.url AS source_url,
    q.source_page
   FROM (((((((public.published_question q
     JOIN public.exam e ON ((e.id = q.exam_id)))
     JOIN public.contest c ON ((c.id = e.contest_id)))
     JOIN public.agency a ON ((a.id = c.agency_id)))
     JOIN public.exam_board b ON ((b.id = c.exam_board_id)))
     JOIN public.subject s ON ((s.id = q.subject_id)))
     LEFT JOIN public.passage p ON ((p.id = q.passage_id)))
     LEFT JOIN public.source_document d ON ((d.id = e.exam_document_id)));


--
-- Name: subject; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.subject AS
 SELECT slug,
    name,
    ( SELECT count(*) AS count
           FROM public.published_question q
          WHERE (q.subject_id = s.id)) AS question_count
   FROM public.subject s;


--
-- Name: topic_ancestor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.topic_ancestor (
    topic_id bigint NOT NULL,
    ancestor_id bigint NOT NULL
);


--
-- Name: topic; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.topic AS
 SELECT (t.path)::text AS path,
    t.name,
    s.slug AS subject_slug,
    (ext.nlevel(t.path) - 1) AS depth,
        CASE
            WHEN (ext.nlevel(t.path) > 2) THEN (ext.subpath(t.path, 0, (ext.nlevel(t.path) - 1)))::text
            ELSE NULL::text
        END AS parent_path,
    ( SELECT count(DISTINCT qt.question_id) AS count
           FROM ((public.topic_ancestor ta
             JOIN public.question_topic qt ON ((qt.topic_id = ta.topic_id)))
             JOIN public.published_question q ON ((q.id = qt.question_id)))
          WHERE (ta.ancestor_id = t.id)) AS question_count
   FROM (public.topic t
     JOIN public.subject s ON ((s.id = t.subject_id)));


--
-- Name: discovered_document; Type: TABLE; Schema: crawl; Owner: -
--

CREATE TABLE crawl.discovered_document (
    id bigint NOT NULL,
    url text NOT NULL,
    source_slug public.slug NOT NULL,
    found_on_url text NOT NULL,
    link_text text,
    guessed_kind public.document_kind,
    guessed_contest_slug public.slug,
    guessed jsonb DEFAULT '{}'::jsonb NOT NULL,
    status crawl.discovery_status DEFAULT 'pending'::crawl.discovery_status NOT NULL,
    status_reason text,
    first_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    last_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT discovered_document_reason CHECK (((status <> ALL (ARRAY['rejected'::crawl.discovery_status, 'out_of_scope'::crawl.discovery_status])) OR (status_reason IS NOT NULL)))
);


--
-- Name: discovered_document_id_seq; Type: SEQUENCE; Schema: crawl; Owner: -
--

ALTER TABLE crawl.discovered_document ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME crawl.discovered_document_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: page; Type: TABLE; Schema: crawl; Owner: -
--

CREATE TABLE crawl.page (
    url text NOT NULL,
    source_slug public.slug NOT NULL,
    last_fetched_at timestamp with time zone,
    http_status smallint,
    etag text,
    last_modified text,
    content_sha256 text,
    next_fetch_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT page_content_sha256_check CHECK ((content_sha256 ~ '^[0-9a-f]{64}$'::text))
);


--
-- Name: agency_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.agency ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.agency_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: asset_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.asset ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.asset_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: booklet_mapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.booklet_mapping (
    exam_id bigint NOT NULL,
    booklet text NOT NULL,
    original_number smallint NOT NULL,
    question_id uuid NOT NULL,
    CONSTRAINT booklet_mapping_original_number_check CHECK ((original_number > 0))
);


--
-- Name: contest_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.contest ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.contest_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: exam_board_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.exam_board ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.exam_board_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: exam_document; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exam_document (
    exam_id bigint NOT NULL,
    source_document_id bigint NOT NULL,
    kind public.document_kind NOT NULL,
    "position" smallint DEFAULT 1 NOT NULL,
    CONSTRAINT exam_document_position_check CHECK (("position" > 0))
);


--
-- Name: TABLE exam_document; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.exam_document IS 'Todos os PDFs de uma prova (caderno e gabaritos), inclusive quando um tipo tem mais de um.';


--
-- Name: exam_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.exam ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.exam_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: position_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public."position" ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.position_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying NOT NULL
);


--
-- Name: source_document_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.source_document ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.source_document_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: subject_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.subject ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.subject_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: topic_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.topic ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.topic_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: discovered_document discovered_document_pkey; Type: CONSTRAINT; Schema: crawl; Owner: -
--

ALTER TABLE ONLY crawl.discovered_document
    ADD CONSTRAINT discovered_document_pkey PRIMARY KEY (id);


--
-- Name: discovered_document discovered_document_url_key; Type: CONSTRAINT; Schema: crawl; Owner: -
--

ALTER TABLE ONLY crawl.discovered_document
    ADD CONSTRAINT discovered_document_url_key UNIQUE (url);


--
-- Name: page page_pkey; Type: CONSTRAINT; Schema: crawl; Owner: -
--

ALTER TABLE ONLY crawl.page
    ADD CONSTRAINT page_pkey PRIMARY KEY (url);


--
-- Name: agency agency_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agency
    ADD CONSTRAINT agency_pkey PRIMARY KEY (id);


--
-- Name: agency agency_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agency
    ADD CONSTRAINT agency_slug_key UNIQUE (slug);


--
-- Name: asset asset_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset
    ADD CONSTRAINT asset_pkey PRIMARY KEY (id);


--
-- Name: asset asset_sha256_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset
    ADD CONSTRAINT asset_sha256_key UNIQUE (sha256);


--
-- Name: asset asset_storage_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset
    ADD CONSTRAINT asset_storage_key_key UNIQUE (storage_key);


--
-- Name: booklet_mapping booklet_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.booklet_mapping
    ADD CONSTRAINT booklet_mapping_pkey PRIMARY KEY (exam_id, booklet, original_number);


--
-- Name: contest contest_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contest
    ADD CONSTRAINT contest_pkey PRIMARY KEY (id);


--
-- Name: contest contest_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contest
    ADD CONSTRAINT contest_slug_key UNIQUE (slug);


--
-- Name: exam_board exam_board_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_board
    ADD CONSTRAINT exam_board_pkey PRIMARY KEY (id);


--
-- Name: exam_board exam_board_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_board
    ADD CONSTRAINT exam_board_slug_key UNIQUE (slug);


--
-- Name: exam exam_contest_id_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_contest_id_slug_key UNIQUE (contest_id, slug);


--
-- Name: exam_document exam_document_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_document
    ADD CONSTRAINT exam_document_pkey PRIMARY KEY (exam_id, source_document_id);


--
-- Name: exam exam_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_pkey PRIMARY KEY (id);


--
-- Name: exam_position exam_position_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_position
    ADD CONSTRAINT exam_position_pkey PRIMARY KEY (exam_id, position_id);


--
-- Name: passage_asset passage_asset_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_asset
    ADD CONSTRAINT passage_asset_pkey PRIMARY KEY (passage_id, asset_id);


--
-- Name: passage passage_exam_source_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage
    ADD CONSTRAINT passage_exam_source_key UNIQUE (exam_id, source_key);


--
-- Name: passage passage_id_exam_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage
    ADD CONSTRAINT passage_id_exam_id_key UNIQUE (id, exam_id);


--
-- Name: passage passage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage
    ADD CONSTRAINT passage_pkey PRIMARY KEY (id);


--
-- Name: position position_agency_id_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."position"
    ADD CONSTRAINT position_agency_id_slug_key UNIQUE (agency_id, slug);


--
-- Name: position position_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."position"
    ADD CONSTRAINT position_pkey PRIMARY KEY (id);


--
-- Name: question_asset question_asset_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_asset
    ADD CONSTRAINT question_asset_pkey PRIMARY KEY (question_id, asset_id);


--
-- Name: question question_exam_id_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_exam_id_number_key UNIQUE (exam_id, number);


--
-- Name: question_option question_option_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_option
    ADD CONSTRAINT question_option_pkey PRIMARY KEY (question_id, letter);


--
-- Name: question question_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_pkey PRIMARY KEY (id);


--
-- Name: question_topic question_topic_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_topic
    ADD CONSTRAINT question_topic_pkey PRIMARY KEY (question_id, topic_id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: setting setting_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.setting
    ADD CONSTRAINT setting_pkey PRIMARY KEY (key);


--
-- Name: source_document source_document_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_document
    ADD CONSTRAINT source_document_pkey PRIMARY KEY (id);


--
-- Name: source_document source_document_sha256_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_document
    ADD CONSTRAINT source_document_sha256_key UNIQUE (sha256);


--
-- Name: subject subject_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subject
    ADD CONSTRAINT subject_pkey PRIMARY KEY (id);


--
-- Name: subject subject_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subject
    ADD CONSTRAINT subject_slug_key UNIQUE (slug);


--
-- Name: topic_ancestor topic_ancestor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topic_ancestor
    ADD CONSTRAINT topic_ancestor_pkey PRIMARY KEY (topic_id, ancestor_id);


--
-- Name: topic topic_path_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topic
    ADD CONSTRAINT topic_path_key UNIQUE (path);


--
-- Name: topic topic_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topic
    ADD CONSTRAINT topic_pkey PRIMARY KEY (id);


--
-- Name: discovered_document_status_idx; Type: INDEX; Schema: crawl; Owner: -
--

CREATE INDEX discovered_document_status_idx ON crawl.discovered_document USING btree (status);


--
-- Name: page_source_next_fetch_idx; Type: INDEX; Schema: crawl; Owner: -
--

CREATE INDEX page_source_next_fetch_idx ON crawl.page USING btree (source_slug, next_fetch_at);


--
-- Name: contest_agency_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contest_agency_idx ON public.contest USING btree (agency_id);


--
-- Name: contest_exam_board_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contest_exam_board_idx ON public.contest USING btree (exam_board_id);


--
-- Name: exam_document_source_document_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX exam_document_source_document_idx ON public.exam_document USING btree (source_document_id);


--
-- Name: exam_position_position_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX exam_position_position_idx ON public.exam_position USING btree (position_id);


--
-- Name: position_slug_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX position_slug_idx ON public."position" USING btree (slug);


--
-- Name: question_duplicate_of_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX question_duplicate_of_idx ON public.question USING btree (duplicate_of);


--
-- Name: question_passage_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX question_passage_idx ON public.question USING btree (passage_id);


--
-- Name: question_search_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX question_search_idx ON public.question USING gin (search_vector);


--
-- Name: question_statement_hash_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX question_statement_hash_idx ON public.question USING btree (statement_hash);


--
-- Name: question_statement_trgm_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX question_statement_trgm_idx ON public.question USING gin (statement_md ext.gin_trgm_ops);


--
-- Name: question_subject_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX question_subject_idx ON public.question USING btree (subject_id);


--
-- Name: question_topic_topic_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX question_topic_topic_idx ON public.question_topic USING btree (topic_id);


--
-- Name: topic_ancestor_ancestor_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX topic_ancestor_ancestor_idx ON public.topic_ancestor USING btree (ancestor_id);


--
-- Name: topic_path_gist; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX topic_path_gist ON public.topic USING gist (path);


--
-- Name: topic_subject_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX topic_subject_idx ON public.topic USING btree (subject_id);


--
-- Name: page page_updated_at; Type: TRIGGER; Schema: crawl; Owner: -
--

CREATE TRIGGER page_updated_at BEFORE UPDATE ON crawl.page FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: agency agency_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER agency_updated_at BEFORE UPDATE ON public.agency FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: contest contest_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER contest_updated_at BEFORE UPDATE ON public.contest FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: exam_board exam_board_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER exam_board_updated_at BEFORE UPDATE ON public.exam_board FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: exam exam_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER exam_updated_at BEFORE UPDATE ON public.exam FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: passage passage_search_touch; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER passage_search_touch AFTER UPDATE OF body_md ON public.passage FOR EACH ROW EXECUTE FUNCTION public.question_search_touch();


--
-- Name: passage passage_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER passage_updated_at BEFORE UPDATE ON public.passage FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: position position_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER position_updated_at BEFORE UPDATE ON public."position" FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: question_option question_option_options_check; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER question_option_options_check AFTER INSERT OR DELETE OR UPDATE ON public.question_option DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.question_options_guard();


--
-- Name: question_option question_option_search_touch; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER question_option_search_touch AFTER INSERT OR DELETE OR UPDATE ON public.question_option FOR EACH ROW EXECUTE FUNCTION public.question_search_touch();


--
-- Name: question_option question_option_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER question_option_updated_at BEFORE UPDATE ON public.question_option FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: question question_options_check; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER question_options_check AFTER INSERT OR UPDATE ON public.question DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.question_options_guard();


--
-- Name: question question_search_refresh; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER question_search_refresh BEFORE INSERT OR UPDATE ON public.question FOR EACH ROW EXECUTE FUNCTION public.question_search_refresh();


--
-- Name: question question_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER question_updated_at BEFORE UPDATE ON public.question FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: subject subject_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER subject_updated_at BEFORE UPDATE ON public.subject FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: topic topic_ancestor_fill; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER topic_ancestor_fill AFTER INSERT ON public.topic FOR EACH ROW EXECUTE FUNCTION public.topic_ancestor_fill();


--
-- Name: topic topic_guard; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER topic_guard BEFORE INSERT OR DELETE OR UPDATE ON public.topic FOR EACH ROW EXECUTE FUNCTION public.topic_guard();


--
-- Name: topic topic_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER topic_updated_at BEFORE UPDATE ON public.topic FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: booklet_mapping booklet_mapping_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.booklet_mapping
    ADD CONSTRAINT booklet_mapping_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exam(id) ON DELETE CASCADE;


--
-- Name: booklet_mapping booklet_mapping_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.booklet_mapping
    ADD CONSTRAINT booklet_mapping_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.question(id) ON DELETE CASCADE;


--
-- Name: contest contest_agency_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contest
    ADD CONSTRAINT contest_agency_id_fkey FOREIGN KEY (agency_id) REFERENCES public.agency(id);


--
-- Name: contest contest_exam_board_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contest
    ADD CONSTRAINT contest_exam_board_id_fkey FOREIGN KEY (exam_board_id) REFERENCES public.exam_board(id);


--
-- Name: exam exam_answer_key_final_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_answer_key_final_document_id_fkey FOREIGN KEY (answer_key_final_document_id) REFERENCES public.source_document(id);


--
-- Name: exam exam_answer_key_preliminary_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_answer_key_preliminary_document_id_fkey FOREIGN KEY (answer_key_preliminary_document_id) REFERENCES public.source_document(id);


--
-- Name: exam exam_contest_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_contest_id_fkey FOREIGN KEY (contest_id) REFERENCES public.contest(id) ON DELETE CASCADE;


--
-- Name: exam_document exam_document_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_document
    ADD CONSTRAINT exam_document_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exam(id) ON DELETE CASCADE;


--
-- Name: exam_document exam_document_source_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_document
    ADD CONSTRAINT exam_document_source_document_id_fkey FOREIGN KEY (source_document_id) REFERENCES public.source_document(id);


--
-- Name: exam exam_exam_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_exam_document_id_fkey FOREIGN KEY (exam_document_id) REFERENCES public.source_document(id);


--
-- Name: exam_position exam_position_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_position
    ADD CONSTRAINT exam_position_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exam(id) ON DELETE CASCADE;


--
-- Name: exam_position exam_position_position_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_position
    ADD CONSTRAINT exam_position_position_id_fkey FOREIGN KEY (position_id) REFERENCES public."position"(id);


--
-- Name: passage_asset passage_asset_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_asset
    ADD CONSTRAINT passage_asset_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.asset(id);


--
-- Name: passage_asset passage_asset_passage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage_asset
    ADD CONSTRAINT passage_asset_passage_id_fkey FOREIGN KEY (passage_id) REFERENCES public.passage(id) ON DELETE CASCADE;


--
-- Name: passage passage_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passage
    ADD CONSTRAINT passage_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exam(id) ON DELETE CASCADE;


--
-- Name: position position_agency_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."position"
    ADD CONSTRAINT position_agency_id_fkey FOREIGN KEY (agency_id) REFERENCES public.agency(id);


--
-- Name: question_asset question_asset_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_asset
    ADD CONSTRAINT question_asset_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.asset(id);


--
-- Name: question_asset question_asset_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_asset
    ADD CONSTRAINT question_asset_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.question(id) ON DELETE CASCADE;


--
-- Name: question question_duplicate_of_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_duplicate_of_fkey FOREIGN KEY (duplicate_of) REFERENCES public.question(id) ON DELETE SET NULL;


--
-- Name: question question_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exam(id) ON DELETE CASCADE;


--
-- Name: question_option question_option_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_option
    ADD CONSTRAINT question_option_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.question(id) ON DELETE CASCADE;


--
-- Name: question question_passage_id_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_passage_id_exam_id_fkey FOREIGN KEY (passage_id, exam_id) REFERENCES public.passage(id, exam_id);


--
-- Name: question question_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- Name: question_topic question_topic_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_topic
    ADD CONSTRAINT question_topic_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.question(id) ON DELETE CASCADE;


--
-- Name: question_topic question_topic_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_topic
    ADD CONSTRAINT question_topic_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.topic(id);


--
-- Name: topic_ancestor topic_ancestor_ancestor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topic_ancestor
    ADD CONSTRAINT topic_ancestor_ancestor_id_fkey FOREIGN KEY (ancestor_id) REFERENCES public.topic(id) ON DELETE CASCADE;


--
-- Name: topic_ancestor topic_ancestor_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topic_ancestor
    ADD CONSTRAINT topic_ancestor_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.topic(id) ON DELETE CASCADE;


--
-- Name: topic topic_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.topic
    ADD CONSTRAINT topic_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subject(id);


--
-- PostgreSQL database dump complete
--

\unrestrict dbmate


--
-- Dbmate schema migrations
--

INSERT INTO public.schema_migrations (version) VALUES
    ('20261007000000'),
    ('20261007100000'),
    ('20261007100100'),
    ('20261007100200'),
    ('20261007100300'),
    ('20261007100400'),
    ('20261007100500'),
    ('20261007100600'),
    ('20261007200000'),
    ('20261007210000');
