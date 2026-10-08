#!/usr/bin/env bash
# Confere a API HTTP do esquema `api` (PostgREST, decisão 0021): catálogo, busca, facetas,
# questão, limite de linhas e erro de entrada → 400. Uso: api-smoke.sh [url-base]
set -euo pipefail

base="${1:-http://127.0.0.1:${EMMONI_API_PORT:-53000}}"

for _ in $(seq 30); do
  curl -fsS -o /dev/null "$base/" 2>/dev/null && break
  sleep 1
done

# post <rota> <json> → corpo; falha se o status não for 200.
post() { curl -fsS -H 'Content-Type: application/json' -d "$2" "$base$1"; }

check() { # check <descrição> <expressão python sobre `r`> <json>
  python3 -c "import json,sys; r=json.loads(sys.argv[1]); assert $1" "$3" \
    || { echo "falhou: $2" >&2; exit 1; }
  echo "ok: $2"
}

boards=$(curl -fsS "$base/exam_board?select=slug,question_count&order=slug")
check 'len(r) > 0 and "slug" in r[0]' 'catálogo (GET /exam_board)' "$boards"

search=$(post /rpc/search_questions '{"filters": {"exam_board": ["cebraspe"]}, "page_size": 2}')
check 'r["total"] > 0 and len(r["items"]) == 2 and r["next_cursor"]' \
  'busca (POST /rpc/search_questions)' "$search"

cursor=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["next_cursor"])' "$search")
page2=$(post /rpc/search_questions "{\"filters\": {\"exam_board\": [\"cebraspe\"]}, \"page_size\": 2, \"cursor\": \"$cursor\"}")
check 'len(r["items"]) == 2' 'segunda página pelo cursor' "$page2"

facets=$(post /rpc/facet_counts '{"filters": {}}')
check '"exam_board" in r and "topic" in r and r["total"] > 0' 'facetas (POST /rpc/facet_counts)' "$facets"

id=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["items"][0]["id"])' "$search")
question=$(post /rpc/get_question "{\"id\": \"$id\"}")
check "r['id'] == '$id' and 'statement_md' in r" 'questão (POST /rpc/get_question)' "$question"

rows=$(curl -fsS "$base/question?select=id")
check 'len(r) <= 100' 'limite de 100 linhas nas views' "$rows"

status=$(curl -sS -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' \
  -d '{"filters": {"bogus": 1}}' "$base/rpc/search_questions")
[ "$status" = 400 ] || { echo "falhou: filtro inválido devolveu $status, esperado 400" >&2; exit 1; }
echo 'ok: filtro inválido → 400 (SQLSTATE 22023)'

echo "API no ar em $base"
