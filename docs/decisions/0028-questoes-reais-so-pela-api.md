# 0028 — Questões reais saem só pela API

**Data:** 2026-10-13 · **Marco:** M5

## Contexto

A decisão 0022 previa dois caminhos para as questões reais chegarem ao público, cada um com o
sim do dono: a imagem `all` da API no Cloud Run e o snapshot `--scope all` do Plantão. O
snapshot do Plantão é **versionado no git** de um repositório público (SPECIFICATION.md §3 de
lá): publicado uma vez, o banco inteiro sai num `git clone` e fica no histórico para sempre, sem
volta. Pela API, os dados não vão para o git, saem de pedido em pedido (com limite de linhas e
`max-instances=1`) e somem quando o serviço sai do ar.

O dono perguntou se dava para guardar as questões num servidor com uma API servindo o cliente,
em vez de publicar os dados. O Cloud Run da decisão 0022 já é esse servidor; uma VM custaria 24 h
por dia no crédito dividido com o Usher e traria sistema e Postgres para manter, sem ganho para
uma API só de leitura.

## Decisão

1. As questões reais saem **só pela API** (Cloud Run, decisão 0022). Nenhum repositório público
   recebe dado real: o snapshot `--scope all` do Plantão deixa de ser caminho de publicação.
   O seed (fictício) continua no snapshot, para desenvolvimento e testes do Plantão.
2. Fica a infraestrutura da decisão 0022 (Cloud Run, sem VM).
3. O sim do dono para as questões reais vale só para o passo 8 do `DEPLOY.md` (imagem `all`
   pública). Ainda não foi dado.
4. Como o Plantão lê a API (no navegador ou no build, sem versionar o resultado) é decisão do
   repositório dele; o pedido vai pela fila do dono, porque mexer em outro projeto é do dono
   (decisão 0026).

## Consequências

- O Plantão hoje só lê o snapshot versionado; até mudar, ele fica no seed, mesmo depois do
  passo 8.
- Ler a API no navegador entra em atrito com o "HTML primeiro" e com a busca no navegador do
  Plantão (decisão 0006 de lá); gerar no build sem versionar mantém o HTML, mas o site público
  continua mostrando as questões, só que fora do git e com volta. A escolha é do Plantão.
- Tirar a API do ar tira as questões do ar; não há cópia pública fora do nosso controle além do
  que alguém já tiver baixado.
