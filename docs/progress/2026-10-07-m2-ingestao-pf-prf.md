# 2026-10-07 — M2: ingestão de PF e PRF, revisão e classificação

**Marco:** M2 — Primeira ingestão

## O que foi feito
- `d561d75` — `emmoni review list|show|sample|approve`: a amostra sorteia questões sem pendência e
  gera `data/review/<concurso>/<prova>/amostra.html`, com cada questão ao lado da página do PDF.
  A aprovação exige a amostra e registra quem aprovou.
- `0d511cd`, `b3f3a5c`, `c09a0ed`, `ab3b64e`, `e70d51e` — manifestos e ingestão de **5 concursos,
  18 provas**: PF 2021 (4 cargos), PF 2018 (4 cargos), PF 2025 (Bloco I, Bloco II, específicos
  de Agente, Escrivão e Papiloscopista; Delegado), PRF 2021 (itens 9–120 + inglês e espanhol) e
  PRF 2018. Disciplinas por faixa conferidas lendo os itens.
- Parser do Cebraspe generalizado para os layouts de 2018 a 2025: numeração de linhas nos textos,
  marcador "PROVA OBJETIVA" com e sem tracinhos, itens que completam a frase da abertura, comandos
  sem "julgue" e em inglês/espanhol, itens que são só figura, réguas duplas, cabeçalhos,
  caracteres de controle e índices (fonte menor) como sinal de fórmula.
- Manifesto aceita `first_number`; check 020 aceita caderno que começa depois do 1.
- Questões em revisão ficam fora da deduplicação (conteúdo incompleto).
- Taxonomia: 31 disciplinas (só o necessário para as provas; assuntos ainda rasos — M4).
- `dcf68a2` — etapa `classify` (Claude API, saída estruturada com `enum` dos assuntos, cache em
  disco, testes com respostas gravadas).

## Números (banco de desenvolvimento)
- 1.496 questões reais; 210 em `review` (com motivo), 161 duplicatas entre cargos, o resto
  `draft` à espera de assunto. Nenhuma prova publicada.

## Verificação
- `make gates`: **passou** — 201 testes; ruff, mypy e checagem do seed limpos; roundtrip das
  migrações ok; 7 checks sem violação.
- A cada mudança do parser, todas as provas já carregadas foram reprocessadas e comparadas com o
  banco: nenhuma mudança de enunciado não intencional.
- Conferência visual (eu, não humana) de itens contra a página do PDF: PF 2021 questão 35,
  PF 2018 Delegado questões 47 e 99.
- **Não verificado:** a amostragem humana (amostras geradas para as 18 provas, nenhuma aprovada);
  a classificação contra a API real (sem credencial nesta máquina); datas de aplicação de
  PF 2018, PF 2025 e PRF (omitidas nos manifestos).

## Problemas encontrados
- DPF 2014: a API do Cebraspe responde 500 para `eventos/DPF_14_AGENTE`. Concursos anteriores a
  2014 estão em `cespe.unb.br`, fora das fontes.
- O `claude-sonnet-5-5` rejeita `tool_choice` forçado: a classificação usa `output_config.format`.
- O PDF do PF 2025 tem o erro "jugue os itens" num comando oficial; o parser aceita.

## Próximo passo
- Credencial da Claude API → `emmoni ingest <concurso> --step classify` e `--step load` → as
  questões sem pendência viram `published`.
- Aprovação humana das amostras (`emmoni review approve <concurso>/<prova>`). Depois disso o M2
  está pronto.
