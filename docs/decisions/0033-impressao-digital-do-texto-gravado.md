# 0033 — Impressão digital do texto como gravado

**Data:** 2026-10-14 · **Marco:** M5

## Contexto

A impressão digital da aprovação (decisão 0016) usava o `statement_hash` de cada questão, que é
normalizado para a deduplicação: sem marcação, pontuação nem quebra de parágrafo. Mudança só de
itálico, negrito, código ou de parágrafo/verso — o que as emendas da 0013 e da 0020 vêm fazendo —
não devolvia a prova publicada a `review`, e a coordenadora listava à mão o que o minos devia
reamostrar. Além disso, `emmoni review sample --also` descartava sem aviso as questões em `review`.

## Decisão

- **Versão 2 da impressão** (`FINGERPRINT_VERSION = 2`, em `ingest/review.py`): por questão, o
  número, se está em `review` e, fora dela, o texto como gravado — enunciado, alternativas (letra e
  corpo) e texto-base em Markdown, com marcação e parágrafos —, o tipo, os gabaritos preliminar e
  final, o status do gabarito, a disciplina e os sha256 dos assets da questão e do texto-base.
  Assuntos continuam fora (amostragem própria); questão em `review` continua valendo só pelo número
  e pela pendência (adendo da 0016).
- O registro em `ingest/approvals/` ganha `fingerprint_version`. `review approve` grava a versão 2.
- **Transição:** registro sem `fingerprint_version` é da versão 1 e o `reconcile` o confere na
  versão 1 enquanto o conteúdo não mudar. A impressão gravada nunca é reescrita: recalcular a
  versão 2 sobre o conteúdo atual suporia que ele é exatamente o que o minos aprovou, e isso não
  dá para provar (uma mudança só de marcação depois da aprovação passaria despercebida). Nenhuma
  prova é reaprovada em massa; cada uma passa à versão 2 na próxima aprovação do minos.
- `review sample --also` avisa (stderr) cada questão descartada e o motivo: em `review` (com os
  motivos gravados) ou inexistente na prova.

## Consequências

- Na data, as 115 aprovações são da versão 1 e conferem com o banco; nenhuma prova mudou de status.
- Até cada prova ser reaprovada, mudança só de marcação ou parágrafo nela ainda não a tira do ar: a
  lista manual de reamostragem do STATUS continua valendo para as provas com registro da versão 1.
- Prova com registro da versão 2: qualquer mudança no que o `api` mostra da questão (fora os
  assuntos) a devolve a `review` no próximo `load`.
