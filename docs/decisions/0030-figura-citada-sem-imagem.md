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

## Emenda de 2026-10-14 — imagem logo abaixo do título "Questão N"

**Contexto.** O minos (semente r9) achou publicadas as questões 38 e 40 do CBM/RO 2022 oficial, que
abrem com uma fotografia (só a legenda virou texto). Na múltipla escolha, `_with_figures` marca a
linha acima da figura; ali essa linha é o título "Questão N", que não entra no bloco da questão, e a
marca se perdia. O comando não cita a figura com as palavras da regra textual.

**Decisão.**

1. A marca `figure` posta no título "Questão N" passa à questão que ele abre (`_segment_choice`).
2. Só a imagem raster marca o título; desenho vetorial ali é a moldura do título ou a régua do
   cabeçalho de disciplina (PC/GO 2016, PC/PE 2023, PM/MA 2017...) e segue ignorado, como antes
   (`_mark_figure`).

**Verificação.** Varredura das 135 provas, HEAD × novo: só mudam pendências de figura, em 9
questões publicadas de 5 provas — CBM/RO 2022 oficial q38 e q40 (fotografias), PC/PB 2021
específicos cargo 4 q77 (datilograma), PC/RO 2022 específicos cargo 1 q42 e q43 (ícone do botão do
Word no meio do comando), PM/TO 2020 QPE q30 (mapa) e q59 (partitura). Auditoria independente (cada
imagem raster das provas casada, pelo texto das linhas vizinhas, com a questão ou o texto-base, e
conferida a pendência): depois da correção, nenhuma imagem cai em questão publicada sem pendência
de figura; as que sobram são faixas de título, imagens da justificativa (PC/PE 2023 P2 cargo 1) ou
de itens fora da prova (DEPEN 2020 itens 25–26), e questões já em `review` por outro motivo (PM/MA
2017 CG2A1BBB, PM/TO 2020 QPE q54). Desenhos vetoriais grandes fora de questões marcadas: só faixas
de título. As quatro provas voltam a `review` pela impressão digital.
