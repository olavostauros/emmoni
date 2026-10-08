# 0011 — A revisão por amostragem passa a ser feita pelo agente

**Data:** 2026-10-08 · **Marco:** M4

## Contexto

Três pontos do pipeline dependiam de uma pessoa: a aprovação das propostas do crawler
(`emmoni manifests approve`), a amostragem por prova antes de publicá-la no `api`
(`emmoni review sample/approve`) e a amostragem de 50 classificações que fecha o M4
(`emmoni review topics`). Com 90 provas sem amostragem e a amostra de assuntos parada, a revisão
humana virou o gargalo do projeto. O dono do projeto decidiu tirá-la do caminho.

## Decisões

1. **O agente revisa nos três pontos**, com os mesmos comandos, amostras e limiares: 10 questões
   por prova, 50 classificações com ≥ 90% de acerto, proposta conferida contra a evidência.
   Nenhuma revisão é pulada; muda só quem revisa.
2. **Quem revisou fica registrado** com o modelo e a versão (ex.: `claude-opus-5-5`):
   `reviewed_by` em `amostra.json`, `approved_by` em `sample.json` (`emmoni review approve --by`)
   e, nas aprovações de manifesto, a mensagem de commit.
3. **A revisão é um passo separado da produção.** Quem confere a classificação não usa as
   respostas nem o raciocínio do `classify`: lê só a questão e os assuntos atribuídos, em contexto
   novo (outro agente ou outra sessão). Quem confere uma prova compara com o PDF, não com o
   staging.
4. **A revisão do agente é feita sobre o que já foi baixado** (PDFs em `data/`, páginas em
   `crawl.page`, bloco `evidence`). Conferir uma proposta não autoriza navegar fora do crawler nem
   fora de `ingest/sources.yaml`.
5. **Reprovação não é contornada.** Amostra com erro: a prova não é aprovada; corrige-se o parser,
   o manifesto ou a classificação e gera-se uma amostra nova com outra semente. Proposta duvidosa:
   rejeitar com motivo ou deixar pendente e registrar no `STATUS.md`.
6. `auto_approve` continua `false`: a aprovação de manifesto segue explícita (o agente roda
   `emmoni manifests approve`), não automática no crawler.

## Consequências

- AGENTS.md (princípios e fluxo), SPECIFICATION.md §7.1 e §8 e `docs/operations.md` atualizados.
- Erros que só uma pessoa veria (o mesmo modelo errando na extração e na conferência) podem passar.
  A pessoa pode conferir qualquer amostra depois; um `wrong` dela vale e reabre a prova ou o marco.
- O M4 pode fechar sem conferência humana.
