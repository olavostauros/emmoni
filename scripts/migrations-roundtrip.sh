#!/usr/bin/env bash
# Aplica todas as migrações, desfaz todas e aplica de novo num banco vazio
# (SPECIFICATIONS.md §9). Uso: migrations-roundtrip.sh <url-do-banco-de-testes-como-owner>
set -euo pipefail

url="$1"
dbmate=(${DBMATE:-dbmate} --url "$url" --no-dump-schema)
count=$(find db/migrations -name '*.sql' | wc -l)

"${dbmate[@]}" drop
"${dbmate[@]}" up
for _ in $(seq "$count"); do
  "${dbmate[@]}" rollback
done

# Depois do rollback não pode sobrar nada: esquemas, privilégios padrão, configurações do banco.
leftovers=$(psql "$url" -Atc "
  select concat_ws('; ',
    (select 'esquemas: ' || string_agg(nspname, ', ') from pg_namespace
      where nspname not in ('public', 'information_schema') and nspname not like 'pg\_%'),
    (select 'privilégios padrão: ' || count(*) from pg_default_acl having count(*) > 0),
    (select 'configurações: ' || string_agg(array_to_string(setconfig, ','), ', ')
      from pg_db_role_setting s join pg_database d on d.oid = s.setdatabase
      where d.datname = current_database()))")
if [[ -n "$leftovers" ]]; then
  echo "roundtrip: sobrou após o rollback: $leftovers" >&2
  exit 1
fi

"${dbmate[@]}" up
echo "roundtrip: ok ($count migração(ões))"
