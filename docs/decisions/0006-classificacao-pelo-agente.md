# 0006 — Classificação pelo próprio agente, sem Claude API

**Data:** 2026-10-07 · **Marco:** M2

## Contexto

A etapa `classify` foi implementada chamando a Claude API pelo SDK `anthropic`, com cache de
respostas em disco. Isso criou um bloqueio artificial: a ingestão parou à espera de uma credencial
(`ANTHROPIC_API_KEY`) que o projeto não precisa ter. Quem opera o repositório já **é** um LLM (o
agente de banco de dados, em Claude Code). Pedir uma chave para o código chamar outro Claude por
fora é redundante, custa tokens e cria uma dependência de rede e de segredo no pipeline.

## Decisão

1. O pipeline **não chama API de LLM nenhuma**. O SDK `anthropic` sai do `pyproject.toml`;
   `ANTHROPIC_API_KEY` e `EMMONI_LLM_MODEL` saem do ambiente; o cache `llm-cache/` deixa de existir.
2. Etapas que precisam de julgamento de LLM (`classify` agora, `structure` depois) trabalham por
   **arquivos no staging da prova**: a etapa grava um arquivo de **tarefas** (o que falta decidir,
   com as instruções do prompt versionado e as opções permitidas) e lê um arquivo de **respostas**
   escrito pelo agente. A etapa valida as respostas com pydantic e com as regras do domínio (assunto
   só da disciplina da questão, confiança em [0, 1], no máximo 3 assuntos) e grava a saída normal
   (`topics.json`). Rerodar com as mesmas respostas é idempotente.
3. Para o `classify`: `classify-tasks.json` → agente → `classify-answers.json` → `topics.json`.
   Resposta inválida derruba a etapa com o nome da questão; assunto fora da disciplina ou confiança
   < 0,6 manda a questão para `review`; questão sem resposta fica `draft` no `load`.
4. `EMMONI_CLASSIFIER` (padrão `agent`) identifica quem respondeu, gravado em `topics.json` e,
   no banco, `question_topic.origin = 'llm'` continua valendo (o agente é um LLM).

## Consequências

- Nenhum segredo, nenhuma rede e nenhum custo por token no pipeline. Os testes continuam sem LLM.
- Classificar uma prova é trabalho do agente na sessão: ler o arquivo de tarefas, escrever as
  respostas, rerodar a etapa. As respostas ficam no staging (versionáveis e auditáveis).
- Trocar o agente por outro modelo ou por uma pessoa não muda o código: só quem escreve o arquivo
  de respostas e o valor de `EMMONI_CLASSIFIER`.
