-- Papéis do banco (SPECIFICATIONS.md §4.6). Papéis são do cluster, não do banco,
-- por isso ficam no init do container e não nas migrações.
-- Senhas valem só para desenvolvimento local.
create role emmoni_owner  login createdb password 'emmoni_owner';
create role emmoni_ingest login password 'emmoni_ingest';
create role emmoni_web    login password 'emmoni_web';
