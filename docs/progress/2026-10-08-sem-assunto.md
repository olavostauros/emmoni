# 2026-10-08 — As 62 questões sem assunto confiante

**Marco:** M4 (pós-fechamento)

## O que foi feito
- Conferida primeiro a disciplina do manifesto (próximo passo 3 do `STATUS.md`). Dois intervalos
  estavam errados; os PDFs não têm títulos de disciplina, então a faixa era palpite:
  - `pcpb-2021` cargo 6: 51–57 são física (massa-mola, gravitação, capacitor), não engenharia →
    `{51–57: fisica}`, `{58–72: engenharia}`. 4 das 62 eram desse caso; 55–57 já estavam
    classificadas em `engenharia.engenharia_eletrica` e foram reclassificadas em física.
  - `pcgo-2016` específicos cargo 2: 64 (contravenções) e 65 (infiltração) são legislação penal
    especial, como no cargo 1 → `{61–63: direito-penal}`, `{64–65: legislacao-penal-especial}`.
- As outras eram lacunas da taxonomia: **36 assuntos novos** em 19 disciplinas (863 → 899), por
  exemplo números complexos e polinômios, Lei Henry Borel, quimiometria, química ambiental, LGPD,
  Lei Anticorrupção, execução penal, funções da linguagem e mecânica dos solos.
- Respostas gravadas em `classify-answers.json` das 29 provas; `--step classify` e `--step load`
  rerodados (`--step validate` antes nas duas provas com faixa corrigida).

## Verificação
- `make gates`: **passou** — 312 testes; lint, roundtrip de migrações e 7 checks sem violação.
- Questões reais: 5.083 `published` (antes 5.043), 1.231 `review`, **0 `draft`**; nenhuma questão
  sem assunto; 0 tarefas pendentes em `classify-tasks.json`.
- `api`: 1.190 questões visíveis (antes 1.188): pf-2025/delegado q58 e q59 entraram, porque a
  prova já estava aprovada.
- **Não verificado:** as 62 novas classificações não passaram por amostra de revisor separado
  (não estavam na amostra do M4). A pcrj-2021 q17 (revitimização) ficou em
  `abuso_de_autoridade` com 0,7, que é o caso mais discutível.
- DEPEN 2020 continua sem carregar (gabarito de 80 itens para 90 questões); a classificação dela
  está no staging.

## Decisões
- Sem decisão nova: assunto de lei especial cobrado dentro de outra disciplina entra **nessa**
  disciplina (crimes hediondos e execução penal em direito penal, Lei Anticorrupção em direito
  administrativo), seguindo o precedente da [0010](../decisions/0010-taxonomia-e-classificacao-m4.md).

## Problemas encontrados
- `subjects_by_range` dos manifestos é palpite quando o caderno não tem títulos de disciplina.
  Outros intervalos podem estar errados sem aparecer como "sem assunto" (a questão encaixa em
  algum assunto da disciplina errada, como pcpb-2021 cargo 6 q55–57).

## Próximo passo
- Amostragem por prova (`emmoni review sample/approve --by`) das 90 provas não aprovadas.
