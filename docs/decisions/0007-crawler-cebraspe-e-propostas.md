# 0007 — Crawler do Cebraspe, propostas de manifesto e estado do crawling

**Data:** 2026-10-07 · **Marco:** M3

## Contexto

O M3 pede que o crawler redescubra sozinho os concursos de PF e PRF ingeridos no M2 e proponha
pelo menos um concurso policial novo. O cliente de cortesia (0003) e a leitura da API JSON do
Cebraspe (0004) já existiam; faltavam o crawler, o estado persistente e o ciclo de proposta →
aprovação. A especificação (§7.1) deixava em aberto como o crawler reconhece o órgão, como casa
prova com gabarito, quem é dono de cada arquivo de manifesto e o que acontece com o que não entra
numa proposta.

## Decisões

1. **Só regras, sem LLM, no crawler do Cebraspe.** As descrições dos arquivos da API são
   padronizadas o bastante: `PROVA OBJETIVA`, `GABARITO DEFINITIVO`, `GABARITO PRELIMINAR` dão o
   tipo; `CURSO DE FORMAÇÃO`, `TURMA`, `CFP`, `ORAL`, `DISCURSIVA`, `PADRÃO DE RESPOSTA` etc.
   excluem o documento (com o motivo gravado). Prova e gabarito se casam, nesta ordem, pelo rótulo
   (a descrição sem o tipo), pelo nome do arquivo (`MATRIZ_408_DGPPF012` ↔
   `GAB_DEFINITIVO_408_DGPPF012`) ou pelo número do cargo. A etapa de LLM prevista na §7.1 só
   entra quando uma fonte precisar dela.
2. **Órgão pelo catálogo.** `db/catalog.yaml` ganha `aliases` por órgão: os prefixos com que a
   fonte escreve o órgão na URL ou no nome do evento (`PF`, `DPF`, `PRF`, `PC_DF`, `PCDF`). Evento
   com prefixo de órgão policial sem alias (`PC_PE`, `PM_AL`, `CBM_MA`, `DEPEN`...) vira **órgão
   candidato** no relatório; o detalhe não é buscado até o órgão entrar no catálogo. `ADM` no nome
   do evento → fora do escopo (cargos administrativos). Cargos vêm de `eventoCargos` casados com
   os cargos do órgão no catálogo; prova cujo cargo não está no catálogo (peritos, por exemplo)
   fica fora da proposta, com o motivo em `evidence.skipped` e em `discovered_document`.
3. **PCDF entra no catálogo** (`pcdf`: delegado, agente, escrivão). É o primeiro órgão além de PF
   e PRF, escolhido porque o Cebraspe tem três concursos dele (2019, 2020, 2026) e a carreira está
   no núcleo do MISSION.md. Os outros órgãos candidatos entram quando houver parser e taxonomia.
4. **Três diretórios, três estados, tudo no git.** `_pending/` é **do crawler**: ele reescreve a
   proposta quando a fonte muda (só se o conteúdo mudou; o arquivo não tem data). Aprovar
   (`emmoni manifests approve`) valida contra o modelo e o catálogo e move o arquivo para
   `ingest/manifests/`, que passa a ser **curado à mão** e nunca mais é reescrito pelo crawler;
   documentos novos de concurso aprovado só aparecem no relatório. Rejeitar
   (`emmoni manifests reject --reason`) move para `_rejected/` com o motivo, e o crawler não volta
   a propor. Os status em `crawl.discovered_document` são derivados desses diretórios (e de
   `source_document`, para `ingested`) a cada execução.
5. **A página do concurso também é um `discovered_document`** (`guessed_kind` nulo,
   `guessed_contest_slug`, `guessed` com órgão, ano e fase). É onde ficam o `out_of_scope` com
   motivo dos concursos não policiais e o `pending` dos órgãos candidatos, sem tabela nova.
6. **Estado e cache.** `crawl.page` guarda `etag`, `last_modified`, `content_sha256` e
   `next_fetch_at` por URL; o corpo fica em `data/crawl/<fonte>/<sha256>`. Página que não venceu é
   relida do cache, sem rede — então regras novas se aplicam sem recrawl. Erro HTTP agenda nova
   tentativa em 1 dia. `recrawl.contest_closed: never` significa "busca uma vez e nunca mais";
   `--force` ignora tudo isso.
7. **Fixtures do crawler em `fixtures/crawl/<fonte>/`** (JSON ou HTML, conforme a fonte), em vez
   de `fixtures/html/`.
8. **Slug do concurso** é `<órgão>-<ano>`; colisão (três eventos PM/TO em 2020) acrescenta o resto
   da URL do evento (`pmto-2020-qpe`). Slug da prova vem do cargo quando a descrição é só
   "CARGO N: nome"; senão, da descrição (`conhecimentos-basicos`, `itens-de-9-a-120`). Quem aprova
   ajusta nomes, `first_number` e `subjects_by_range` no manifesto aprovado.

## Consequências

- Com as fixtures de 2026-10-07, as propostas de PF 2018, PF 2021, PF 2025, PRF 2018 e PRF 2021
  têm exatamente os mesmos pares prova/gabarito dos manifestos escritos à mão no M2 (teste
  `test_proposals_reproduce_the_manual_manifests`). PCDF 2019, 2020 e 2026 são propostos.
- Uma proposta pode ter provas sem par que um humano saberia casar (PCDF 2019: um caderno, dois
  gabaritos — básicos e específicos); o manifesto aceita um gabarito por prova e o caso fica no
  relatório. Resolver isso é mudança de modelo, não de crawler.
- A dependência de `eventoCargos` e das descrições significa que uma mudança de padrão do Cebraspe
  deixa provas fora das propostas de forma **visível** (motivo gravado), nunca silenciosa.
- `DPF_14_AGENTE` continua sem proposta: a API responde 500 (registrado em `crawl.page`).
