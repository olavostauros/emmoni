# 0004 — Leitura do site do Cebraspe pela API JSON

**Data:** 2026-10-07 · **Marco:** M2

## Contexto

`https://www.cebraspe.org.br/concursos/` é uma aplicação React: o HTML não traz links para provas.
A lista de concursos e os arquivos de cada um vêm de uma API JSON, descoberta no bundle
`/concursos/static/js/main.*.chunk.js`:

- `https://apis.cebraspe.org.br/cebraspe/eventos/tipo/concursos/` — concursos por fase
  (`faseEvento`, `eventos[].eventoURL`, `eventoNomeAbreviado`, `eventoAno`);
- `https://apis.cebraspe.org.br/cebraspe/eventos/<eventoURL>` — detalhe, com `eventoCargos`,
  `arquivosEdital` e `arquivosGabarito` (`nomeArquivo`, `descricaoArquivo`, `dataArquivo`);
- PDF: `https://cdn.cebraspe.org.br/concursos/<eventoURL>/arquivos/<nomeArquivo>`
  (ou `cdn + nomeArquivo` quando `isGuid`).

O `robots.txt` dos dois hosts não restringe nada. A lista começa em 2014; concursos mais antigos
estão no site antigo (`cespe.unb.br`), que não está na lista de fontes.

## Decisão

1. Novo campo opcional por fonte em `sources.yaml`: **`extra_content_types`**, tipos aceitos além
   de PDF e HTML. Para o Cebraspe: `application/json` (a API) e `application/javascript`,
   `text/javascript` (só para reler o bundle se a API mudar de endereço).
2. Novo prefixo permitido: `https://apis.cebraspe.org.br/cebraspe/eventos`.
3. Continua `js: false`: não usamos navegador; lemos a mesma API que a página lê, pelo cliente de
   cortesia.

## Consequências

- O crawler do Cebraspe (M3) lê JSON em vez de HTML; as fixtures dele serão respostas JSON
  gravadas.
- Se o Cebraspe mudar a API, o crawler quebra de forma visível (erro de validação), não silenciosa.
- Concursos anteriores a 2014 (ex.: PF 2012, PRF 2013) ficam fora até uma decisão sobre
  `cespe.unb.br`.
