# 2026-10-08 — Amostragem das 90 provas: rodada 1 e correções do parser

**Marco:** M4 → publicação das provas (antes do M5)

## O que foi feito
- Decisão 0013 (texto-base na múltipla escolha só para quem o cita) e `review sample` com
  `amostra.md` + páginas em PNG (commit dc3b7ad).
- Rodada 1 da amostragem: 9 agentes revisores, 90 provas. Os vereditos (`verdicts.json`) **não
  valem mais**: os dados mudaram com as correções abaixo, e um revisor (lote 6) aprovou páginas
  que não conseguiu ver ("request limit"). Nenhuma prova foi aprovada.
- Correções a partir dos defeitos achados (extract + parser), todas as provas reprocessadas:
  rótulo "Texto X" fora da margem gruda na alternativa E; títulos "Proposição/Situação hipotética
  X" como rótulo; código de rótulo com ponto final e "P3" como falso rótulo; tabela
  `||JUSTIFICATIVAS||` engolia o texto-base seguinte (PC/PE 2023); título de disciplina em caixa
  alta grudado na alternativa E (PC/RO 2022); marcador "•" lido como "C" (PC/GO 2016);
  "FimDoTexto"; glifos Symbol em uso privado (U+F0xx) mapeados; glifo de controle (μ perdido)
  vira U+FFFD → fórmula; parágrafo que começa em número de linha não se funde mais (também PF
  2018); figura da própria questão citada e remissão a texto-base não encontrado → `review`.

## Verificação
- `make gates`: **passou** — 315 testes, lint, roundtrip, 7 checks sem violação.
- Questões reais: 5.317 `published`, 997 `review`. 11 questões com "remete a um texto-base que
  não foi encontrado" (algumas reais: 12A1-I, CG4A2AAA anuladas; outras falso positivo).
- **Não verificado:** nenhuma prova nova foi aprovada; as amostras precisam ser regeradas.

## Próximo passo
- Regerar as amostras das 90 provas (`emmoni review sample`) e rodar a rodada 2 com o prompt de
  revisor em que imagem não vista = `unverified` / prova `incomplete` (não aprovar).
- Restam sem correção: "texto 1A1- I" (espaço no rótulo), PCPB cargo-12 texto 12A1-I não
  segmentado; linhas numeradas dos textos-base não preservadas (limitação conhecida).
