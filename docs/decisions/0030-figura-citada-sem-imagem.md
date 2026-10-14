# 0030 — Figura citada sem imagem extraída vai para revisão

**Data:** 2026-10-14 · **Marco:** M5

## Contexto

O minos reprovou `pf-2018/agente` (amostra de 2026-10-14): os itens 81–83 estavam publicados sem o
diagrama ER que fica entre o item 80 e o comando "Considerando o modelo entidade-relacionamento
(ER) precedente, julgue os seguintes itens...". O parser marca com `figure` a linha que antecede
cada figura; aqui ela era a última do item 80, que foi para `review`, e o grupo seguinte saiu
limpo. A regra textual (`FIGURE_REF`) só reconhecia o nome da figura colado à remissão ("figura
precedente"), sem palavras no meio, e não via "modelo ... precedente", "o diagrama e a situação
hipotética apresentados" nem "mostrada anteriormente"/"antes ilustrado". Ainda não há etapa de
imagens que ligue a figura a um texto-base das questões (`structure`, próximos passos).

## Decisão

No parser do Cebraspe (`_reference_flags` e `_passage_flags`), a opção conservadora: a questão
fica em `review` com a pendência certa até a etapa de imagens existir.

1. **Figura citada** (motivo "figura ou tabela não extraída"), no enunciado, nas alternativas ou no
   texto-base, além do `FIGURE_REF` de antes:
   - nome de figura (figura, gráfico, imagem, ilustração, esquema, mapa, planilha, circuito,
     cartograma, tabela, diagrama, fluxograma, organograma) seguido, com até cinco palavras no
     meio, de remissão de lugar ou de particípio ("precedente", "a seguir", "acima",
     "anteriormente", "apresentados", "mostrada", "ilustrado"...);
   - "modelo" e "quadro" só com remissão de lugar ("o modelo ER precedente", "o quadro a
     seguir"): "o quadro apresentado" (quadro clínico) e "o modelo apresentado" (uma função) não
     são figura;
   - particípio de figura com remissão para trás ("mostrada anteriormente", "antes ilustrado").
2. **Comando que aponta para trás sem texto-base** (motivo "remete a um texto-base que não foi
   encontrado"): item certo/errado sem texto-base cujo comando, fora "itens a seguir/seguintes",
   diz "precedente", "anterior", "anteriormente", "acima" ou "antes apresentado/descrito": o que
   o comando aponta ficou de fora ("os dados acima", PF 2012 agente 85–86).
3. A marca posicional do item acima da figura continua: em caso de dúvida sobre a quem a figura
   pertence, os dois lados ficam em revisão.

## Consequências

- Com o banco de 2026-10-14, a regra tira de `published` 7 questões: PF 2018 agente 81–83, PC/DF
  2020 conhecimentos específicos 85–86 e PC/PB 2021 cargo 7, 51 e 54. As três provas voltam a
  `review` pela impressão digital e precisam de nova amostra. PF 2012 agente 85–86 já estavam em
  revisão e ganham o segundo motivo.
- Sem mudança de texto: só `review_reasons` e o status.
- Falso positivo deixa questão boa em revisão (custo aceito); falso negativo continua possível
  quando o comando nomeia a figura por outra palavra ("estrutura", "tela") sem particípio.
