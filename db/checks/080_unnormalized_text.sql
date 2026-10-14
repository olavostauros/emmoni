-- Texto fora da normalização da gravação (docs/content-format.md): espaço nas pontas ou fora de
-- Unicode NFC, no enunciado, nas alternativas e no texto-base.
with texts as (
    select 'passage' as kind, p.id::text as id, p.body_md as body from passage p
    union all
    select 'statement', q.id::text, q.statement_md from question q
    union all
    select 'option', o.question_id::text || '/' || o.letter, o.body_md from question_option o
)
select kind, id
  from texts
 where body ~ '^[[:space:] ]|[[:space:] ]$'
    or body is not nfc normalized
 order by kind, id;
