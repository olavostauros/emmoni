# 2026-10-08 — `cespe.unb.br` por HTTP e `ocrmypdf`

## Feito
- Exceção ao HTTPS autorizada pelo dono para `www.cespe.unb.br` (decisão 0017): campo
  `allow_http` em `sources.yaml`, validado ao carregar; o cliente só aceita `http://` em prefixo de
  fonte com a exceção (redirecionamentos inclusos); `robots.txt` pelo esquema da URL.
- Fonte `cespe-unb` sem crawler (`crawler: null`); `emmoni crawl --all` a pula.
- Duas requisições ao host pelo cliente de cortesia: `robots.txt` (permite `/concursos/`) e a
  listagem `/concursos/` (200, HTML).
- `ocrmypdf` 17.13 adicionado ao `pyproject.toml`.

## Gates
`make gates`: ok — 334 testes, `emmoni check` sem violações.

## Sem verificar
- Idioma `por` do Tesseract não instalado (exige sudo do dono); OCR não testado de ponta a ponta.
- Nenhum manifesto do `cespe-unb` escrito ainda; estrutura de `_antigos/` e `provas.htm` não
  explorada.

## Continuação — OCR com revisão do agente (decisão 0018)

### Feito
- `tesseract-data-por` instalado pelo dono. `extract` com OCR só nas páginas sem texto, limpeza de
  layout e recuperação dos números de item na margem (OCR só de dígitos).
- Revisão linha a linha das linhas de conteúdo pelo agente (`ingest/ocr/<sha256>.yaml`):
  PCDF 2020 básicos, 41 correções em 7 páginas; PM/TO 2020 QPE gabarito, 9 linhas e as 60 marcas
  conferidas contra a imagem.
- PCDF 2020 básicos: faixas de disciplina no manifesto; classificação por um subagente (50/50 com
  assunto confiante; 2 sugestões de assunto para unidades de conservação do DF em `topics.json`).
- Amostras por revisores em contexto separado. 1.ª rodada: PCDF recusada (apóstrofo reto em
  "suspect’s"), PM/TO recusada (crédito colado ao comando em q22/q23). Causas corrigidas (correção de
  OCR; `CREDIT_END` no parser). 2.ª rodada: 10/10 nas duas; aprovadas por claude-opus-5-5.
- O revisor do PCDF apontou o item 43 como anulado; conferido contra a imagem do gabarito: é C
  (anulados só 23, 27 e 30). Erro do revisor, fora da amostra.
- Parser: "do expediente forense" não é referência a documento.

### Gates
`make gates`: ok — 341 testes, `emmoni check` sem violações.

### Sem verificar / pendente
- A regra `CREDIT_END` em `_paragraphs` apareceu no arquivo sem que esta sessão a tenha gravado de
  forma rastreável (provavelmente antes de uma retomada de contexto); foi mantida, coberta por teste
  e completada em `_choice_paragraphs`.
- 16 provas aprovadas mudariam com a regra (47 questões, só quebra de parágrafo): não reprocessadas,
  seguem publicadas com o staging antigo. Lista no `STATUS.md`.
