-- Questão publicada sem nenhum assunto.
select q.id as question_id
  from published_question q
 where not exists (select 1 from question_topic qt where qt.question_id = q.id);
