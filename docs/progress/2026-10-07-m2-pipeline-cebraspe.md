# 2026-10-07 — M2: fontes, cliente HTTP e pipeline do Cebraspe

**Marco:** M2 — Primeira ingestão

## O que foi feito
- `e202058` — commit do M1, que estava só na árvore de trabalho.
- `245c5ca` — `ingest/sources.yaml` (Cebraspe + denylist de agregadores) e
  `ingest/crawlers/http.py`, o cliente com as regras de cortesia (decisão 0003).
- `78a28fb` — o site de concursos do Cebraspe é uma aplicação React; a lista e os arquivos vêm de
  `apis.cebraspe.org.br`. Lemos a API JSON pelo mesmo cliente (decisão 0004).
- `5709a9c` — pipeline até o `load`: `fetch`, `extract`, `segment` (parser do Cebraspe),
  `answer-key`, `validate`, `load`; `emmoni ingest` e `emmoni catalog load`; catálogo curado em
  `db/catalog.yaml`; manifesto `ingest/manifests/pf-2021.yaml` (só Agente); migração
  `question.review_reasons` + `passage.source_key`; taxonomia de Estatística e Contabilidade Geral
  (decisão 0005; contrato v1.1, só documentação).
- Concursos de PF/PRF que o site do Cebraspe lista (desde 2014): PF_25 (em andamento), PF_21,
  PF_18, DPF_14_AGENTE, PRF_21, PRF_18. PF_25_ADM é de cargos administrativos (fora do escopo).
- PF 2021 — Agente carregado no banco de desenvolvimento: 120 questões, 15 textos-base, 5 anuladas
  (28, 92, 106, 108, 119). **93 sem pendência** (aguardam assunto → `draft`) e **27 em `review`**
  (layout especial 21, figura/tabela 19, fórmula 12; uma questão pode ter mais de um motivo).

## Verificação
- `make gates`: **passou** — 181 testes; ruff, mypy e checagem do seed limpos; roundtrip das 9
  migrações ok; 7 checks sem violação.
- `emmoni ingest pf-2021` rodado duas vezes: a segunda não baixa nada (índice em `data/raw/`) e o
  `load` mantém os mesmos ids (também coberto por teste).
- Saída do parser conferida à mão para os 120 itens (comandos, textos-base, faixas de disciplina).
  A fixture de 2 páginas dá o mesmo resultado que o documento completo.
- **Não verificado:** amostragem manual lado a lado com o PDF (falta `emmoni review sample`); outras
  provas do Cebraspe (o parser foi calibrado numa prova só); OCR (nenhuma página sem texto até agora).

## Decisões
- [0003 — Fontes e cliente HTTP](../decisions/0003-fontes-e-cliente-http.md)
- [0004 — API JSON do Cebraspe](../decisions/0004-cebraspe-api-json.md)
- [0005 — Ingestão do Cebraspe](../decisions/0005-ingestao-cebraspe.md)

## Problemas encontrados
- Número do item sai 1 pt abaixo da primeira linha → linhas agrupadas por sobreposição vertical.
- Fórmulas em Cambria Math saem como glifos etíopes/malaialas → marcadas `formula` (revisão).
- Recuo de parágrafo (+29 pt) confundido com continuação de item (+18 pt) → regra por recuo.
- Réguas que separam grupos de itens viravam "figura" → régua isolada da largura da coluna é ignorada.
- Rótulos de gráfico e o código do caderno grudavam no item anterior → corrigido; texto que sobra
  depois do último item agora marca `orphan_text` em vez de sumir.
- O gabarito preliminar do PF 2021 não está mais no site; só o definitivo.

## Próximo passo
- Etapa `classify` (precisa de `ANTHROPIC_API_KEY`) → as 93 questões limpas viram `published`.
- `emmoni review sample/approve` e a amostragem manual da prova.
- Demais provas: PF 2021 (Delegado, Escrivão, Papiloscopista), PF 2018, DPF 2014, PF 2025, PRF 2018
  e PRF 2021.
