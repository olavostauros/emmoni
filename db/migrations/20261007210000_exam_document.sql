-- migrate:up
-- Vários PDFs por tipo de documento numa prova (decisão 0009): o gabarito definitivo do PCDF 2019
-- vem em dois PDFs (básicos e específicos) para um único caderno. As colunas
-- exam.*_document_id continuam apontando para o primeiro PDF de cada tipo.
set local search_path = public, ext;

create table exam_document (
  exam_id            bigint not null references exam on delete cascade,
  source_document_id bigint not null references source_document,
  kind               document_kind not null,
  position           smallint not null default 1 check (position > 0),
  primary key (exam_id, source_document_id)
);
comment on table exam_document is
  'Todos os PDFs de uma prova (caderno e gabaritos), inclusive quando um tipo tem mais de um.';
create index exam_document_source_document_idx on exam_document (source_document_id);

insert into exam_document (exam_id, source_document_id, kind, position)
select id, exam_document_id, 'exam'::document_kind, 1 from exam where exam_document_id is not null
union all
select id, answer_key_preliminary_document_id, 'answer_key_preliminary'::document_kind, 1
  from exam where answer_key_preliminary_document_id is not null
union all
select id, answer_key_final_document_id, 'answer_key_final'::document_kind, 1
  from exam where answer_key_final_document_id is not null
on conflict do nothing;

grant select on exam_document to emmoni_web;
grant select, insert, update, delete on exam_document to emmoni_ingest;

-- migrate:down
drop table exam_document;
