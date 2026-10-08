# 2026-10-07 — M2: aprovação das 18 provas e correção do PRF 2018

**Marco:** M2 — Primeira ingestão (concluído)

## O que foi feito
- Humano conferiu as 18 amostras em `data/review/`; o agente rodou `emmoni review approve` para
  cada prova. Todas as 18 provas estão `published`; 784 questões visíveis no esquema `api`
  (65 do seed + 719 reais).
- `ingest/manifests/prf-2018.yaml`: a faixa 101–107 (`direito-penal`) foi dividida em 101–102
  (descaminho, Direito Penal), 103–105 (prisão em flagrante, Direito Processual Penal) e 106–107
  (legalidade, Direito Penal). Respostas de classificação das Q103–105 refeitas em
  `data/staging/prf-2018/policial/classify-answers.json` (`prisao.prisao_em_flagrante`, 0,9).
  Rerodado `validate → classify → load` só para `prf-2018 --exam policial`: 88 publicáveis (eram 86).
- PF 2021 Q31–33, citado no STATUS anterior, já estava corrigido no manifesto e no banco; nada a fazer.
- Levantamento das **105 duplicatas**: todas do PF 2021 — o bloco comum de conhecimentos básicos
  aparece nas provas de agente, escrivão e papiloscopista; 62 da prova de escrivão e 43 da de
  papiloscopista apontam (`duplicate_of`) para a cópia de agente, que é a canônica. PF 2018 não tem
  bloco comum (textos diferentes por cargo; 0 coincidências de enunciado), e PF 2025 já separa os
  cadernos básicos. Comportamento conforme SPECIFICATION.md §5/§7: nada a corrigir.

## Verificação
- `make gates`: **passou** — 201 testes; 7 checks sem violações (`040_unmarked_duplicates` = 0).
- Reaplicar a carga do PRF 2018 não alterou `exam.publish_status` (o `load` não toca na prova):
  confirmado no banco.
- **Não verificado:** a aprovação humana em si (foi feita fora do repositório, pela pessoa); o
  agente só executou o comando.

## Decisões
- Nenhuma nova.

## Problemas encontrados
- `emmoni` exige `DATABASE_URL` no ambiente mesmo com os valores padrão do Makefile; fora do `make`
  é preciso exportar a URL (ou ter um `.env`).
- O registro de aprovação (`sample.json`, com `approved_by`/`approved_at`) é ignorado pelo git.
  A rastreabilidade da aprovação vive só no banco de desenvolvimento. Ver STATUS.md.
- Ao crescer a taxonomia no M4, as 462 questões em `review` só por classificação voltam à
  deduplicação; esperar o número de duplicatas subir (161 antes da classificação).

## Próximo passo
- M3 — crawler do Cebraspe.
