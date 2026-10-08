#!/bin/sh
# Entrada da imagem de produção (decisão 0022): sobe o Postgres no socket Unix e entrega o
# processo ao PostgREST na porta $PORT (o Cloud Run define a porta).
set -eu

# O COPY do Dockerfile recria a pasta com 0755; o Postgres exige 0700.
chmod 0700 "$PGDATA"
postgres &
pg=$!

for _ in $(seq 60); do
  pg_isready -q -h /var/run/postgresql && break
  kill -0 "$pg" 2>/dev/null || { echo "postgres saiu antes de ficar pronto" >&2; exit 1; }
  sleep 0.25
done
pg_isready -q -h /var/run/postgresql || { echo "postgres não ficou pronto" >&2; exit 1; }

echo "emmoni-api build ${EMMONI_BUILD}"
export PGRST_SERVER_PORT="$PORT"
exec postgrest
