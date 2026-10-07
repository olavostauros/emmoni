-- Múltipla escolha publicada com menos de 4 alternativas ou com letras fora de sequência (A, B, C...).
select q.id as question_id,
       coalesce(string_agg(o.letter, '' order by o.letter), '') as letters
  from published_question q
  left join question_option o on o.question_id = q.id
 where q.type = 'multiple_choice'
 group by q.id
having count(o.letter) < 4
    or string_agg(o.letter, '' order by o.letter) <> left('ABCDE', count(o.letter)::int);
