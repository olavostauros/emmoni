# 2026-10-07 — M2: classificação pelo agente, sem Claude API

**Marco:** M2 — Primeira ingestão

## O que foi feito
- Decisão 0006: o pipeline não chama API de LLM. Quem classifica é o agente que opera o
  repositório, por arquivos no staging da prova.
- `ingest/classify.py` reescrito: a etapa grava `classify-tasks.json` (questões sem resposta, com
  disciplina, `allowed_topics`, texto-base, enunciado e as instruções de `classify@1.md`) e lê
  `classify-answers.json` (`{número: {topics: [{path, confidence}], suggested_topic}}`). Valida com
  pydantic e com a taxonomia; grava `topics.json`. Assunto fora da disciplina → `review`.
- Removidos: SDK `anthropic` (pyproject e uv.lock), `ANTHROPIC_API_KEY`, `EMMONI_LLM_MODEL`,
  cache `llm-cache/`, verificação de credencial no pipeline. Nova variável `EMMONI_CLASSIFIER`
  (padrão `agent`).
- SPECIFICATION.md §1, §2, §7.3, §7.4 e §9 atualizados no mesmo commit.

## Verificação
- `make gates`: **passou** — 201 testes; ruff, mypy, seed, roundtrip das migrações e 7 checks
  limpos.
- `emmoni ingest prf-2018 --step classify` rodou sem pedir credencial e gerou 120 tarefas em
  `data/staging/prf-2018/policial/classify-tasks.json`.
- **Não verificado:** o ciclo completo tarefas → respostas → `topics.json` → `load` numa prova
  real (só nos testes unitários). Nenhuma questão real classificada ainda.

## Próximo passo
- Classificar o PRF 2018 (o agente responde as 120 tarefas), rerodar `classify` e `load`, conferir
  que as questões sem pendência viram `published`. Depois as outras 17 provas.
