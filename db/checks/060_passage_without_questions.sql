-- Texto-base que nenhuma questão usa.
select p.id as passage_id, p.exam_id
  from passage p
 where not exists (select 1 from question q where q.passage_id = p.id);
