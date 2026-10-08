# 0010 — Taxonomia do M4 e questão sem assunto confiante fica `draft`

**Data:** 2026-10-07 · **Marco:** M4

## Contexto

A taxonomia do M2 era rasa (56 disciplinas, ~250 assuntos, metade com um ou dois assuntos). No M2,
464 das 1.496 questões ficaram em `review` só porque nenhum assunto descrevia a questão, misturando
lacuna da taxonomia com defeito de extração e tirando essas questões da deduplicação. Após a
ingestão dos 36 manifestos (decisão 0009) havia 5.470 questões a classificar (4.976 novas e 494 do
M2 sem assunto confiante).

## Decisões

1. **Taxonomia ampliada para 863 assuntos** em `db/taxonomy/`, curada a partir do relatório de
   sugestões do M2, das dúvidas registradas na decisão 0009 e dos conteúdos dos editais policiais.
   Nenhum `path` existente foi removido (as respostas antigas continuam válidas). Lei de Execução
   Penal e crimes do CTB também existem em `legislacao-penal-especial`, porque a disciplina vem do
   manifesto e essas leis aparecem nesse bloco em várias provas.
2. **Resposta sem assunto com confiança ≥ 0,6 não é revisão.** A questão fica sem assunto
   (`draft` no `load`), a sugestão é registrada em `topics.json` (`unresolved` + `suggestions`) e
   a questão **volta às tarefas** do `classify`, para ser reclassificada quando a taxonomia crescer.
   Assunto de outra disciplina continua `review` (resposta inválida). Com isso, `review` volta a
   significar só defeito de extração, e as questões `draft` entram na deduplicação.
3. **Classificação em paralelo por agentes** derivados, um por grupo de provas, com scripts de
   apoio fora do repositório (impressão compacta das tarefas; validação e mesclagem das respostas
   contra `allowed_topics` antes de rerodar `--step classify`). As respostas continuam versionadas
   em `data/staging/*/*/classify-answers.json`.
4. **Amostragem da classificação:** `emmoni review topics --n 50` sorteia (determinístico) 50
   questões classificadas de todas as provas reais e gera `data/review/assuntos/amostra.{json,md}`;
   o revisor grava `verdict` (`ok`/`wrong`) e `--report` calcula o acerto (critério do M4: ≥ 90%).

## Consequências

- SPECIFICATION.md §7.3 (regra do `classify`) e §8 (amostragem de assuntos) atualizados.
- Reclassificar uma prova inteira exige apagar as respostas em `classify-answers.json`; só as
  questões sem assunto confiante são retarefadas automaticamente.
