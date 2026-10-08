#!/bin/sh
# Roda no build da imagem (deploy/Dockerfile), como o usuário postgres: cria o cluster, os papéis
# e restaura o dump. Uso: emmoni-bake <arquivo.dump>
set -eu

dump="$1"

initdb --auth-local=peer --auth-host=reject --no-instructions -E UTF8 --locale=C.UTF-8 >/dev/null

cat >>"$PGDATA/postgresql.conf" <<'EOF'
# emmoni (decisão 0022): só socket Unix, dados só de leitura, container descartável.
listen_addresses = ''
max_connections = 20
shared_buffers = 32MB
fsync = off
synchronous_commit = off
full_page_writes = off
autovacuum = off
jit = off
logging_collector = off
log_min_messages = warning
EOF

# Só o emmoni_web entra, e só pelo socket, no banco emmoni; o superusuário só por peer.
cat >"$PGDATA/pg_hba.conf" <<'EOF'
local emmoni emmoni_web trust
local all    postgres   peer
EOF

pg_ctl -w -s -o "-c listen_addresses=''" start

# Papéis sem LOGIN, salvo o do front-end; sem senha (não há rede para usá-la).
psql -X -q -v ON_ERROR_STOP=1 -d postgres <<'EOF'
create role emmoni_owner nologin;
create role emmoni_ingest nologin;
create role emmoni_web login;
create database emmoni owner emmoni_owner;
-- A única configuração do banco (migração foundation); o dump sem --create não a traz.
alter database emmoni set search_path = public, ext;
EOF

# Sem --create: o dump pode vir do emmoni_test (escopo seed); o banco aqui é sempre emmoni.
pg_restore --exit-on-error -d emmoni "$dump"

psql -X -q -v ON_ERROR_STOP=1 -d emmoni <<'EOF'
alter role emmoni_web set default_transaction_read_only = on;
alter role emmoni_web set statement_timeout = '3s';
alter role emmoni_web connection limit 10;
vacuum (analyze, freeze);
EOF

pg_ctl -w -s stop -m fast
