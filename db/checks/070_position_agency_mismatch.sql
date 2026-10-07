-- Prova ligada a um cargo de outro órgão que não o do concurso.
select ep.exam_id, ep.position_id
  from exam_position ep
  join exam e on e.id = ep.exam_id
  join contest c on c.id = e.contest_id
  join position po on po.id = ep.position_id
 where po.agency_id <> c.agency_id;
