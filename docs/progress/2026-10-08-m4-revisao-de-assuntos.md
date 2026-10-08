# 2026-10-08 — M4 pronto: revisão da amostra de assuntos pelo agente

**Marco:** M4

## O que foi feito
- Amostra de 50 classificações (`data/review/assuntos/amostra.json`, semente `assuntos`)
  conferida por um agente revisor em contexto separado do `classify` (decisão 0011): leu só
  `amostra.md`, `amostra.json` e `db/taxonomy/*.yaml`; não abriu `classify-answers.json` nem o
  prompt. `reviewed_by: claude-opus-5-5` em todos os itens.
- `emmoni review topics --report`: **50/50 conferidas, 49 corretas (98%)**.
- O único `wrong` — pf-2021/agente, questão 2 (deslocamento do advérbio "até"), classificada como
  `lingua_portuguesa.interpretacao_de_texto` — foi corrigido na origem: resposta em
  `data/staging/pf-2021/agente/classify-answers.json` trocada por `lingua_portuguesa.reescrita`
  (0,9) e `lingua_portuguesa.morfologia.adverbio` (0,7); `--step classify` e `--step load`
  rerodados na prova. A prova segue aprovada (92 `published`, 28 `review`, como antes).

## Verificação
- `make gates`: **passou** — 312 testes; lint, roundtrip de migrações e 7 checks sem violação.
- Critério 1 do M4 (≥ 90% das publicadas com assunto): 5.043/5.043 questões reais `published`
  com assunto (100%).
- Critério 2 (amostra de 50 com ≥ 90% de acerto): 98%. **M4 pronto.**
- **Não verificado:** a amostra não foi reamostrada depois da correção (o `wrong` corrigido não
  muda o resultado); nenhuma conferência humana (decisão 0011).
- `amostra.json` está em `data/` (no `.gitignore`): os vereditos só existem nesta máquina.

## Decisões
- Nenhuma nova.

## Problemas encontrados
Defeitos de extração vistos pelo revisor (não de assunto), todos em provas ainda sem amostragem,
portanto fora do `api`:
- pcgo-2016 (escrivão, básicos) q14: texto-base sobre educação e crime, item sobre o cerrado
  goiano.
- pcpe-2023/p1-cargo-1 q6: texto-base contém um bloco "JUSTIFICATIVAS" de outra questão.
- cbmro-2022/oficial q84: texto-base cita a figura de um pórtico que não tem relação com o item.
- pcma-2017-delegado q99: caso de João/Estela sem relação, anteposto ao item.
São texto-base atribuído à questão errada ou com sobra; aparecem na amostragem por prova.

Casos limítrofes marcados `ok` pelo revisor (granularidade): pf-2025/delegado q55 e q10,
pf-2021/agente q107 e q75, prf-2021 q94.

## Próximo passo
- M5 só depois de publicar as 90 provas sem amostragem (`emmoni review sample/approve --by`),
  começando pelas quatro acima, cuja segmentação de texto-base precisa de correção.
