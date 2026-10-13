# 0027 — Página do comando na amostra

**Data:** 2026-10-13 · **Marco:** M5

## Contexto

A amostra por prova (`emmoni review sample`) grava as páginas do PDF de cada questão: da página
onde começa o texto-base (ou a anterior, quando há texto-base) até a seguinte à da questão. No
certo/errado do Cebraspe, o **comando** do grupo ("Julgue os itens a seguir...") abre o enunciado
de cada item, mas pode estar numa página anterior à do item, sem texto-base. Foi o caso do PCDF
2026 q96 (comando na página 11, item na 12): o revisor não viu a página do comando e marcou `ok`.
O banco não guardava a página do comando.

## Decisão

1. O parser do Cebraspe grava em cada item certo/errado a página onde começa a abertura do grupo
   que contém o comando (`RawQuestion.command_page`, staging). Quando há situação ou texto antes do
   comando no mesmo trecho, vale a página do início dela: no pior caso, uma página a mais.
2. Coluna nova `question.command_page` (nula), gravada pelo `load`. Fica fora do esquema `api`, do
   contrato e da impressão digital da aprovação: não muda o que o front-end vê nem republica prova.
3. A amostra começa na menor das páginas: a da questão (ou a anterior, com texto-base), a do
   texto-base e a do comando. Página repetida não entra duas vezes.
4. Questões carregadas antes da coluna (`command_page` nula): o comando sai do próprio banco. Os
   itens seguidos com o mesmo primeiro parágrafo (o comando, que tem "julg") são um grupo; o
   comando fica entre o item anterior ao grupo e o primeiro item do grupo, e a página do item
   anterior é o limite usado.

## Consequências

- A coluna fica nula nas provas já carregadas até o próximo `load`; até lá vale o item 4, que não
  cobre comando sem parágrafo próprio (o item que completa a frase do comando, "julgue ... :" +
  item): ali o grupo não é reconhecido e a amostra começa na página do item anterior.
- A amostra pode trazer uma página a mais que o necessário; nunca uma a menos quando o dado
  existe.
