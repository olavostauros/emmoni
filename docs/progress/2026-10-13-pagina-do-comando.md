# 2026-10-13 — Página do comando na amostra

**Marco:** M5

Worktree `agent-a9da15c1a74acec18`, branch `worktree-agent-a9da15c1a74acec18`, sobre `15e4fed`,
em paralelo com o primeiro ciclo autônomo no checkout principal. Feito pelo hefesto; integrado
pela sessão coordenadora.

## O que foi feito
- Próximo passo 9 do `STATUS.md`: `emmoni review sample` inclui a página onde começa o comando do
  grupo de itens quando ela é anterior à da questão (decisão 0027, commit `5eef346`).
- Parser grava `command_page`; coluna nova `question.command_page` (migração
  `20261013000000_question_command_page.sql`), nula, fora do esquema `api`, do contrato e da
  impressão digital da aprovação: nenhuma prova volta para `review`.
- Questões já carregadas (coluna nula): o grupo é achado pelo primeiro parágrafo repetido com
  "julg", e a amostra começa na página do item anterior ao grupo.
- Testes em `tests/test_review.py` e `tests/test_parser_cebraspe.py`.

## Verificação
- `make gates`: **passou** — 384 testes, lint, ida e volta das migrações, 7 checks sem violação.
- PCDF 2026 q96 conferida só lendo o banco: a amostra traz as p. 11–13 e o comando está na p. 11.
- Não verificado: nenhum `load` rodou, então `command_page` está nula em todas as linhas reais;
  o caminho pelo banco não acha o grupo quando o item completa a frase do comando; o
  `amostra.html` continua só com a página da questão.

## Decisões
- [0027 — Página do comando na amostra](../decisions/0027-pagina-do-comando-na-amostra.md)

## Problemas encontrados
- A migração foi aplicada no Postgres compartilhado pelo `make gates` do worktree.
- A p. 11 do PDF guardado como caderno do PCDF 2026 (`data/raw/7cffe418…pdf`) traz
  "JUSTIFICATIVA - Certo/Errado ..." abaixo de cada item: pode ser o caderno com justificativas
  da banca no lugar da prova. A investigar.

## Próximo passo
- Conferir se o texto das justificativas entrou em alguma questão do PCDF 2026.
