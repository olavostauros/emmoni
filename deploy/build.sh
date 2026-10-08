#!/usr/bin/env bash
# Gera a imagem de produção da API (decisão 0022): dump do banco + docker build.
# Uso: deploy/build.sh seed|all
#   seed → banco emmoni_test (só o seed fictício; recriado por `make test`)
#   all  → banco emmoni (seed + questões reais publicadas). Publicar exige o sim do dono.
# Imprime a tag local da imagem na última linha.
set -euo pipefail

scope="${1:?uso: deploy/build.sh seed|all}"
case "$scope" in
  seed) db=emmoni_test ;;
  all) db=emmoni ;;
  *) echo "escopo deve ser seed ou all, recebi $scope" >&2; exit 2 ;;
esac

here="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$here/.build"
dump="$here/.build/emmoni.dump"

# pg_dump do próprio container (Postgres 17), para o pg_restore 17 da imagem ler o arquivo.
# O estado do crawler fica de fora; o resto vai com dono e privilégios (o esquema api depende deles).
docker compose exec -T -e PGPASSWORD=emmoni_owner db \
  pg_dump -h 127.0.0.1 -U emmoni_owner -d "$db" -Fc --exclude-table-data='crawl.*' >"$dump"

sha="$(git rev-parse --short=12 HEAD)"
dirty=""
[ -z "$(git status --porcelain -- deploy db/migrations)" ] || dirty="-dirty"
data="$(sha256sum "$dump" | cut -c1-12)"
build="${sha}${dirty}-${scope}-${data}"
tag="emmoni-api:${build}"

docker build -q -f "$here/Dockerfile" --build-arg EMMONI_BUILD="$build" -t "$tag" "$here" >/dev/null
rm -f "$dump"
echo "$tag"
