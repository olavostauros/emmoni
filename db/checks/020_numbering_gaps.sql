-- Prova publicada com buraco na numeração das questões (esperado: do menor ao maior número sem
-- falhas; um caderno pode começar depois do 1, como o da PRF 2021, que começa no item 9).
select e.id as exam_id, e.slug as exam_slug, count(*) as questions,
       min(q.number) as min_number, max(q.number) as max_number
  from exam e
  join question q on q.exam_id = e.id
 where e.publish_status = 'published'
 group by e.id, e.slug
having count(*) <> max(q.number) - min(q.number) + 1;
