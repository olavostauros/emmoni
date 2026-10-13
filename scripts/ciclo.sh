#!/usr/bin/env bash
# Ciclo autônomo da sessão coordenadora (decisão 0026), rodado pelo emmoni-ciclo.timer.
# Uso: scripts/ciclo.sh   (log em data/ciclo/AAAA-MM-DD-HHMM.log)
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo"

# Um ciclo por vez.
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/emmoni-ciclo.lock"
if ! flock -n 9; then
  echo "ciclo: outro ciclo ainda está rodando"
  exit 0
fi

# Checkout sujo = o dono (ou outra sessão) está trabalhando aqui.
if [ -n "$(git status --porcelain)" ]; then
  echo "ciclo: checkout principal com mudanças sem commit; não rodo"
  git status --short
  exit 0
fi
if [ "$(git branch --show-current)" != main ]; then
  echo "ciclo: checkout fora do main; não rodo"
  exit 0
fi
git pull --ff-only --quiet origin main

mkdir -p data/ciclo
log="data/ciclo/$(date +%F-%H%M).log"

# O projeto padrão do gcloud nesta máquina é o usher-prod.
export CLOUDSDK_CORE_PROJECT=emmoni-prod

status=0
timeout --kill-after=5m "${EMMONI_CICLO_TIMEOUT:-3h}" \
  claude -p "$(cat scripts/ciclo-prompt.md)" --permission-mode auto \
  >"$log" 2>&1 || status=$?

# O que o ciclo deixou sem commit vai para um stash nomeado, para não travar o próximo.
if [ -n "$(git status --porcelain)" ]; then
  git stash push --include-untracked --quiet -m "ciclo $(date +%F-%H%M): sobra"
  echo "ciclo: mudanças sem commit guardadas em git stash" >>"$log"
fi

echo "ciclo: terminou com código $status; log em $log"
exit "$status"
