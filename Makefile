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

export EMMONI_DB_PORT DATABASE_URL DATABASE_URL_TEST DATABASE_URL_TEST_OWNER DATABASE_URL_TEST_WEB

UV     ?= uv
DBMATE ?= dbmate --wait

.PHONY: help db-up db-down db-reset install migrate seed test test-db migrations-roundtrip \
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

seed: ## Carrega taxonomia e seed (a partir do M1)
	@echo "seed: nada para carregar ainda (chega no M1)"

test-db: ## Recria o banco de testes do zero
	$(DBMATE) --url "$(DATABASE_URL_TEST_OWNER)" drop
	$(DBMATE) --url "$(DATABASE_URL_TEST_OWNER)" --no-dump-schema up

test: install test-db ## Roda os testes contra o banco de testes recriado
	$(UV) run pytest

migrations-roundtrip: ## up → down de tudo → up, no banco de testes
	DBMATE="$(DBMATE)" scripts/migrations-roundtrip.sh "$(DATABASE_URL_TEST_OWNER)"

lint: install ## ruff + mypy
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy

format: install ## Formata o código
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

check: install ## Checks de qualidade dos dados
	$(UV) run emmoni check

bench: ## Mede as funções do contrato (a partir do M1)
	@echo "bench: nada para medir ainda (chega no M1)"

gates: db-up migrate lint migrations-roundtrip test check ## Obrigatório antes de entregar
	@echo "gates: ok"
