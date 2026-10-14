-- Caractere de substituição (U+FFFD, "�") em questão publicada: glifo sem mapeamento que a
-- extração não resolveu (fonte de símbolos, decisão 0023). No enunciado, nas alternativas e no
-- texto-base. A questão com esse caractere vai para `review` (o parser a marca como fórmula com
-- glifos não mapeados) até a extração ou uma revisão em `ingest/ocr/` dar o texto certo.
with texts as (
    select 'statement' as kind, q.id::text as id, q.statement_md as body
      from question q
     where q.publish_status = 'published'
    union all
    select 'option', o.question_id::text || '/' || o.letter, o.body_md
      from question_option o
      join question q on q.id = o.question_id
     where q.publish_status = 'published'
    union all
    select 'passage', p.id::text, p.body_md
      from passage p
     where exists (
               select 1 from question q
                where q.passage_id = p.id and q.publish_status = 'published'
           )
)
select kind, id
  from texts
 where strpos(body, U&'\FFFD') > 0
 order by kind, id;
