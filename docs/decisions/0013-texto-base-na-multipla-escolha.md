# 0013 — Texto-base na múltipla escolha só para quem o cita

**Data:** 2026-10-08 · **Marco:** M4 (publicação das provas)

## Contexto

O revisor de assuntos viu quatro questões com texto-base errado. A causa era uma regra do parser
de múltipla escolha: o texto aberto entre duas questões valia para **todas** as questões seguintes,
até a próxima abertura. Em 44 provas de múltipla escolha, 899 questões carregavam um texto que não
citavam (física em questões de medicina legal, texto de português em direito empresarial), e as
figuras desse texto mandavam questões sem figura para `review`. Além disso, PC/PE 2023 traz uma
tabela `||JUSTIFICATIVAS||` depois de cada questão, que o parser não reconhecia (plural, e a tabela
fica na margem): a justificativa da questão anterior virava o texto-base da seguinte.

## Decisões

1. Na múltipla escolha do Cebraspe, a questão que usa um texto o cita ("texto 2A1-I",
   "figura 5A2", "situação hipotética 12A3-I"). O texto-base vale para a **primeira questão depois
   dele** e para **as que citam o rótulo** (a chave ou o título da primeira linha do texto). As
   demais ficam sem texto-base.
2. Título de bloco em negrito ("**Atualidades e conhecimentos...**") entre questões não é texto-base.
3. A tabela `||JUSTIFICATIVAS||` passa pelo fluxo e a múltipla escolha pula tudo até o próximo
   título de questão; a regex aceita o plural.
4. Certo/errado não muda: o comando do grupo continua valendo para todos os itens do grupo.

## Consequências

- As 44 provas de múltipla escolha foram ressegmentadas e recarregadas; menos questões em
  `review` (as figuras do texto não se espalham mais).
- Questão que usa o texto sem citar o rótulo e não é a primeira do grupo fica sem texto-base.
  A amostragem por prova é onde isso aparece.
