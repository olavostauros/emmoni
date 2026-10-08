# 2026-10-08 — M3: pontas soltas (gabarito por bloco, propostas obsoletas, SDS/PE)

**Marco:** M3 (pendências; o marco atual continua M4)

## O que foi feito
- `ingest/crawlers/cebraspe.py` — `_attach_block_keys`: caderno único sem bloco no rótulo recebe
  os gabaritos de cada bloco (básicos antes de específicos). A proposta de PCDF 2019 agora tem os
  dois gabaritos do manifesto aprovado.
- `ingest/crawl.py` — `ExamFound.more_keys` / `all_documents()`; `_remove_stale_proposals` apaga
  de `_pending/` a proposta da fonte cujo concurso foi visto e lido e não a refez; `Report.removed`
  e a linha "proposta removida" no relatório.
- `ingest/proposals.py` — `build` escreve lista de URLs quando há mais de um gabarito do tipo;
  evidência em `answer_key_final#2`.
- `db/catalog.yaml` — alias `SDS_PE_16_CIVIL` em `pcpe`.
- `fixtures/crawl/cebraspe/SDS_PE_16_CIVIL.json` (reduzido aos campos lidos) e testes novos:
  gabarito por bloco, remoção de propostas obsoletas (sem prova, slug novo; mantém concurso não
  visto, detalhe com erro e outra fonte), escopo de SDS/PE, host bloqueado não remove nada.
- Execução real `make crawl`: 1 requisição nova (detalhe de SDS_PE_16_CIVIL), proposta nova
  `ingest/manifests/_pending/pcpe-2016.yaml`; reexecução com 0 requisições.
- SPECIFICATION.md §7.1 atualizado.

## Verificação
- `make gates`: **passou** — 312 testes; ruff, mypy, roundtrip das migrações ok; `emmoni check`
  com 7 checks sem violação.
- `pcpe-2016` aprovado pelo agente (claude-opus-5-5) com `emmoni manifests approve`, pela
  evidência guardada pelo crawler; no manifesto aprovado, `conhecimentos-gerais` ficou só para
  agente e escrivão (o delegado tem caderno próprio, série 257) e o nome passou a ser o da PC-PE.
- **Não verificado:** `pcpe-2016` contra os PDFs (o crawler não baixa PDFs; a atribuição da
  série 258 a agente/escrivão vem da numeração dos arquivos); `isGuid: true`
  (nenhum caso nos 4.229 arquivos em cache); timer do systemd (depende da máquina que vai rodar o
  crawl, não instalado).

## Decisões
- [0012 — Pontas soltas do M3](../decisions/0012-pontas-soltas-do-m3.md)

## Problemas encontrados
- `pcpe-2016`: a regra de rótulo genérico (decisão 0008) dava `conhecimentos-gerais` também ao
  delegado, que tem caderno próprio (série 257). Corrigido na aprovação.
- DEPEN 2015 responde 500 no detalhe, como DPF 2014.
- DEPEN 2020 continua precisando do gabarito de complementares acrescentado à mão.

## Próximo passo
- Calibrar e ingerir `pcpe-2016` (`first_number`, `subjects_by_range`).
- Fechar o M4 (amostra de assuntos pelo agente revisor).
