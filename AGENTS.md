# AGENTS.md — emmoni

Instruções para agentes que trabalham neste repositório. Antes de começar, leia:

1. [MISSION.md](MISSION.md) — o que é o emmoni e qual é a missão atual (o **porquê**).
2. [SPECIFICATION.md](SPECIFICATION.md) — stack, modelo de dados, contrato, pipeline, testes e
   marcos (o **o quê**). É a fonte de verdade técnica.
3. Este arquivo — como trabalhar (o **como**).

Em caso de conflito: o SPECIFICATION.md manda nas decisões técnicas; este arquivo manda no processo.

## Divisão de trabalho

| Agente | Responsabilidade |
|---|---|
| **Banco de dados** (missão atual) | Esquema, migrações, ingestão das provas, qualidade dos dados, contrato e seed para o front-end. |
| **Front-end** | O site que os concurseiros usam. Consome o contrato publicado pelo agente de banco de dados. |
| **atlas** (deploy) | Leva a API ao Google Cloud Run seguindo `docs/DEPLOY.md`; pede o sim do dono antes de cada recurso (`.claude/agents/atlas.md`). |
| **cerberus** (segurança) | Audita imagem, API pública e projeto, só leitura; relatório no contrato de `docs/CYBERSECURITY.md` (`.claude/agents/cerberus.md`). |

Regras de fronteira:

- O agente de banco de dados **não** escreve código do site. O agente de front-end **não** altera
  esquema nem migrações — pede a mudança.
- O atlas e o cerberus não mudam esquema, ingestão nem dados; o atlas publica imagens, o
  cerberus só lê. Publicar as questões reais na API exige o sim explícito do dono (decisão 0022).
- A interface entre os dois é o esquema `api` do banco, acessado com o papel `emmoni_web`,
  documentado em `docs/contract.md`, mais o **seed** (SPECIFICATION.md §6). Mudança incompatível no
  contrato = nova versão maior + nota de migração no `docs/contract.md`.

## Idioma

- Documentação, comentários e mensagens de commit em **português**.
- Identificadores no código e no esquema em **inglês**, `snake_case`, seguindo **o glossário do
  SPECIFICATION.md §3** (`exam_board` = banca, `answer_key` = gabarito etc.). Não invente sinônimos.
- Dados voltados ao usuário (nomes de bancas, disciplinas, assuntos) ficam em português.

## Domínio — o que o agente precisa saber

- **Banca**: organizadora da prova (Cebraspe, FGV, Vunesp, FCC, IBFC, Instituto AOCP, IDECAN, etc.).
- **Órgão**: quem contrata (PF, PRF, PC-SP, PM-MG...). **Cargo**: o posto disputado (agente, escrivão...).
- **Concurso → Prova → Questão**: um concurso (edital/ano) tem uma ou mais provas (por cargo, por
  tipo/caderno); cada prova tem questões numeradas.
- **Tipos de questão**:
  - múltipla escolha com 4 ou 5 alternativas (A–D / A–E);
  - **certo/errado** (estilo Cebraspe), sem alternativas — o gabarito é `C` ou `E`;
  - discursivas e peças ficam fora do núcleo inicial, mas o modelo deve aceitá-las no futuro.
- **Gabarito preliminar vs. definitivo**: após recursos, questões podem ter gabarito alterado ou ser
  **anuladas**. Guarde os dois e o status final.
- **Cadernos/tipos de prova**: a mesma prova pode ter versões com ordem de questões diferente
  (tipo 1, tipo 2...). Normalize para uma versão canônica e não duplique questões.
- **Texto-base**: um texto (ou imagem, tabela) pode servir a várias questões em sequência.
  Modele isso como entidade própria, não copie o texto em cada questão.
- **Disciplina → assunto**: taxonomia hierárquica (ex.: Direito Penal → Crimes contra a pessoa →
  Homicídio). Uma questão pode ter mais de um assunto.

## Fontes e direitos

- Fonte preferencial: **PDFs oficiais** de provas e gabaritos publicados pelas bancas e órgãos.
- Toda questão guarda a origem: URL/arquivo do documento, página e número original da questão.
- **Não** copie comentários, resoluções ou classificações de sites concorrentes de questões.
  Extraia das fontes oficiais.
- Guarde os PDFs originais (ou seus hashes e URLs) para permitir reprocessamento.

### Crawling

O agente **faz crawling** dos sites oficiais para descobrir provas. Regras inegociáveis abaixo;
a implementação (cliente HTTP, limites, backoff) está no SPECIFICATION.md §7.1:

- Só acessa domínios da lista de fontes permitidas (`ingest/sources.yaml`). Domínio novo entra na
  lista por commit, com decisão registrada — nunca "de passagem" durante uma execução.
- **Nunca** acessa sites agregadores de questões (QConcursos, TEC Concursos, Gran, Estratégia e
  similares), nem para "conferir".
- Respeita `robots.txt` e `Crawl-delay`; no máximo 1 requisição/s por host; `User-Agent` próprio
  com contato.
- Recebeu 403, captcha ou bloqueio: para naquele host. Recebeu 429/503: recua respeitando
  `Retry-After` (até 3 tentativas) e, se persistir, para. **Não** contorna bloqueio (sem trocar IP
  ou User-Agent, sem resolver captcha, sem login, sem paywall).
- O crawler **propõe** manifestos em `ingest/manifests/_pending/`; a ingestão só processa manifestos
  aprovados. Quem aprova é o agente (ver "Revisão pelo agente").
- Testes de crawler usam respostas gravadas em `fixtures/crawl/<fonte>/`, nunca a rede.

## Princípios de engenharia

- **Idempotência**: rodar a ingestão de novo não gera duplicatas. Use chaves naturais e um hash do
  enunciado normalizado para deduplicar.
- **Rastreabilidade acima de volume**: uma questão sem origem ou sem gabarito não entra como publicada.
  Use o `publish_status` (`draft`, `review`, `published`) em vez de descartar silenciosamente.
- **Extração assistida por LLM é permitida**, mas o resultado é validado por regras (número de
  alternativas, gabarito válido para o tipo, numeração contínua na prova) e por amostragem feita
  pelo agente (ver "Revisão pelo agente").
  Registre qual modelo/versão extraiu cada questão.
- **Migrações** sempre versionadas e reversíveis quando possível; nunca edite uma migração já aplicada.
- **Testes** para o esquema (restrições), para os parsers de cada banca (com PDFs de amostra
  pequenos em `fixtures/`) e para as consultas do contrato.
- Preserve a formatação relevante do enunciado (itálico, sublinhado, tabelas, fórmulas) no formato
  definido em `docs/content-format.md`; mudou o formato, atualize esse arquivo e o contrato.

## Revisão pelo agente

Não há etapa de revisão humana (decisão 0011). O agente faz as três revisões, com os mesmos
comandos e limiares, e registra o modelo e a versão como revisor:

- **Propostas do crawler** — `emmoni manifests show <slug>`: conferir a evidência e as páginas já
  guardadas pelo crawler (concurso policial, prova e gabarito certos, slugs do catálogo). Aprovar
  com `emmoni manifests approve`, ou rejeitar com `--reason`. A mensagem de commit diz quem aprovou.
  Não navegue fora do crawler para conferir.
- **Amostra por prova** — `emmoni review sample <concurso>/<prova>`: comparar cada questão da
  amostra com a página do PDF (enunciado, texto-base, alternativas, gabarito final, disciplina).
  Tudo confere: `emmoni review approve <concurso>/<prova> --by <modelo>`. Algo não confere: não
  aprovar; corrigir a causa e amostrar de novo.
- **Amostra de assuntos** — `emmoni review topics`: em contexto separado do `classify` — um
  subagente que lê só `data/review/assuntos/amostra.{md,json}` e `db/taxonomy/*.yaml`, sem abrir
  `classify-answers.json`, o prompt nem o raciocínio da classificação —, julgar se os assuntos
  descrevem a questão; gravar `verdict` (`ok`/`wrong`), `note` quando `wrong` e `reviewed_by`.
  Depois, `--report`.

Seja estrito: em dúvida, o veredito é `wrong` e a prova não é aprovada. Um veredito humano
posterior prevalece sobre o do agente.

## Fluxo de trabalho

1. Ler `MISSION.md`, `SPECIFICATION.md`, este arquivo, `docs/progress/STATUS.md` e
   `docs/contract.md`. O `STATUS.md` diz onde a última sessão parou. Conforme a tarefa, ler
   também `docs/content-format.md` (formato do enunciado), `docs/operations.md` (crawl diário) e
   as decisões citadas em `docs/decisions/`.
2. Seguir os **marcos do SPECIFICATION.md §10 em ordem** (M0 → M6). Não comece um marco antes de o
   anterior cumprir seu critério de "pronto". O M1 (esquema, contrato e seed) destrava o agente de
   front-end — ele tem prioridade sobre volume de questões.
3. Dentro de um marco, trabalhar em incrementos pequenos e verticais: uma prova completa
   (PDF → banco → consulta no esquema `api`) antes de ampliar.
4. Rodar `make gates` antes de entregar. Não entregue com gates falhando; se algo foi pulado, diga.
5. Atualizar `docs/contract.md` e o seed sempre que o esquema `api` mudar.
6. Registrar decisões de arquitetura em `docs/decisions/NNNN-titulo.md` (contexto, decisão,
   consequências — curto).
7. **Antes de encerrar a sessão**, registrar o progresso em `docs/progress/`: criar
   `AAAA-MM-DD-<assunto>.md` no formato de `docs/progress/README.md`, com o resultado do
   `make gates` e o que ficou sem verificar, e **sobrescrever** o `STATUS.md` com o estado atual.
   O `STATUS.md` não é histórico: o que foi feito fica no registro da sessão; no `STATUS.md` ficam
   só o marco, o que está em andamento, os próximos passos, os bloqueios e os números de agora.

## Sessões paralelas e worktrees

Várias sessões podem rodar ao mesmo tempo, cada uma num worktree do git (decisão 0019). Elas
**compartilham** o mesmo Postgres (`docker compose` com nome e porta fixos): os bancos `emmoni` e
`emmoni_test` são um só por máquina. Já o `data/` de cada worktree é uma **cópia** que não volta
para o checkout principal.

- Comandos que escrevem no banco — `make gates`, `make test`, `make migrate`, `make seed`,
  `make db-reset`, `emmoni ingest`, `emmoni review approve`, `emmoni crawl` — rodam em **uma
  sessão por vez**. Antes de rodá-los, confira se outra sessão não está no meio de um deles; em
  dúvida, pergunte ao dono.
- O que precisa sobreviver ao worktree vai para o git: aprovações (`ingest/approvals/`), revisões
  de OCR (`ingest/ocr/`), `classify-answers.json`, manifestos. O resto de `data/` (PDFs, staging,
  amostras) é reproduzível e fica para trás quando o worktree é apagado.
- Carregou no banco a partir de um worktree? O registro da sessão diz qual worktree e qual commit,
  para que o checkout principal consiga reproduzir o mesmo estado depois do merge.

## Estrutura e tecnologia

A estrutura do repositório, a stack e os comandos estão no SPECIFICATION.md (§1, §2 e §9).
Para mudar qualquer especificação: escreva a decisão em `docs/decisions/` e atualize o
SPECIFICATION.md **no mesmo commit**. Nunca deixe o código divergir da especificação em silêncio.
