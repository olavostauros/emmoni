# 2026-10-07 — M2: classificação das 18 provas pelo agente e carga

**Marco:** M2 — Primeira ingestão

## O que foi feito
- Commit `84d55f8`: a reescrita da etapa `classify` sem Claude API (decisão 0006), que estava sem
  commit na sessão anterior, com `make gates` passando.
- Ciclo completo `classify → classify-answers.json → classify → load` rodado para as **18 provas**
  (1.496 questões). O agente classificou PRF 2018 e PF 2018 Agente diretamente; as outras 16
  provas foram classificadas por agentes derivados (forks) em paralelo, com as mesmas regras, e a
  carga (`--step load`) foi feita em sequência pelo agente principal.
- Respostas em `data/staging/<concurso>/<prova>/classify-answers.json` (18 arquivos, 252 KB),
  agora **versionadas no git** por exceção no `.gitignore` (SPECIFICATION.md §7.4 atualizado).
- Amostras das 18 provas regeneradas (`emmoni review sample`) com o status final das questões:
  `data/review/<concurso>/<prova>/amostra.html`.
- Relatório de sugestões de assunto: `docs/progress/2026-10-07-sugestoes-de-assuntos.md`
  (728 sugestões agregadas por disciplina).

## Verificação
- `make gates`: **passou** — 201 testes; ruff, mypy, seed, roundtrip das migrações e 7 checks sem
  violações (`emmoni check` limpo com as 1.496 questões carregadas).
- Resultado da carga, por status de questão (sem o seed):

  | status | questões |
  |---|---|
  | `published` (nível de questão; a prova ainda não) | 822 |
  | `review` só por classificação com confiança < 0,6 | 464 |
  | `review` por problema de extração (figura, fórmula, layout) | 210 |
  | `draft` | 0 |
  | duplicatas marcadas (`duplicate_of`) | 105 |

- **Não verificado:** a qualidade das classificações por amostragem humana (M4 exige 50 amostras
  com ≥ 90% de acerto). Nenhuma prova aprovada: `emmoni review approve` é ato humano.

## Decisões
- Nenhuma nova. A exceção do `.gitignore` segue a decisão 0006 ("respostas versionáveis e
  auditáveis").

## Problemas encontrados
- **Taxonomia fina** é o gargalo: 464 questões (31%) ficaram em `review` apenas porque nenhum
  assunto da disciplina descrevia a questão. Piores casos: provas de Delegado (PF 2018: 75 em
  revisão; PF 2021: 73), Informática (sistemas de informação, banco de dados, big data, nuvem,
  programação), Legislação Penal Especial (só tem Lei de Drogas), Direito Processual Penal (sem
  "Provas" nem "Competência"), Língua Portuguesa (redação oficial, semântica, reescrita).
- O manifesto fatia blocos mistos "Direito Penal e Processual Penal" por faixa de número; algumas
  questões ficam com a disciplina trocada (ex.: PRF 2018 Q103–105, flagrante, em `direito-penal`;
  PF 2021 Q31–33). Corrigir `subjects_by_range` nesses manifestos antes de aprovar as provas.
- PF 2025 básicos bloco I: enunciados de Estatística (Q45–52) e RL (Q53–56) perderam símbolos de
  fórmula e trazem restos de tabela ("F F F") — caso para a etapa `structure`.
- Sugestões com nomes quase iguais vindas de sessões paralelas (ex.: três variantes de
  "Navegadores"); unificar na curadoria.
- Questões em `review` só por classificação não entram na deduplicação (regra do `load`): as 105
  duplicatas marcadas são menos que as 161 de antes da classificação. Discutir no M4 se
  "sem assunto adequado" deveria ser `draft` em vez de `review`.
- `emmoni coverage` (SPECIFICATION.md §7.3 e §8) ainda não existe no CLI.

## Próximo passo
- Humano: abrir as 18 amostras em `data/review/` e aprovar com `emmoni review approve
  <concurso>/<prova>`; com isso as 822 questões aparecem no esquema `api` e o M2 fica pronto.
- Antes de aprovar, corrigir `subjects_by_range` dos manifestos com blocos mistos e rerodar
  `validate → classify → load` dessas provas (as respostas existentes são reaproveitadas).
- M3 — crawler do Cebraspe.
- M4 — crescer a taxonomia a partir do relatório de sugestões e reclassificar as 464 questões
  (basta editar as respostas e rerodar `classify` + `load`).
