-- Referência asset:<sha256> em conteúdo publicado sem asset cadastrado e vinculado
-- (question_asset para enunciado e alternativas, passage_asset para texto-base).
with refs as (
  select q.id as question_id, null::uuid as passage_id, m[1] as sha256
    from published_question q,
         regexp_matches(q.statement_md, 'asset:([0-9a-f]{64})', 'g') as m
  union all
  select o.question_id, null::uuid, m[1]
    from question_option o
    join published_question q on q.id = o.question_id,
         regexp_matches(o.body_md, 'asset:([0-9a-f]{64})', 'g') as m
  union all
  select null::uuid, p.id, m[1]
    from passage p,
         regexp_matches(p.body_md, 'asset:([0-9a-f]{64})', 'g') as m
   where exists (select 1 from published_question q where q.passage_id = p.id)
)
select r.question_id, r.passage_id, r.sha256
  from refs r
 where not exists (
   select 1
     from asset a
    where a.sha256 = r.sha256
      and (exists (select 1 from question_asset qa
                    where qa.asset_id = a.id and qa.question_id = r.question_id)
           or exists (select 1 from passage_asset pa
                       where pa.asset_id = a.id and pa.passage_id = r.passage_id)));
