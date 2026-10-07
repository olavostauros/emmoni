# Ponto de entrada do projeto (SPECIFICATIONS.md §9).
# Valores padrão = ambiente de desenvolvimento; um .env sobrescreve.

-include .env

EMMONI_DB_PORT ?= 55432
db_url = postgres://$(1):$(1)@localhost:$(EMMONI_DB_PORT)/$(2)?sslmode=disable

DATABASE_URL            ?= $(call db_url,emmoni_ingest,emmoni)
DATABASE_URL_OWNER      ?= $(call db_url,emmoni_owner,emmoni)
DATABASE_URL_TEST       ?= $(call db_url,emmoni_ingest,emmoni_test)
DATABASE_URL_TEST_OWNER ?= $(call db_url,emmoni_owner,emmoni_test)
DATABASE_URL_TEST_WEB   ?= $(call db_url,emmoni_web,emmoni_test)
BENCH_URL_OWNER  ?= $(call db_url,emmoni_owner,emmoni_bench)
BENCH_URL_INGEST ?= $(call db_url,emmoni_ingest,emmoni_bench)
BENCH_URL_WEB    ?= $(call db_url,emmoni_web,emmoni_bench)

export EMMONI_DB_PORT DATABASE_URL DATABASE_URL_TEST DATABASE_URL_TEST_OWNER DATABASE_URL_TEST_WEB

UV     ?= uv
DBMATE ?= dbmate --wait

.PHONY: help db-up db-down db-reset install migrate catalog seed seed-build test test-db migrations-roundtrip \
        lint format check bench gates

help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

db-up: ## Sobe o Postgres local
	docker compose up -d --wait db

db-down: ## Para o Postgres local (mantém os dados)
	docker compose down

db-reset: ## Apaga o volume do Postgres e sobe de novo, do zero
	docker compose down -v
	$(MAKE) db-up

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

bench: install ## Mede as funções do contrato com 100 mil questões (banco emmoni_bench)
	$(DBMATE) --url "$(BENCH_URL_OWNER)" drop
	$(DBMATE) --url "$(BENCH_URL_OWNER)" --no-dump-schema up
	$(call load_seed,$(BENCH_URL_INGEST))
	$(UV) run python scripts/bench.py "$(BENCH_URL_OWNER)" "$(BENCH_URL_WEB)"

gates: db-up migrate lint migrations-roundtrip test check ## Obrigatório antes de entregar
	@echo "gates: ok"
