# 0005 — Primeira ingestão: catálogo curado, modelagem do Cebraspe e fila de revisão

**Data:** 2026-10-07 · **Marco:** M2

## Contexto

A primeira prova real (PF 2021, Agente) mostrou o que a especificação ainda não dizia: de onde vêm
as bancas, órgãos e cargos reais; como representar o "comando" dos itens certo/errado; onde guardar
o motivo de uma questão ir para revisão; e como recarregar uma prova sem trocar ids.

## Decisões

1. **Catálogo curado em `db/catalog.yaml`**, carregado por `emmoni catalog load` (upsert por slug,
   como a taxonomia). Manifestos só citam slugs que existem nele (testado). O seed continua com o
   próprio catálogo, compatível por slug.
2. **Comando no enunciado.** Pela regra do Cebraspe, cada item depende do comando que o antecede.
   O comando ("Com relação a X, julgue os itens a seguir.") é o primeiro parágrafo de cada
   `statement_md` do grupo. O texto rotulado ("Texto 2A1-I") ou a situação hipotética sem rótulo
   vira `passage`. Situação que remete a um texto rotulado entra no enunciado junto com o comando.
3. **Nada some em silêncio.** O parser marca o que não reproduz com fidelidade (`figure`,
   `formula`, `layout`, `underline`, `no_command`, `orphan_text`); `validate` traduz as marcas e as
   demais regras em motivos, gravados em **`question.review_reasons`** (nova coluna). Questão com
   motivo vai para `review`.
4. **`passage.source_key`** (rótulo da banca ou `g<primeiro item>`), único por prova: chave
   natural para o `load` ser idempotente sem trocar o id do texto-base.
5. **Status no `load`:** `review` se há motivo; `published` se não há motivo e há assunto; `draft`
   se falta assunto. A prova nunca é publicada pelo `load`, só depois da amostragem.
6. **Gabarito sem preliminar.** Quando a banca só mantém o definitivo no site, `answer_preliminary`
   fica nulo e `answer_status` é `valid` ou `annulled` (contrato v1.1).
7. **Classificação por assunto** fica numa etapa própria que grava `topics.json` no staging; o
   `load` usa o arquivo se existir. Nesta entrega a etapa `classify` ainda não está implementada.

## Consequências

- Questões com fórmula, figura ou tabela ficam em revisão até existir a etapa `structure` (LLM) e a
  exportação de imagens como assets.
- Uma alteração de gabarito por recurso só é detectável quando o preliminar existe (ou, no futuro,
  lendo as "justificativas de alteração de gabarito").
