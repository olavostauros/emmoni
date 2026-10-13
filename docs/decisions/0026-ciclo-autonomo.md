# 0026 — Ciclo autônomo: os agentes trabalham sem perguntar ao dono

**Data:** 2026-10-13 · **Marco:** M5

## Contexto

O dono pediu que os agentes trabalhem continuamente, sem lhe fazer perguntas. Uma auditoria do
contexto dos agentes (AGENTS.md, `.claude/agents/*.md`, decisões 0011, 0019, 0022 e 0024) achou
os pontos em que o trabalho parava esperando uma pessoa:

- a regra "uma sessão por vez no banco — em dúvida, pergunte ao dono" (AGENTS.md, hefesto, minos);
  resolvida pela trava da decisão 0025;
- commit e PR só "quando pedidos" (coordenadora);
- o atlas pedia o sim do dono antes de cada recurso na nuvem;
- nada roda sem uma sessão aberta pelo dono: não há laço nem timer (o do crawl, `docs/operations.md`,
  nunca foi instalado);
- "Revisão pelo agente" dizia "corrigir a causa e amostrar de novo" sem dizer quem corrige, contra
  a regra de que o minos nunca corrige;
- o `STATUS.md` dava o passo 0 do deploy como pendente, e o `DEPLOY.md` como feito;
- o projeto padrão do `gcloud` na máquina é `usher-prod`: um comando sem `--project` cai no Usher;
- o cerberus gravava em `$CLAUDE_JOB_DIR`, que não existe fora de um job.

Respostas do dono em 2026-10-13: commit e push direto no `main`; atlas autônomo até o seed
público (passos 1–7 do `DEPLOY.md`); execução por timer do systemd.

## Decisão

1. **Ciclo autônomo** (AGENTS.md, "Ciclo autônomo"): `scripts/ciclo.sh`, rodado pelo timer de
   usuário `emmoni-ciclo.timer` a cada 3 h, abre uma sessão coordenadora headless (`claude -p`,
   modo `auto`) com o pedido de `scripts/ciclo-prompt.md`. Um ciclo por vez (`flock`), no
   checkout principal, limite de 3 h, log em `data/ciclo/`.
2. **Ninguém pergunta.** Dúvida técnica: a escolha mais conservadora que cabe nas regras, registrada
   no registro da sessão. Decisão que só o dono pode tomar: vai para "Bloqueios e perguntas em
   aberto" do `STATUS.md`, que é a fila do dono, e o ciclo passa ao próximo item. O dono responde
   quando quiser, editando o `STATUS.md` ou numa sessão.
3. **Git:** a coordenadora commita e faz `git push origin main` ao fim de cada ciclo com
   `make gates` verde. Gates vermelhos: commit num branch `ciclo/AAAA-MM-DD-<assunto>`, push do
   branch e registro no `STATUS.md`; o `main` não recebe código com gates vermelhos. Nunca
   `--force`, nunca reescrever histórico publicado.
4. **atlas** faz os passos 1–7 do `DEPLOY.md` sem perguntar, um passo por ciclo, com as regras de
   dinheiro do §1 intactas. Continuam do dono: o passo 8 (questões reais) e tudo que o §1 proíbe,
   remoções de recurso, recurso fora do §3 e qualquer coisa fora do `emmoni-prod`. O passo 7
   (público) só roda depois do teste do corte (passo 4) e da medição da ressalva do §2 (tamanho
   real das respostas e vazão de uma instância), com o pior caso diário recalculado e registrado;
   pior caso acima de R$ 100/dia vai para a fila do dono.
5. **Projeto do `gcloud`:** todo comando leva `--project=emmoni-prod` por extenso, e o ciclo
   exporta `CLOUDSDK_CORE_PROJECT=emmoni-prod`. `.claude/settings.json` nega `usher-prod`,
   `gcloud projects delete`, `gcloud billing accounts` e `git push --force`.
6. **Continua igual:** a separação hefesto/minos (decisões 0011 e 0024), as regras de crawling, a
   publicação das questões reais só com o sim do dono (decisão 0022) e as mensagens para fora
   (Discord, e-mail, outras sessões), que o dono manda. O aviso ao Plantão vira item da fila.

## Consequências

- O dono deixa de ser chamado; em troca, lê a fila do `STATUS.md` e os commits do `main`.
- Commits no `main` sem PR: a revisão humana passa a ser posterior. Um `wrong` do dono continua
  valendo (decisão 0011) e reabre o que ele apontar.
- Um ciclo que trava ou erra repetidamente só aparece no log e no `STATUS.md`; o timer não alerta.
- Sessões que o dono abrir em paralelo esperam a trava do banco (decisão 0025). Checkout principal
  sujo no início = o dono está trabalhando: o ciclo não roda. O que um ciclo deixar sem commit ao
  terminar vai para um `git stash` nomeado ("ciclo <data>: sobra"), para não travar os próximos.
- Desligar: `systemctl --user disable --now emmoni-ciclo.timer`.
