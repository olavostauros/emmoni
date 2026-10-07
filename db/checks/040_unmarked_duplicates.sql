-- Questões publicadas com o mesmo statement_hash, nenhuma marcada como duplicata da outra.
select statement_hash, count(*) as questions, array_agg(id order by id) as question_ids
  from published_question
 group by statement_hash
having count(*) > 1;
