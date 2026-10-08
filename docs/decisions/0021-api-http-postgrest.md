# 0021 — API HTTP do esquema `api` por PostgREST

**Data:** 2026-10-08 · **Marco:** M5

## Contexto

O front-end (Plantão, repositório `olavostauros/plantao`) é estático no GitHub Pages e lê um
snapshot exportado do esquema `api` direto do Postgres (decisão 0001 do Plantão). A decisão dele já
apontava uma API pública, "por exemplo, PostgREST sobre o esquema `api`", para quando o snapshot
deixar de caber. O dono pediu uma API no ar para o Plantão. Hoje o acesso é só por SQL, e isso
obriga o front-end a ter um cliente Postgres para conferir a semântica da busca (casos gravados do
F2) ou para desenvolver contra o banco.

## Decisão

1. **PostgREST v12.2.3** como serviço `api` do docker compose, no perfil `api`: só sobe com
   `make api-up`. O `make gates` e o `make db-up` não mudam.
2. Conecta como **`emmoni_web`** (papel autenticador e anônimo ao mesmo tempo) e expõe só o
   esquema `api`. A superfície HTTP é, por construção, a mesma do contrato: as views viram
   `GET /<view>` e as funções `POST /rpc/<função>` (ou `GET` com parâmetros na URL). Nenhum
   `GRANT` novo, nenhuma migração.
3. Erro `22023` das funções vira **HTTP 400** com `{code, message, hint, details}` (mapeamento
   padrão do PostgREST), o que o contrato já pedia ("trate como erro 400").
4. `PGRST_DB_MAX_ROWS=100`: leitura direta de view devolve no máximo 100 linhas por requisição,
   o mesmo teto do `page_size`. Para mais, `limit`/`offset` ou cabeçalho `Range` do PostgREST.
5. Porta **53000**, só em `127.0.0.1` (`EMMONI_API_PORT`). CORS aberto (padrão do PostgREST), o
   que basta para o `npm run dev` do Plantão.
6. `scripts/api-smoke.sh` (`make api-smoke`) confere catálogo, busca, cursor, facetas, questão,
   limite de linhas e o 400. Não entra no `make gates`: os testes do contrato já cobrem as funções
   como `emmoni_web`, e o smoke depende de um container a mais.

## Consequências

- O contrato ganha a seção "Acesso por HTTP" (v1.3, sem mudança no esquema).
- **Imagens não são servidas** pela API: `assets[].url` continua `/assets/<sha256>.<ext>`, a ser
  servido pelo front-end (o snapshot do Plantão já copia `data/assets/`).
- **Não é deploy público.** Publicar exige outra decisão (veio na 0022, Cloud Run): senha própria do `emmoni_web`, TLS,
  limite de taxa e de tempo de consulta (`statement_timeout`), CORS restrito ao domínio do site e
  hospedagem do banco. Até lá, o Plantão continua no snapshot.
