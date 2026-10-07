-- Prova publicada com buraco na numeração das questões (esperado: 1..N sem falhas).
select e.id as exam_id, e.slug as exam_slug, count(*) as questions, max(q.number) as max_number
  from exam e
  join question q on q.exam_id = e.id
 where e.publish_status = 'published'
 group by e.id, e.slug
having count(*) <> max(q.number);
