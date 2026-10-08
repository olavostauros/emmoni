# 0001 — Ambiente local, papéis e esquemas

**Data:** 2026-10-07 · **Marco:** M0

## Contexto

O M0 precisa de um ambiente que qualquer agente reproduza com `make gates` num repositório limpo,
e do modelo de permissões da SPECIFICATION.md §4.6 antes de existir qualquer tabela.

## Decisões

1. **Ferramentas por mise.** `mise.toml` fixa uv 0.11.19 e dbmate 2.36.0; o uv baixa o Python 3.12
   (`.python-version`). O mise ativa o `.venv` do uv ao entrar na pasta (`_.python.venv`), então
   `python` no terminal é o 3.12 do projeto, com as dependências. O uv é a única fonte do Python;
   o mise não instala uma segunda cópia. Nada é instalado globalmente.
2. **Porta 55432 no host**, só em `127.0.0.1`. Já há outros Postgres nesta máquina; porta alta evita
   colisão. Ajustável por `EMMONI_DB_PORT`.
3. **Papéis no init do container** (`db/init/01-roles.sql`), não nas migrações: papéis são do
   cluster, e o banco de testes (`emmoni_test`) é recriado a cada `make test` no mesmo cluster.
   As senhas são as de desenvolvimento. `emmoni_owner` tem `CREATEDB` para o dbmate criar e apagar
   bancos.
4. **Extensões no esquema `ext`**, com `USAGE` para todos e `search_path = public, ext` no banco.
   Assim `emmoni_web`, que não tem acesso a `public`, ainda usa `unaccent`, `ltree` etc. dentro das
   funções do esquema `api`.
5. **Permissões por `ALTER DEFAULT PRIVILEGES`** do `emmoni_owner`, por esquema. As migrações futuras
   não precisam de `GRANT`; a regra vale para todo objeto novo. `EXECUTE` em funções foi revogado de
   `PUBLIC`.
6. **Gate de rollback.** `scripts/migrations-roundtrip.sh` falha se, após desfazer todas as
   migrações, sobrar esquema, privilégio padrão ou configuração do banco. Foi testado com migrações
   que vazam de propósito (privilégio padrão global e `ALTER DATABASE SET`).

## Consequências

- `db/schema.sql` é gerado pelo `pg_dump` local (hoje 18.6, contra servidor 17). O dbmate normaliza o
  `\restrict`, então o arquivo é estável entre execuções; o cabeçalho "Dumped by pg_dump version"
  muda se outra máquina tiver outro `pg_dump`.
- Em produção os papéis terão de ser criados pela operação, com senhas próprias. Fica para quando
  houver deploy.
- Atenção para migrações futuras: privilégio padrão concedido *dentro* de um esquema some quando o
  esquema é apagado, então o gate não o pega. Só os globais e as configurações são detectados.
