# SPECIFICATION — emmoni

Especificações técnicas para cumprir o [MISSION.md](MISSION.md). As regras de trabalho estão no
[AGENTS.md](AGENTS.md). Em caso de conflito, **este documento manda nas decisões técnicas** e o
AGENTS.md manda no processo. Para mudar uma especificação: registre a decisão em `docs/decisions/`
e atualize este arquivo no mesmo commit.

---

## 1. Stack

| Camada | Escolha | Motivo |
|---|---|---|
| Banco de dados | **PostgreSQL 17** | Busca textual em português (`tsvector`), `unaccent`, `pg_trgm`, `ltree`, JSONB, restrições fortes. |
| Extensões | `unaccent`, `pg_trgm`, `ltree`, `pgcrypto` | Busca sem acento, busca aproximada, taxonomia hierárquica, UUIDs/hashes. |
| Migrações | **dbmate** (SQL puro, `-- migrate:up` / `-- migrate:down`) | Independente de linguagem; o agente de front-end lê o mesmo SQL. |
| Ingestão | **Python 3.12**, gerenciado com **uv** | Ecossistema de PDF/OCR. |
| PDF | **PyMuPDF** (texto, layout, imagens); **ocrmypdf + Tesseract `por`** como fallback para PDFs escaneados | |
| Crawling | **httpx** (HTTP/2, retries, requisições condicionais), **selectolax** (HTML), `urllib.robotparser`; **Playwright** só para fontes marcadas `js: true` | Leve por padrão; navegador só quando o site exige JavaScript. |
| Classificação e estruturação por LLM | **O próprio agente** que opera o repositório, por arquivos de tarefa e resposta no staging (decisão 0006) | Sem SDK, sem credencial, sem custo por token. A resposta é validada por pydantic e pela taxonomia. |
| Validação em Python | **pydantic v2** | Mesmo modelo para as respostas do agente, o staging e a carga. |
| Acesso ao banco | **psycopg 3** (SQL explícito, sem ORM) | O esquema é o produto; nada de esquema implícito em ORM. |
| Testes | **pytest** contra um Postgres descartável (docker compose, banco `emmoni_test`) | |
| Qualidade de código | **ruff** (lint + format), **mypy** em modo estrito no pacote `ingest` | |
| Ambiente local | **docker compose** (serviço `db`, porta `55432` no host), **Makefile** como ponto de entrada | Porta alta para não colidir com outros Postgres da máquina. |
| Produção da API | **Google Cloud Run** (`emmoni-prod`, `southamerica-east1`): imagem imutável com Postgres 17 + PostgREST e os dados dentro, `max-instances=1`, corte de gasto por budget (decisão 0022, `docs/DEPLOY.md`); único caminho das questões reais para o público, nunca um repositório público (decisão 0028) | Só leitura em produção: sem VM, sem rede de banco, sem segredo, escala a zero. |
| API HTTP (opcional) | **PostgREST v12.2.3** sobre o esquema `api` como `emmoni_web` (serviço `api`, perfil `api`, porta `53000`; decisão 0021) | O contrato por HTTP sem código de servidor: views e funções do `api`, e nada mais. |
| Versões das ferramentas | **mise** (`mise.toml`) fixa uv e dbmate e ativa o `.venv`; o uv instala o Python de `.python-version` | Ambiente reproduzível sem instalar nada globalmente. |

Variáveis de ambiente: a lista completa está em `.env.example` (nunca commitar `.env`). O Makefile
tem padrões de desenvolvimento para todas as URLs do banco, então um repositório limpo funciona sem
`.env`.

| Variável | Uso |
|---|---|
| `DATABASE_URL` / `DATABASE_URL_OWNER` | Banco `emmoni` como `emmoni_ingest` / `emmoni_owner` (migrações). |
| `DATABASE_URL_TEST`, `_TEST_OWNER`, `_TEST_WEB` | Banco `emmoni_test`, um por papel. |
| `EMMONI_CLASSIFIER` | Identificador de quem classifica, gravado em `topics.json` (padrão `agent`). |
| `EMMONI_DATA_DIR` | Raiz de `raw/`, `staging/`, `assets/`, `crawl/`. |
| `EMMONI_CRAWL_CONTACT` | Contato no `User-Agent` do crawler. |
| `EMMONI_API_PORT` | Porta da API HTTP no host (padrão `53000`). |
| `EMMONI_DB_LOCK` | Arquivo da trava do banco (padrão `${XDG_RUNTIME_DIR:-/tmp}/emmoni-db.lock`; decisão 0025). |
| `EMMONI_DB_LOCK_WAIT` | Espera máxima pela trava do banco, em segundos (padrão `1800`); estourou, sai com 75. |
| `EMMONI_DB_LOCKED` | Definida pelo processo que segura a trava; os filhos não travam de novo. Não definir à mão. |

---

## 2. Estrutura do repositório

```
emmoni/
├── MISSION.md  AGENTS.md  SPECIFICATION.md
├── Makefile  docker-compose.yml  .env.example  pyproject.toml  mise.toml  .python-version
├── docs/
│   ├── contract.md          # contrato com o front-end (seção 6)
│   ├── DEPLOY.md            # deploy da API no Google Cloud (agente atlas, decisão 0022)
│   ├── CYBERSECURITY.md     # segurança da produção e contrato de correção (agente cerberus)
│   ├── security/reports/    # relatórios datados do cerberus
│   ├── content-format.md    # formato do conteúdo das questões (seção 5)
│   ├── coverage.md          # relatório de cobertura gerado (seção 8)
│   ├── progress/            # STATUS.md + um registro por sessão (ver docs/progress/README.md)
│   └── decisions/           # NNNN-titulo.md, uma decisão por arquivo
├── db/
│   ├── init/                # SQL do init do container: cria os papéis (cluster)
│   ├── migrations/          # dbmate: AAAAMMDDHHMMSS_descricao.sql
│   ├── schema.sql           # dump gerado pelo dbmate (commitado, nunca editado à mão)
│   ├── checks/              # consultas de qualidade (seção 8)
│   ├── catalog.yaml         # bancas, órgãos e cargos reais (seção 4.1, decisão 0005)
│   ├── taxonomy/            # disciplinas e assuntos em YAML (seção 4.4)
│   └── seed/seed.sql        # dados de exemplo para o front-end
├── ingest/                  # pacote Python
│   ├── sources.yaml         # fontes permitidas para crawling (seção 7.1)
│   ├── crawlers/            # um módulo por fonte: cebraspe.py, fgv.py, ...
│   ├── approvals/           # aprovação de cada prova, com a impressão digital (seção 8)
│   ├── manifests/           # um YAML por concurso aprovado (seção 7.2)
│   │   ├── _pending/        # manifestos propostos pelo crawler, aguardando aprovação
│   │   └── _rejected/       # propostas rejeitadas, com o motivo (decisão 0007)
│   ├── ocr/                 # correções revisadas pelo agente (OCR e fonte sem mapeamento), um YAML por PDF (decisões 0018 e 0020)
│   ├── parsers/             # um módulo por banca: cebraspe.py, fgv.py, ...
│   ├── cli.py               # comando `emmoni`
│   └── ...
├── deploy/                  # imagem de produção (Dockerfile, build.sh), audit.py, budget-cap/ (decisão 0022)
├── .claude/agents/          # atlas (deploy) e cerberus (segurança)
├── scripts/                 # scripts de apoio chamados pelo Makefile
├── fixtures/                # PDFs (pdf/) e respostas gravadas das fontes (crawl/<fonte>/) para testes
├── tests/
└── data/                    # ignorado pelo git: raw/, staging/, ocr/, assets/, crawl/
```

---

## 3. Convenções de nomes

Identificadores do esquema e do código em **inglês, `snake_case`**, tabelas no **singular**.
Glossário obrigatório (use sempre estes nomes):

| Domínio (pt) | Esquema (en) |
|---|---|
| Banca | `exam_board` |
| Órgão | `agency` |
| Cargo | `position` |
| Carreira (PF, PRF, PC, PM...) | `career` (enum) |
| Concurso | `contest` |
| Prova | `exam` |
| Caderno / tipo de prova | `booklet` |
| Questão | `question` |
| Alternativa | `question_option` |
| Gabarito | `answer_key` (colunas `answer_*`) |
| Texto-base | `passage` |
| Disciplina | `subject` |
| Assunto | `topic` |
| Documento de origem (PDF) | `source_document` |

Textos voltados ao usuário (nomes de bancas, disciplinas etc.) ficam em português nos **dados**.
Todo registro de catálogo tem um `slug` estável (`cebraspe`, `pf`, `lingua-portuguesa`) usado em URLs
pelo front-end.

---

## 4. Modelo de dados

O DDL de verdade está em `db/migrations/` (e no dump `db/schema.sql`); os esboços abaixo resumem
e não repetem cada detalhe. Se divergirem, valem as migrações, e este texto deve ser corrigido.

Todas as tabelas têm `created_at timestamptz not null default now()` e, quando mutáveis,
`updated_at` mantido por trigger. Chaves primárias: `bigint generated always as identity` para
catálogos; `uuid` (`gen_random_uuid()`) para `question` e `passage`, que são expostos em URLs.

### 4.1 Catálogo

```sql
create type career as enum (
  'pf', 'prf', 'policia_civil', 'policia_militar', 'bombeiro_militar',
  'policia_penal', 'policia_legislativa', 'guarda_municipal', 'policia_cientifica', 'outra'
);
create type government_level as enum ('federal', 'estadual', 'distrital', 'municipal');

create type education_level as enum ('fundamental', 'medio', 'superior');
create domain slug as text check (value ~ '^[a-z0-9]+(-[a-z0-9]+)*$');

exam_board (id, slug unique, name, short_name)            -- Cebraspe, FGV, Vunesp...
agency     (id, slug unique, name, short_name, career, level government_level,
            state text null)                               -- UF; null se e só se federal
position   (id, agency_id, slug, name, education_level)    -- unique (agency_id, slug)
```

O catálogo real é **curado em `db/catalog.yaml`** e carregado por `emmoni catalog load`
(idempotente, por slug). Manifestos só citam slugs que existem nele (decisão 0005). Cada órgão
pode ter `aliases` — os prefixos com que as fontes o escrevem nas URLs e nomes de evento (`PF`,
`DPF`, `PC_DF`) —, usados só pelo crawler para reconhecer o órgão; não vão para o banco
(decisão 0007). Cada cargo pode ter `aliases` — outras palavras com que as fontes o escrevem
(`PRACA`, `CADETE`, `ASPIRANTE`) —, com o mesmo uso e o mesmo destino (decisão 0008).

### 4.2 Concurso, prova e origem

```sql
create type document_kind as enum
  ('exam', 'answer_key_preliminary', 'answer_key_final', 'notice', 'appeal_result');

source_document (id, kind, url, sha256 unique, local_path, page_count,
                 fetched_at, ocr_applied boolean)

contest (id, slug unique, agency_id, exam_board_id, year smallint, notice_number,
         name)                                   -- "PF 2021 — Agente"

exam    (id, contest_id, slug, name, applied_on date, shift text null,
         canonical_booklet text,                  -- caderno usado como referência
         exam_document_id, answer_key_preliminary_document_id,
         answer_key_final_document_id,
exam_document (exam_id, source_document_id, kind document_kind, position)
            -- todos os PDFs da prova; um tipo pode ter vários (decisão 0009)
         publish_status)                          -- unique (contest_id, slug)

exam_position (exam_id, position_id)              -- uma prova pode servir vários cargos
                                                  -- pk (exam_id, position_id)
```

`exam.publish_status` é a aprovação da prova pela amostragem (seção 8): uma questão só aparece no
contrato se ela **e** a prova estiverem `published`.

Cadernos com ordem diferente: só o **caderno canônico** gera questões. Outros cadernos, se
necessários, entram em `booklet_mapping (exam_id, booklet, original_number, question_id)`.

### 4.3 Questões

```sql
create type question_type   as enum ('multiple_choice', 'true_false', 'essay');
create type answer_status   as enum ('valid', 'changed', 'annulled');  -- após recursos
create type publish_status  as enum ('draft', 'review', 'published');  -- também em exam

passage (id uuid, exam_id, body_md, source_page,
         source_key text null)                  -- rótulo na prova ("2A1-I"); unique (exam_id, source_key)

question (
  id               uuid primary key,
  exam_id          bigint not null references exam,
  number           smallint not null,           -- número no caderno canônico
  type             question_type not null,
  subject_id       bigint references subject,   -- disciplina (do cabeçalho da prova)
  passage_id       uuid null references passage,
  statement_md     text not null,               -- enunciado (seção 5)
  answer_preliminary text null,                 -- 'A'..'E' ou 'C'/'E'
  answer_final       text null,
  answer_status    answer_status not null default 'valid',
  statement_hash   text not null,               -- sha256 da questão normalizada (seção 5)
  duplicate_of     uuid null references question,
  source_page      smallint not null,
  command_page     smallint null,               -- onde começa o comando do grupo (decisão 0027)
  extracted_by     text not null,               -- ex.: 'cebraspe-parser@1 + claude-sonnet-5-5'
  publish_status   publish_status not null default 'draft',
  review_reasons   text[] not null default '{}', -- motivos da etapa validate (decisão 0005)
  search_vector    tsvector not null,           -- mantido por trigger (seção 4.5)
  unique (exam_id, number)
)

question_option (question_id uuid, letter text check ('A'..'E'), body_md text,
                 primary key (question_id, letter))   -- só para multiple_choice

asset (id, sha256 unique, mime_type, width, height, alt_text, storage_key)
question_asset / passage_asset (owner_id, asset_id, position)
```

Restrições obrigatórias (no banco, não só na ingestão):

- `true_false` → gabaritos em `('C','E')` e **nenhuma** linha em `question_option`.
- `multiple_choice` → gabaritos em `('A'..'E')`; a letra precisa existir em `question_option`
  (verificado por trigger de constraint diferida).
- `answer_status = 'annulled'` → `answer_final is null`.
- `answer_status = 'changed'` → os dois gabaritos preenchidos e diferentes; `valid` → iguais
  quando os dois existem.
- `essay` → sem gabarito.
- O texto-base precisa ser da mesma prova da questão (FK composta `(passage_id, exam_id)`).
- `publish_status = 'published'` exige `answer_final` preenchido **ou** questão anulada, e
  `subject_id` preenchido.

### 4.4 Taxonomia

```sql
subject (id, slug unique, name)                          -- Língua Portuguesa, Direito Penal...
topic   (id, subject_id, name, path ltree unique)        -- direito_penal.crimes_contra_pessoa.homicidio
topic_ancestor (topic_id, ancestor_id)                   -- fecho transitivo, mantido por trigger
question_topic (question_id, topic_id, origin text,      -- 'manual' | 'llm' | 'rule'
                confidence real null,
                primary key (question_id, topic_id))
```

O identificador público de um assunto é o **`path`**: o primeiro rótulo é o slug da disciplina com
`-` trocado por `_`, e os seguintes são os slugs dos ancestrais (triggers garantem isso e que o pai
existe). O `path` é **imutável**; renomear um assunto muda só o `name`. `topic_ancestor` liga cada
assunto a si mesmo e a todos os ancestrais; é o que torna baratas as contagens com subassuntos.

A taxonomia é **curada em `db/taxonomy/*.yaml`** e carregada por `emmoni taxonomy load`
(idempotente, por slug/path; assuntos que saem dos arquivos são apenas avisados, nunca apagados). O LLM de classificação só escolhe entre assuntos existentes; nunca cria
assuntos novos — sugere-os num relatório para revisão.

### 4.5 Busca textual

- Configuração de busca `pt_unaccent` (dicionário `portuguese` + `unaccent`).
- `question.search_vector` = enunciado (peso A) + alternativas e texto-base (peso B), depois de
  `md_plain()` tirar a marcação. Como alternativas e texto-base moram em outras tabelas, o vetor é
  mantido por trigger: mudar uma alternativa ou um texto-base recalcula as questões afetadas.
- Índices: GIN em `search_vector`; GIN `gin_trgm_ops` em `statement_md` para busca por trecho;
  btree nos filtros (`exam_id`, `subject_id`, `publish_status`); GIST em `topic.path`.

### 4.6 Papéis do banco

| Papel | Permissões |
|---|---|
| `emmoni_owner` | Dono do esquema; usado só pelas migrações. |
| `emmoni_ingest` | Leitura/escrita nas tabelas; usado pela ingestão. |
| `emmoni_web` | **Somente leitura**, e somente no esquema `api` (seção 6). Usado pelo front-end. |

Esquemas: `public` (tabelas internas), `crawl` (estado do crawler), `api` (contrato) e `ext`
(extensões, com `USAGE` para todos; o `search_path` do banco é `public, ext`). Os papéis são do
cluster e nascem em `db/init/`; as permissões são dadas por `ALTER DEFAULT PRIVILEGES` na migração
de fundação, então todo objeto criado depois pelo `emmoni_owner` já nasce com as permissões
certas. Funções não são executáveis por `PUBLIC`.

---

### 4.7 Estado do crawler

Esquema separado `crawl`, **fora** do contrato (o front-end não vê):

```sql
create type discovery_status as enum
  ('pending', 'proposed', 'approved', 'rejected', 'out_of_scope', 'ingested');

crawl.page (url primary key, source_slug, last_fetched_at, http_status, etag,
            last_modified, content_sha256, next_fetch_at)

crawl.discovered_document (
  id, url unique, source_slug,
  found_on_url,            -- página onde o link foi encontrado (evidência)
  link_text,
  guessed_kind document_kind null,
  guessed_contest_slug text null,
  guessed jsonb,           -- órgão, cargo, ano, banca + confiança de cada campo
  status discovery_status not null default 'pending',
  status_reason text null, -- ex.: 'fora do escopo: concurso de prefeitura (não policial)'
  first_seen_at, last_seen_at
)
```

A página de cada concurso encontrado também é uma linha de `discovered_document` (`guessed_kind`
nulo; `guessed` com órgão, ano e fase): é nela que ficam o `out_of_scope` com motivo dos concursos
não policiais e o `pending` dos órgãos ainda fora do catálogo (decisão 0007). Os status são
derivados a cada execução dos diretórios de manifestos e de `source_document` (`ingested`).

## 5. Formato do conteúdo

`statement_md`, `body_md` das alternativas e dos textos-base usam **Markdown restrito**,
especificado em `docs/content-format.md`:

- CommonMark + tabelas GFM.
- Itálico `*x*`, negrito `**x**`, sublinhado `<u>x</u>` (única tag HTML permitida).
- Fórmulas em LaTeX: `$...$` inline, `$$...$$` em bloco.
- Imagens: `![texto alternativo](asset:<sha256>)` — o front-end resolve `asset:` para uma URL.
- Proibido: HTML arbitrário, links externos, cabeçalhos (`#`).
- Texto literal: `$`, `*`, `_`, `` ` ``, `<` e `\` do original escapados com `\` (`R\$ 10,00`), decisão 0023.
- Normalização: Unicode NFC, hifenização de fim de linha do PDF removida, espaços colapsados,
  aspas e travessões preservados.

`statement_hash` = sha256 de **enunciado + alternativas (em ordem) + texto-base**, cada parte
normalizada: NFC → minúsculas → remover acentos → remover markdown e pontuação → colapsar espaços;
imagens valem pelo sha256. Só o enunciado não basta: enunciados genéricos ("Assinale a alternativa
correta") se repetem entre questões diferentes. Implementação: `ingest/content.py`.

---

## 6. Contrato com o front-end

O front-end **só** acessa o esquema `api`, com o papel `emmoni_web`. Tabelas internas podem mudar
livremente; o esquema `api` é o contrato e é versionado em `docs/contract.md` (versão semântica;
mudança incompatível = versão maior + nota de migração). **O `docs/contract.md` é a referência
para o front-end**: formatos de resposta, filtros, erros e garantias. Esta seção fixa os requisitos.

Objetos mínimos do esquema `api` (as funções devolvem `jsonb`):

| Objeto | Descrição |
|---|---|
| `api.question` (view) | Questões `published`, com banca, órgão, cargos, concurso, ano, disciplina, assuntos, gabarito final, status do gabarito, origem. Alternativas como `jsonb` (`[{letter, body_md}]`). |
| `api.passage` (view) | Textos-base. |
| `api.exam_board`, `api.agency`, `api.position`, `api.subject`, `api.topic`, `api.exam` (views) | Catálogos para montar filtros e páginas de prova, com contagem de questões publicadas. |
| `api.search_questions(filters jsonb, query text, page_size int, cursor text)` | Busca com filtros e texto; retorna `{total, items, next_cursor}`. Paginação por **keyset**, nunca `offset`. Ordem: ano decrescente, concurso, prova, número (sem relevância na v1). |
| `api.facet_counts(filters jsonb, query text)` | Contagens por banca, órgão, carreira, cargo, ano, disciplina, assunto, tipo — **disjuntivas** (cada faceta ignora o próprio filtro). |
| `api.get_question(id uuid)` | Uma questão completa. |
| `api.asset_url(sha256 text)` | Resolve `asset:` para caminho público. |

Formato de `filters` (todos opcionais, valores por **slug**; listas = OU, chaves diferentes = E):

```json
{
  "exam_board": ["cebraspe"],
  "agency": ["pf", "prf"],
  "position": ["agente"],
  "career": ["pf"],
  "year": {"from": 2018, "to": 2024},
  "subject": ["lingua-portuguesa"],
  "topic": ["direito_penal.crimes_contra_pessoa"],   // inclui descendentes
  "type": ["true_false"],
  "include_annulled": false
}
```

Implementação: views rodam com as permissões do dono; as funções são `SECURITY DEFINER` com
`search_path` fixo, validam toda entrada (erro `22023` para filtro desconhecido ou mal formado) e só
interpolam valores do usuário com `%L`. A montagem do SQL fica em funções internas de `public`
(`search_condition`, `search_from`, `question_docs`), inacessíveis ao `emmoni_web`.

Acesso por HTTP (decisão 0021): `make api-up` sobe o PostgREST com `emmoni_web` e só o esquema
`api`; as views viram `GET /<view>` (no máximo 100 linhas por requisição) e as funções
`POST /rpc/<função>`, com o erro `22023` em HTTP 400. Em produção, a mesma API roda no Cloud Run (decisão 0022, `docs/DEPLOY.md`).

Requisitos de desempenho (com ≥ 100 mil questões publicadas, máquina de desenvolvimento):
`search_questions` p95 < 150 ms; `facet_counts` p95 < 300 ms. Medidos por `make bench`, que cria
o banco descartável `emmoni_bench`, multiplica o seed até ~100 mil questões e falha se uma meta não
for atingida.

O **seed** (`db/seed/seed.sql`) deve cobrir: ≥ 3 bancas, ≥ 4 órgãos, ≥ 60 questões publicadas,
ambos os tipos (`multiple_choice` e `true_false`), questões com texto-base compartilhado, com imagem,
com tabela, anuladas e com gabarito alterado. Dados do seed são marcados com `contest.slug` prefixado
por `seed-` e podem ser fictícios. O `seed.sql` é **gerado** por `scripts/build_seed.py`
(`make seed-build`); o lint falha se o arquivo estiver desatualizado. As imagens do seed ficam em
`db/seed/assets/` e o `make seed` as copia para `data/assets/<sha256>.<ext>`, que é o
`storage_key` padrão de um asset (URL pública = `setting.asset_base_url` + `storage_key`).

---

## 7. Pipeline de ingestão

Comando único: `emmoni` (definido em `pyproject.toml`). Cada etapa grava seu resultado em disco,
pode ser rerodada isoladamente e é **idempotente**.

```
crawl ─► propose ─► [aprovação] ─► manifest ─► fetch ─► extract ─► segment ─► structure ─► answer-key ─► validate ─► classify ─► load
```

### 7.1 Descoberta (crawler)

O crawler encontra provas novas e **propõe** manifestos; ele não ingere nada.

**Fontes permitidas** — `ingest/sources.yaml` é a única lista de domínios que o crawler pode acessar:

```yaml
- slug: cebraspe
  kind: exam_board               # exam_board | agency
  base_url: https://www.cebraspe.org.br/concursos/
  allowed_prefixes: [https://www.cebraspe.org.br/concursos/, https://cdn.cebraspe.org.br/]
  crawler: cebraspe              # módulo em ingest/crawlers/; null = só a etapa fetch (decisão 0017)
  js: false
  max_depth: 3
  recrawl: {listing: 1d, contest_open: 3d, contest_closed: never}
  auto_approve: false
  extra_content_types: []        # opcional; ex.: [application/json] (decisão 0004)
  allow_http: false              # opcional; exceção ao HTTPS por fonte (decisão 0017)
```

**Bloqueadas por padrão** (lista `denylist` no mesmo arquivo, checada antes de qualquer requisição):
agregadores de questões e cursinhos — qconcursos.com, tecconcursos.com.br, grancursosonline.com.br,
estrategiaconcursos.com.br e similares. Incluir domínio novo em qualquer das listas exige registro em
`docs/decisions/`.

**Regras de cortesia** (implementadas num cliente HTTP único, `ingest/crawlers/http.py`, que todo
crawler é obrigado a usar):

- `robots.txt` buscado e cacheado por 24 h por host; URL proibida não é acessada; `Crawl-delay`
  respeitado.
- No máximo **1 requisição/s por host** e **1 conexão simultânea por host**.
- `User-Agent: emmoni-bot/<versão> (+<EMMONI_CRAWL_CONTACT>)`.
- Requisições condicionais (`ETag`, `If-Modified-Since`); página sem mudança (`content_sha256`
  igual) não é reprocessada.
- 429/503 → backoff exponencial respeitando `Retry-After`, até 3 tentativas. 403, captcha ou
  bloqueio → para aquele host na execução e registra. **Proibido** contornar: trocar IP ou
  User-Agent, resolver captcha, fazer login, acessar área paga.
- Limites por execução: `max_depth` da fonte, 2.000 páginas por fonte, PDFs até 50 MB, só
  `application/pdf` e `text/html`.
- Só `https`, salvo fonte com `allow_http: true` (exceção por host que não aceita HTTPS, como
  `www.cespe.unb.br` — decisão 0017). Redirecionamentos seguidos à mão: o destino passa pelas
  mesmas checagens. `robots.txt`
  pela RFC 9309 (4xx → sem restrições; 5xx ou falha → tudo proibido). A etapa `fetch` usa o mesmo
  cliente (decisão 0003).
- Tipos além de PDF e HTML só por fonte, no campo `extra_content_types` de `sources.yaml` (ex.: a API
  JSON do Cebraspe, decisão 0004).

**Classificação do que foi encontrado:**

1. **Regras** primeiro: padrões de texto do link, nome do arquivo e título da página
   (`gabarito definitivo`, `caderno de prova`, `prova objetiva`, `edital de abertura`...) →
   `guessed_kind`.
2. **Escopo**: o órgão é casado com o catálogo `agency` pelos `aliases` (seção 4.1); os cargos,
   com `position` do órgão. Concurso fora do escopo do MISSION.md → `out_of_scope` com motivo.
   Órgão policial que não existe no catálogo → proposto como novo `agency` no relatório, não
   criado automaticamente (o detalhe do concurso só é lido depois que o órgão entra no catálogo).
   Prova cujo cargo não está no catálogo fica fora da proposta, com o motivo registrado.
3. **LLM** só quando as regras não resolvem: recebe título da página, texto do link e trecho ao redor,
   responde por JSON schema com confiança por campo (seção 7.4).

**Proposta:** quando um concurso tem ao menos prova + um gabarito identificados, o crawler escreve
`ingest/manifests/_pending/<contest-slug>.yaml` no formato da seção 7.2, mais um bloco `evidence`
(URL da página, texto do link e confiança de cada campo). A proposta pendente é **do crawler**: é
reescrita quando a fonte muda (e só então; não tem data). O manifesto aprovado é curado à mão e
**nunca** é reescrito pelo crawler: documento que chegar depois (ex.: o gabarito definitivo) para
um concurso aprovado aparece no relatório e em `discovered_document` como `pending`, e a pessoa
edita o manifesto e reroda a ingestão daquela prova (decisão 0007). Proposta cujo concurso foi
visto e lido na execução e não rendeu proposta com aquele slug (regra mudou, saiu do escopo, mudou
de slug) é apagada de `_pending/`, com o motivo no relatório; falha de rede não apaga nada
(decisão 0012). Caderno único com um gabarito por bloco (básicos, específicos) recebe a lista dos
gabaritos, na ordem dos itens (decisão 0012).

**Aprovação:** `emmoni manifests approve <slug>` valida a proposta (modelo da seção 7.2 e slugs do
catálogo) e a move para `ingest/manifests/`. `emmoni manifests reject <slug> --reason "..."` move
para `ingest/manifests/_rejected/` com o motivo, e o crawler não volta a propor o concurso. Os três
diretórios ficam no git. Enquanto
`auto_approve: false` (padrão), toda proposta passa por revisão explícita, feita pelo agente
(decisão 0011, AGENTS.md "Revisão pelo agente"). Ligar `auto_approve` numa
fonte exige decisão registrada e só vale para propostas em que todos os campos vieram de regras ou
têm confiança ≥ 0,9.

**Estado e cache:** `crawl.page` guarda, por URL, `etag`, `last_modified`, `content_sha256`,
`http_status` e `next_fetch_at` (calculado de `recrawl` da fonte: `listing` para a listagem,
`contest_open`/`contest_closed` para a página do concurso; `never` = busca uma vez). O corpo fica em
`data/crawl/<fonte>/<sha256>`; página que não venceu é relida do cache, sem rede, de modo que uma
regra nova se aplica sem recrawl. Erro HTTP agenda nova tentativa em 1 dia. `--force` ignora
`next_fetch_at`.

**Agendamento:** `emmoni crawl --all` (ou `make crawl`) roda uma vez por dia, por um timer do
systemd ou cron documentado em `docs/operations.md`. O comando respeita `next_fetch_at`, então
rodar com mais frequência não aumenta a carga nos sites. Isso garante o critério de "até 7 dias"
do MISSION.md.

### 7.2 Manifesto

Cada concurso aprovado é descrito por um YAML em `ingest/manifests/<contest-slug>.yaml`
(escrito à mão ou aprovado a partir de uma proposta do crawler):

```yaml
contest: pf-2021
agency: pf
exam_board: cebraspe
year: 2021
notice_number: "1/2021"
exams:
  - slug: agente
    positions: [agente]
    applied_on: 2021-05-23
    canonical_booklet: "1"
    first_number: 1                # opcional; caderno que começa no meio (PRF 2021: 9)
    documents:
      exam: https://.../prova_agente.pdf
      answer_key_preliminary: https://.../gabarito_preliminar.pdf
      answer_key_final: https://.../gabarito_definitivo.pdf   # ou lista de URLs (decisão 0009)
    subjects_by_range:            # opcional: mapa número → disciplina
      - {from: 1, to: 20, subject: lingua-portuguesa}
```

### 7.3 Etapas

| Etapa | Entrada → saída | Detalhes |
|---|---|---|
| `fetch` | manifesto → `data/raw/<sha256>.pdf` + `source_document` | Não baixa de novo se o sha256 já existe. Respeita `robots.txt`, 1 requisição/s por host, `User-Agent` identificado. |
| `extract` | PDF → `data/staging/<exam>/pages.json` | PyMuPDF com blocos e posições; OCR (`ocrmypdf` + Tesseract `por`) se a página não tiver texto, com revisão linha a linha pelo agente em `ingest/ocr/<sha256>.yaml` (decisão 0018); nos cadernos do site antigo do Cebraspe (fonte `cespe-unb`), vão entre colunas, números de item, negrito/itálico e "ℓ" deduzidos do documento, e as mesmas correções revisadas valem para linhas em fonte sem mapeamento Unicode (decisão 0020); imagens exportadas para `data/assets/<sha256>.<ext>`. |
| `segment` | páginas → questões brutas | Parser da banca (`ingest/parsers/<banca>.py`): separa cabeçalhos de disciplina, textos-base, questões e alternativas por regras. |
| `structure` | questões brutas → `questions.json` | Agente só onde as regras falham (tabelas, fórmulas, layout em colunas), pelo mesmo mecanismo de tarefas/respostas do `classify`. Saída validada por pydantic; inválida → `review`. |
| `answer-key` | PDFs de gabarito → gabaritos | Preliminar e definitivo; deriva `answer_status`. |
| `validate` | `questions.json` | Numeração contínua, alternativas compatíveis com o tipo, gabarito válido, enunciado não vazio, imagens resolvidas. Falha → questão fica `review`, com motivo registrado. |
| `classify` | questões → assuntos | Disciplina vem do cabeçalho/manifesto; assuntos pelo agente dentro da taxonomia, com `confidence`. Grava `classify-tasks.json` com o que falta; lê `classify-answers.json`. Assunto de outra disciplina → `review`; sem resposta, ou sem assunto com confiança ≥ 0,6 → `draft`, e a questão volta às tarefas (decisão 0010). |
| `load` | staging → banco | Uma transação por prova; upsert por `(exam_id, number)`; deduplicação por `statement_hash` marca `duplicate_of` (questões em `review` ficam fora: o conteúdo extraído está incompleto). |

No Cebraspe (certo/errado), o **comando** do grupo abre o enunciado de cada item, e o texto
rotulado ou a situação hipotética vira texto-base. Na múltipla escolha, o texto-base vale para a
primeira questão depois dele e para as que o citam pelo rótulo ("texto 2A1-I", "figura 5A2");
as demais não o herdam (decisão 0013). O `load` grava `review` quando há motivo de
revisão, `published` quando não há motivo e há assunto, e `draft` quando falta assunto. A prova só é
publicada depois da amostragem (decisão 0005).

Comandos:

```
emmoni catalog load                 # db/catalog.yaml → banco
emmoni crawl <fonte>|--all [--force]   # descobre documentos e propõe manifestos
emmoni manifests pending|show <slug>|approve <slug>|reject <slug> --reason "..."
emmoni ingest <manifest>            # todas as etapas
emmoni ingest <manifest> --step <s> # uma etapa
emmoni review list|show [<concurso>/<prova>]   # fila de questões em review, com motivos
emmoni review sample <concurso>/<prova> [--n 10] # amostra em HTML, ao lado da página do PDF
emmoni review approve <concurso>/<prova>        # publica a prova (exige amostra)
emmoni review restore                           # publica as provas que conferem com ingest/approvals/
emmoni review topics [--n 50] [--report]        # amostra de classificações por assunto (M4)
emmoni taxonomy load
emmoni check                        # seção 8
emmoni coverage                     # gera docs/coverage.md
```

### 7.4 Uso do LLM

O LLM é **o agente que opera o repositório** (Claude Code ou equivalente), não um serviço chamado
pelo código. Não há SDK, chave de API nem cache de respostas (decisão 0006).

- Prompts versionados em `ingest/prompts/`, com o nome da versão gravado em `topics.json` /
  `extracted_by`. O prompt é a instrução que a etapa entrega ao agente no arquivo de tarefas.
- Cada etapa que precisa do agente grava um arquivo de **tarefas** no staging da prova e lê um
  arquivo de **respostas** escrito pelo agente; a etapa valida as respostas (pydantic + regras) e
  nunca aceita texto livre. Rerodar a etapa com as mesmas respostas é idempotente.
- `classify` (`ingest/classify.py`, prompt `ingest/prompts/classify@1.md`):
  `classify-tasks.json` traz, por questão, a disciplina, os assuntos permitidos (`allowed_topics`),
  o texto-base e o enunciado; `classify-answers.json` traz `{número: {topics: [{path, confidence}],
  suggested_topic}}`. Só entram assuntos da disciplina da questão; no máximo 3. Sugestões de assunto
  novo vão para `topics.json`, para curadoria da taxonomia. `EMMONI_CLASSIFIER` identifica quem
  respondeu. O `classify-answers.json` é o único arquivo de `data/` versionado no git (exceção no
  `.gitignore`): é o trabalho do agente, auditável e reaproveitado em reprocessamentos.
- Fluxo: `emmoni ingest <concurso> --step classify` → agente lê as tarefas e grava as respostas →
  `--step classify` de novo → `--step load`.
- O agente **nunca** decide gabarito: o gabarito vem só dos PDFs oficiais de gabarito.

---

## 8. Qualidade e cobertura

- `db/checks/NNN_<nome>.sql`: cada arquivo é uma consulta que retorna as linhas que **violam** uma
  regra. `emmoni check` roda todas; qualquer linha numa questão `published` = falha (código de
  saída ≠ 0).
- Checks mínimos: questão publicada sem gabarito final e não anulada; múltipla escolha com < 4
  alternativas; buraco na numeração de uma prova; `asset:` sem asset; duplicatas publicadas
  não marcadas; questão publicada sem assunto; texto-base sem questões.
- Amostragem por prova (feita pelo agente, decisão 0011): para cada prova nova, `emmoni review sample <concurso>/<prova> --n 10` sorteia
  (de forma determinística) 10 questões sem pendência e gera `data/review/<concurso>/<prova>/amostra.html`
  com cada questão ao lado da página do PDF; a prova só vai para `published` após a conferência
  (`emmoni review approve --by <modelo>`, que registra quem aprovou e a impressão digital do
  conteúdo em `ingest/approvals/<concurso>/<prova>.json`, versionado; decisão 0016). A amostra traz também `amostra.md` e as páginas em PNG (da página onde começa o texto-base ou o comando do grupo até a seguinte à da questão; decisão 0027); o revisor segue
  `ingest/prompts/review-sample@1.md` e grava `verdicts.json` (decisão 0014). Prova reprocessada depois de aprovada é
  reamostrada; se reprovar, volta para `review` até nova aprovação (decisão 0015). Depois de cada
  `load`, a prova só continua publicada se o conteúdo tem a impressão digital aprovada (número,
  hash do enunciado, gabarito, disciplina e pendência de cada questão; assuntos ficam de fora);
  senão volta para `review` até ser reamostrada. `emmoni review restore` republica, num banco novo,
  as provas que conferem.
- Amostragem da classificação: `emmoni review topics --n 50` sorteia 50 questões classificadas e
  gera `data/review/assuntos/amostra.{json,md}`; o agente revisor, em contexto separado do
  `classify`, grava `verdict` e `reviewed_by`, e `--report` mede o acerto (critério do M4,
  decisões 0010 e 0011).
- `emmoni coverage` gera `docs/coverage.md`: questões publicadas por banca × órgão × ano e por
  disciplina, provas de manifestos ainda não ingeridas, propostas pendentes de aprovação e, por
  fonte, a última execução do crawler e os hosts que bloquearam.

---

## 9. Testes e gates

`make` é a interface:

| Alvo | O que faz |
|---|---|
| `make db-up` / `db-down` / `db-reset` | Sobe, para ou recria do zero o Postgres do docker compose. |
| `make prod-image SCOPE=seed\|all` / `prod-audit IMAGE=<tag>` | Gera a imagem de produção da API / audita a imagem (`deploy/audit.py --image`). |
| `make api-up` / `api-down` / `api-smoke` | Sobe (e confere), para ou confere a API HTTP do esquema `api` (seção 6). |
| `make install` | `uv sync --frozen`. |
| `make migrate` | `dbmate up` + atualiza `db/schema.sql`. |
| `make catalog` | Carrega `db/catalog.yaml` e a taxonomia (dados reais, sem o seed). |
| `make seed` | Carrega taxonomia e `db/seed/seed.sql`; copia as imagens do seed para `data/assets/`. |
| `make seed-build` | Regenera `db/seed/seed.sql` a partir de `scripts/build_seed.py`. |
| `make test` | pytest contra `emmoni_test` recriado do zero (migrações + seed). |
| `make migrations-roundtrip` | up → rollback de todas → up em banco vazio; falha se sobrar esquema, privilégio padrão ou configuração do banco. |
| `make lint` | ruff check, ruff format --check, mypy, `build_seed.py --check`. |
| `make check` | `emmoni check`. |
| `make crawl` | `emmoni crawl --all` (operação diária, `docs/operations.md`). |
| `make bench` | Mede as funções do contrato (seção 6). |
| `make gates` | db-up + migrate + lint + migrations-roundtrip + test + check. **Obrigatório passar antes de entregar.** |

**Trava do banco** (decisão 0025): o Postgres é um só por máquina, compartilhado pelos worktrees
(decisão 0019). Os alvos que escrevem nele (`gates`, `test`, `test-db`, `migrate`, `seed`,
`catalog`, `db-reset`, `db-down`, `migrations-roundtrip`, `crawl`, `bench`, `prod-image`) e os
subcomandos `emmoni ingest`, `crawl`, `catalog load`, `taxonomy load`, `review approve` e
`review restore` rodam um por vez: tomam a trava `flock` de `EMMONI_DB_LOCK` (`scripts/db-lock.sh`
no Makefile, `ingest/dblock.py` no `emmoni`). Quem chega com o banco ocupado espera até
`EMMONI_DB_LOCK_WAIT` segundos, dizendo quem segura; não pergunta a ninguém. Outro comando que
escreva no banco fora do make: `scripts/db-lock.sh "<descrição>" <comando>`.

Testes obrigatórios:

- **Esquema**: cada restrição da seção 4.3 tem um teste que tenta violá-la e espera erro.
- **Migrações**: `up` → `down` → `up` em banco vazio funciona.
- **Parsers**: cada parser de banca tem PDFs de `fixtures/` com saída esperada (snapshot JSON).
- **Contrato**: testes para cada função do esquema `api`, rodando como `emmoni_web`, incluindo
  que `emmoni_web` não consegue ler tabelas fora de `api`.
- **Idempotência**: rodar `load` duas vezes produz o mesmo estado; rodar `crawl` duas vezes sobre
  as mesmas páginas não cria propostas novas.
- **Crawlers**: cada crawler tem respostas gravadas da fonte (HTML ou JSON) em
  `fixtures/crawl/<fonte>/` com o resultado esperado (documentos encontrados e manifesto proposto);
  para o Cebraspe, as propostas geradas a partir das fixtures reproduzem os manifestos manuais do M2.
- **Cortesia**: testes do cliente HTTP comprovam que URL proibida no `robots.txt`, domínio fora da
  lista e domínio da denylist **não** geram requisição, e que o limite por host é respeitado.
- Nenhum teste acessa a rede (fixtures e servidor HTTP local).
- Testes da classificação usam arquivos de resposta gravados; nenhum teste depende de LLM.

---

## 10. Marcos

A ordem prioriza destravar o agente de front-end cedo.

| Marco | Entrega | Pronto quando |
|---|---|---|
| **M0 — Fundação** | docker compose, Makefile, dbmate, extensões, papéis, pyproject | `make gates` passa em repositório limpo. |
| **M1 — Esquema e contrato** | Seção 4 completa, esquema `api`, `docs/contract.md` v1.0, `docs/content-format.md`, seed | Agente de front-end consegue desenvolver só com `make db-up migrate seed`. |
| **M2 — Primeira ingestão** | Pipeline completo para **Cebraspe + PF e PRF** (provas dos últimos 5 concursos) | Questões publicadas, `emmoni check` limpo, amostragem aprovada. |
| **M3 — Crawling** | `http.py` com as regras de cortesia, `sources.yaml`, crawler do Cebraspe, propostas e aprovação de manifestos | O crawler descobre sozinho os concursos de PF e PRF já ingeridos no M2 (comparação com os manifestos manuais) e propõe pelo menos um concurso policial novo; testes de cortesia passando. |
| **M4 — Taxonomia e classificação** | Taxonomia das disciplinas mais cobradas em carreiras policiais; classificação por assunto | ≥ 90% das questões publicadas com assunto; amostragem de 50 classificações com ≥ 90% de acerto. |
| **M5 — Mais bancas** | Crawler **e** parser para FGV, Vunesp, IBFC, Instituto AOCP, IDECAN, FCC; sites de órgãos (polícias civis e militares) quando a banca não publica | Cada crawler e parser com fixtures e testes; cobertura em `docs/coverage.md`. |
| **M6 — Escala** | ≥ 100 mil questões publicadas | Metas de desempenho da seção 6 atendidas em `make bench`. |
