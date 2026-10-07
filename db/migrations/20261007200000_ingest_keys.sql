-- migrate:up
-- Ingestão (M2, decisão 0005): motivo de revisão por questão e chave natural do texto-base.
set local search_path = public, ext;

alter table question
  add column review_reasons text[] not null default '{}';
comment on column question.review_reasons is
  'Motivos da etapa validate para a questão ficar em review (vazio = sem pendências).';

-- Rótulo do texto-base na prova ("2A1-I") ou "g<primeiro item>" para situações sem rótulo.
-- Permite recarregar a prova sem trocar o id do texto-base.
alter table passage
  add column source_key text check (source_key <> '');
alter table passage
  add constraint passage_exam_source_key unique (exam_id, source_key);

-- migrate:down
set local search_path = public, ext;

alter table passage drop constraint passage_exam_source_key;
alter table passage drop column source_key;
alter table question drop column review_reasons;
