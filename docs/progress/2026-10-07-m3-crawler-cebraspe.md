# 2026-10-07 — M3: crawler do Cebraspe, propostas e aprovação de manifestos

**Marco:** M3 — Crawling (concluído)

## O que foi feito
- `ingest/crawl.py` — orquestração comum a todas as fontes: `Fetcher` com estado em `crawl.page`
  (`etag`, `last_modified`, `content_sha256`, `http_status`, `next_fetch_at`) e cache dos corpos em
  `data/crawl/<fonte>/<sha256>`; página que não venceu é relida do cache, sem rede; limite de
  2.000 páginas e `max_depth` por fonte; erro HTTP agenda nova tentativa em 1 dia. Atribuição de
  slugs (`<órgão>-<ano>`, com desempate), sincronização de `crawl.discovered_document` (status
  derivado dos diretórios de manifestos e de `source_document`) e relatório da execução.
- `ingest/crawlers/cebraspe.py` — lê a listagem e o detalhe de cada concurso pela API JSON;
  escopo pelos `aliases` do catálogo; tipo de cada arquivo pela descrição; prova ↔ gabarito pelo
  rótulo, pelo nome do arquivo ou pelo número do cargo; cargos por `eventoCargos` × catálogo.
  Órgãos policiais sem alias viram candidatos no relatório (o detalhe não é buscado).
- `ingest/proposals.py` + `emmoni manifests pending|show|approve|reject --reason`: `_pending/` é
  do crawler, `ingest/manifests/` é curado à mão, `_rejected/` guarda o motivo. `approve` valida o
  modelo e os slugs do catálogo (`catalog.manifest_problems`).
- `emmoni crawl <fonte>|--all [--force]` e `make crawl`; `docs/operations.md` com timer do
  systemd e cron.
- `db/catalog.yaml`: `aliases` em PF (`PF`, `DPF`) e PRF; **PCDF** entra no catálogo (delegado,
  agente, escrivão). `Manifest.evidence` (ignorado pelo pipeline).
- Fixtures em `fixtures/crawl/cebraspe/` (listagem reduzida + 8 detalhes) e 51 testes novos:
  regras puras, execução sobre as fixtures no banco de testes, idempotência (segunda execução sem
  rede e sem mudança), política de recrawl, host bloqueado, aprovação e rejeição.
- **Execução real** (`emmoni crawl cebraspe`, 10 requisições): 498 concursos vistos, 440 fora do
  escopo; PF 2018, PF 2021, PF 2025, PRF 2018 e PRF 2021 reconhecidos como aprovados com
  **36/36** documentos dos manifestos manuais encontrados; **3 propostas novas** em
  `ingest/manifests/_pending/`: `pcdf-2019`, `pcdf-2020`, `pcdf-2026`. Órgãos candidatos ao
  catálogo: PC (19 eventos), PM (15), CBM (9), DEPEN (2), SEAP (2), SDS (2).

## Verificação
- `make gates`: **passou** — 252 testes; ruff, mypy e checagem do seed limpos; roundtrip das 9
  migrações ok; 7 checks sem violação.
- Critério do M3: coberto pelo teste `test_proposals_reproduce_the_manual_manifests` (as propostas
  geradas das fixtures têm exatamente os pares prova/gabarito dos 5 manifestos manuais) e pela
  execução real acima.
- Rodar o crawl duas vezes: a segunda não faz requisição nenhuma (listagem com 1 dia de validade)
  e nenhuma proposta muda (teste e execução real).
- **Não verificado:** as propostas de PCDF contra os PDFs (o parser do Cebraspe ainda não foi
  calibrado em provas da PCDF; `first_number`, `subjects_by_range` e nomes ficam para a aprovação);
  `isGuid: true` na API (nenhum arquivo com esse campo apareceu; a URL segue a decisão 0004);
  o timer do systemd (documentado, não instalado).

## Decisões
- [0007 — Crawler do Cebraspe, propostas e estado do crawling](../decisions/0007-crawler-cebraspe-e-propostas.md)

## Problemas encontrados
- `DPF_14_AGENTE`: a API continua respondendo 500; fica registrado em `crawl.page` e é tentado de
  novo a cada dia. PF 2014 segue sem proposta.
- PCDF 2019 tem um caderno e dois gabaritos definitivos (básicos e específicos); o manifesto aceita
  um gabarito por prova, então só o de específicos é pareado e o de básicos fica `pending` com
  motivo. Resolver exige mudar o modelo (vários documentos de gabarito por prova).
- `REABERTURA` casava com `ABERTURA` na detecção de edital de abertura; corrigido com fronteira de
  palavra.
- O relatório de "documentos novos em concurso aprovado" só considera documentos que entrariam
  numa proposta (prova com gabarito e cargo do catálogo); provas de perito e editais ficam só em
  `discovered_document`, com motivo.

## Próximo passo
- Humano decide sobre as 3 propostas de PCDF (`emmoni manifests approve|reject`). Para ingerir,
  calibrar o parser nos cadernos da PCDF e preencher `subjects_by_range`.
- M4 — taxonomia e classificação (ver STATUS.md).
