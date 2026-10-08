# 0002 — Contrato com o front-end: busca, paginação e facetas

**Data:** 2026-10-07 · **Marco:** M1

## Contexto

O M1 entrega o esquema `api` (SPECIFICATION.md §6) para o agente de front-end trabalhar sem
conhecer as tabelas internas, com p95 < 150 ms na busca e < 300 ms nas facetas a 100 mil questões.

## Decisões

1. **Respostas em `jsonb`**, com um documento de questão "achatado" (`exam_board_slug`,
   `agency_name`...) igual em `search_questions`, `get_question` e na view `api.question`. Mais
   simples de consumir do que objetos aninhados, e uma única fonte (`question_docs`).
2. **Funções `SECURITY DEFINER`** com `search_path` fixo para a busca e as facetas. O `emmoni_web` não
   enxerga `public`, e os filtros por cargo e assunto precisam de tabelas internas. O SQL é montado
   dinamicamente (só com os filtros presentes, para o planner) e todo valor do usuário entra via
   `format('%L')`, depois de validado. Há teste com entrada hostil.
3. **Ordem fixa por recência** (ano ↓, concurso, prova, número), também com texto. É o que os bancos
   de questões fazem, e permite paginação keyset com um cursor simples (base64 de JSON com os quatro
   valores da última linha). Relevância fica para uma versão futura do contrato, se pedida.
4. **`total` em toda busca.** Custa uma contagem extra, cabe na meta e o site sempre mostra "N questões".
5. **Facetas disjuntivas**: cada faceta é contada com todos os filtros menos o dela, que é o
   comportamento esperado de checkboxes de filtro.
6. **Assuntos identificados pelo `path`** (sem coluna `slug`), imutável, com o fecho transitivo em
   `topic_ancestor` mantido por trigger. Sem ele, a faceta de assuntos levava 390 ms a 100 mil
   questões; com ele, 93 ms.
7. **Faceta de cargos agregada por prova** antes de juntar com os cargos (86 → 16 ms). Funciona
   porque numa prova um slug de cargo aparece uma vez (o check 070 pega cargo de outro órgão).
8. **`statement_hash` inclui alternativas e texto-base**, não só o enunciado: enunciados genéricos se
   repetem entre questões diferentes e virariam falsas duplicatas.
9. **Seed gerado por script** (`scripts/build_seed.py`), com IDs determinísticos (uuid5) e hash
   calculado pelo mesmo código da ingestão. As 65 questões foram escritas para o seed; o catálogo
   (bancas, órgãos, cargos, taxonomia) é real.
10. **ruff sem E501.** O `ruff format` cuida do comprimento das linhas de código; SQL e textos em
    strings podem passar de 100 colunas.

## Resultado do `make bench` (2026-10-07, 100.065 questões)

| Função | Caso | p95 (ms) | Meta |
|---|---|---:|---:|
| search_questions | pior caso (página 51 via cursor) | 66 | 150 |
| search_questions | texto | 11 | 150 |
| facet_counts | sem filtros | 281 | 300 |
| facet_counts | banca | 189 | 300 |
| facet_counts | texto | 46 | 300 |

## Consequências

- **Folga pequena nas facetas sem filtro** (281 de 300 ms). Antes do M6, a otimização prevista é
  contar numa só passada, com `GROUPING SETS`, as facetas cujo filtro não está ativo, já que elas
  compartilham a mesma condição.
- Mudar o formato do documento ou a ordem é mudança incompatível: exige versão 2 do contrato.
- `get_question` devolve `null` para questão não publicada, anulada ou não: o site não distingue
  "não existe" de "ainda não publicada".
