# 0023 — Escape de texto literal no Markdown restrito

**Data:** 2026-10-13 · **Marco:** M5

## Contexto

O `extract` copiava o texto do PDF para o Markdown sem escape. Os dados reais têm centenas de `R$`
e nenhuma fórmula em `$...$`: "R$ 10,00 e R$ 20,00" é fórmula para qualquer extensão de matemática,
e o asterisco de nota ("Austrália*") ou o `_` de nome de arquivo podem abrir itálico. O Plantão
desligou as fórmulas inline à espera de uma regra (`src/lib/markdown.ts`: "até o banco de questões
confirmar a content-format v1.1").

## Decisão

1. `$`, `*`, `_`, `` ` ``, `<` e `\` do texto do PDF saem escapados com `\` (escape padrão do
   CommonMark), em `ingest/content.py` (`escape_md`), aplicado por trecho em `extract._markdown`
   antes de o negrito/itálico entrar. A marcação que a ingestão gera não é escapada.
2. As correções de OCR (`ingest/ocr/*.yaml`) já são Markdown escrito pelo agente: ficam como estão.
3. O `statement_hash` não muda: a normalização já tira `\` e pontuação.
4. `docs/content-format.md` v1.1 e contrato v1.4, sem mudança no esquema.

## Consequências

- O front-end pode ligar `$...$` de novo: o `$` literal chega como `\$`.
- Quem mostra ou indexa o texto sem renderizar o Markdown (busca, prévia) tira a barra antes desses
  caracteres.
- As provas já carregadas só ganham o escape quando são reprocessadas e recarregadas.
