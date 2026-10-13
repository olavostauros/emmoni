# Ponto de entrada do projeto (SPECIFICATION.md §9).
# Valores padrão = ambiente de desenvolvimento; um .env sobrescreve.

-include .env

EMMONI_DB_PORT ?= 55432
EMMONI_API_PORT ?= 53000
db_url = postgres://$(1):$(1)@localhost:$(EMMONI_DB_PORT)/$(2)?sslmode=disable

DATABASE_URL            ?= $(call db_url,emmoni_ingest,emmoni)
DATABASE_URL_OWNER      ?= $(call db_url,emmoni_owner,emmoni)
DATABASE_URL_TEST       ?= $(call db_url,emmoni_ingest,emmoni_test)
DATABASE_URL_TEST_OWNER ?= $(call db_url,emmoni_owner,emmoni_test)
DATABASE_URL_TEST_WEB   ?= $(call db_url,emmoni_web,emmoni_test)
BENCH_URL_OWNER  ?= $(call db_url,emmoni_owner,emmoni_bench)
BENCH_URL_INGEST ?= $(call db_url,emmoni_ingest,emmoni_bench)
BENCH_URL_WEB    ?= $(call db_url,emmoni_web,emmoni_bench)

export EMMONI_DB_PORT EMMONI_API_PORT DATABASE_URL DATABASE_URL_TEST DATABASE_URL_TEST_OWNER DATABASE_URL_TEST_WEB EMMONI_CRAWL_CONTACT \
       EMMONI_DB_LOCK EMMONI_DB_LOCK_WAIT

UV     ?= uv
DBMATE ?= dbmate --wait

# Trava do banco (decisão 0025): os alvos abaixo escrevem no Postgres (ou o derrubam, ou leem o
# emmoni_test que o `test` recria) e rodam um por vez na máquina. Pedido algum deles, o make de
# fora roda a si mesmo sob scripts/db-lock.sh com EMMONI_DB_LOCKED=1; os makes de dentro (e o
# comando emmoni) veem a variável e não travam de novo. Quem chega com o banco ocupado espera.
DB_TARGETS := gates test test-db migrate seed catalog db-reset db-down migrations-roundtrip \
              crawl bench prod-image
db_goals := $(if $(EMMONI_DB_LOCKED),,$(filter $(DB_TARGETS),$(MAKECMDGOALS)))

ifneq ($(db_goals),)

.PHONY: $(MAKECMDGOALS)
$(firstword $(MAKECMDGOALS)):
	@scripts/db-lock.sh "make $(MAKECMDGOALS)" $(MAKE) --no-print-directory $(MAKECMDGOALS)
$(filter-out $(firstword $(MAKECMDGOALS)),$(MAKECMDGOALS)):
	@:

else

.PHONY: help db-up db-down db-reset api-up api-down api-smoke prod-image prod-audit install migrate catalog seed seed-build test test-db migrations-roundtrip \
        lint format check crawl bench gates

help:
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

db-up: ## Sobe o Postgres local
	docker compose up -d --wait db

db-down: ## Para o Postgres local e a API (mantém os dados)
	docker compose --profile api down

db-reset: ## Apaga o volume do Postgres e sobe de novo, do zero
	docker compose down -v
	$(MAKE) db-up

api-up: db-up ## Sobe a API HTTP do esquema `api` (PostgREST, decisão 0021)
	docker compose --profile api up -d api
	scripts/api-smoke.sh

api-down: ## Para a API HTTP
	docker compose --profile api stop api

api-smoke: ## Confere a API HTTP no ar (catálogo, busca, facetas, questão, erro 400)
	scripts/api-smoke.sh

SCOPE ?= seed
prod-image: ## Imagem de produção da API (SCOPE=seed|all; decisão 0022, docs/DEPLOY.md)
	deploy/build.sh $(SCOPE)

prod-audit: ## Audita uma imagem de produção (IMAGE=<tag>) num container descartável
	python3 -I deploy/audit.py --image $(IMAGE)

install: ## Instala o ambiente Python
	$(UV) sync --frozen

migrate: ## Aplica as migrações e atualiza db/schema.sql
	$(DBMATE) --url "$(DATABASE_URL_OWNER)" up

catalog: install ## Carrega db/catalog.yaml e a taxonomia no banco de desenvolvimento
	$(UV) run emmoni catalog load
	$(UV) run emmoni taxonomy load

# Taxonomia + seed num banco: $(call load_seed,<url como emmoni_ingest>)
define load_seed
	DATABASE_URL="$(1)" $(UV) run emmoni taxonomy load
	psql "$(1)" -v ON_ERROR_STOP=1 -q -f db/seed/seed.sql
endef

seed: install ## Carrega taxonomia e seed no banco de desenvolvimento e copia os assets
	$(call load_seed,$(DATABASE_URL))
	mkdir -p data/assets
	for f in db/seed/assets/*; do cp "$$f" "data/assets/$$(sha256sum "$$f" | cut -d' ' -f1).$${f##*.}"; done

seed-build: install ## Regenera db/seed/seed.sql a partir de scripts/build_seed.py
	$(UV) run python scripts/build_seed.py

test-db: ## Recria o banco de testes do zero
	$(DBMATE) --url "$(DATABASE_URL_TEST_OWNER)" drop
	$(DBMATE) --url "$(DATABASE_URL_TEST_OWNER)" --no-dump-schema up

test: install test-db ## Roda os testes contra o banco de testes recriado (com seed)
	$(call load_seed,$(DATABASE_URL_TEST))
	$(UV) run pytest

migrations-roundtrip: ## up → down de tudo → up, no banco de testes
	DBMATE="$(DBMATE)" scripts/migrations-roundtrip.sh "$(DATABASE_URL_TEST_OWNER)"

lint: install ## ruff + mypy
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy
	$(UV) run python scripts/build_seed.py --check

format: install ## Formata o código
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

check: install ## Checks de qualidade dos dados
	$(UV) run emmoni check

crawl: install ## Descobre provas nas fontes e propõe manifestos (docs/operations.md)
	$(UV) run emmoni crawl --all

bench: install ## Mede as funções do contrato com 100 mil questões (banco emmoni_bench)
	$(DBMATE) --url "$(BENCH_URL_OWNER)" drop
	$(DBMATE) --url "$(BENCH_URL_OWNER)" --no-dump-schema up
	$(call load_seed,$(BENCH_URL_INGEST))
	$(UV) run python scripts/bench.py "$(BENCH_URL_OWNER)" "$(BENCH_URL_WEB)"

gates: db-up migrate lint migrations-roundtrip test check ## Obrigatório antes de entregar
	@echo "gates: ok"

endif
