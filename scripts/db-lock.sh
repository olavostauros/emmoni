#!/usr/bin/env bash
# Roda um comando segurando a trava do banco (decisão 0025): um comando que escreve no Postgres
# por vez na máquina. Quem chega com o banco ocupado espera, até EMMONI_DB_LOCK_WAIT segundos.
# Uso: scripts/db-lock.sh <descrição> <comando> [args...]
#   EMMONI_DB_LOCK       arquivo da trava (padrão ${XDG_RUNTIME_DIR:-/tmp}/emmoni-db.lock)
#   EMMONI_DB_LOCK_WAIT  espera máxima em segundos (padrão 1800); estourou, sai com 75
#   EMMONI_DB_LOCKED     já definido: um processo pai segura a trava; roda o comando direto
# A mesma trava é tomada pelo comando emmoni (ingest/dblock.py). O arquivo nunca é apagado.
set -uo pipefail

label="${1:?uso: scripts/db-lock.sh <descrição> <comando> [args...]}"
shift
[ $# -gt 0 ] || { echo "db-lock: falta o comando" >&2; exit 2; }

if [ -n "${EMMONI_DB_LOCKED:-}" ]; then
  exec "$@"
fi

lock="${EMMONI_DB_LOCK:-${XDG_RUNTIME_DIR:-/tmp}/emmoni-db.lock}"
wait="${EMMONI_DB_LOCK_WAIT:-1800}"
case "$wait" in
  '' | *[!0-9.]*) echo "db-lock: EMMONI_DB_LOCK_WAIT deve ser um número de segundos: '$wait'" >&2; exit 75 ;;
esac

mkdir -p "$(dirname "$lock")"
exec 9<>"$lock" || { echo "db-lock: não consegui abrir $lock" >&2; exit 75; }
if ! flock -n 9; then
  who="$(head -n1 "$lock" 2>/dev/null)"
  echo "banco ocupado (${who:-quem segura não se identificou}); esperando a trava $lock por até ${wait} s" >&2
  if ! flock -w "$wait" 9; then
    who="$(head -n1 "$lock" 2>/dev/null)"
    echo "db-lock: banco ocupado há mais de ${wait} s (${who:-sem dono}); desisti de esperar a trava $lock" >&2
    exit 75
  fi
fi

# Seguramos a trava: grava quem somos (só informativo) pelo próprio descritor da trava.
truncate -s 0 "$lock"
printf 'pid %s desde %s: %s\n' "$$" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$label" >&9

# O filho não herda o descritor 9: um processo que fique para trás não prende a trava.
EMMONI_DB_LOCKED=1 "$@" 9>&-
status=$?
truncate -s 0 "$lock"
exit "$status"
