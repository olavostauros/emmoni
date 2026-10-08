# Imagem de produção da API do emmoni (decisão 0022): Postgres + PostgREST num container imutável.
# Os dados entram no build (deploy/build.sh grava o dump em deploy/.build/); em produção nada
# escreve no banco. O Postgres só escuta no socket Unix; a única porta é a do PostgREST.

FROM postgrest/postgrest:v12.2.3@sha256:729bf65c733b73f5b52777f0e4b853f22ed73aa67a22d38269d289779b0a8401 AS postgrest

FROM postgres:17@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3 AS bake
# PGDATA fora de /var/lib/postgresql/data: o VOLUME da imagem base descartaria o que o RUN grava.
ENV PGDATA=/srv/pgdata
COPY bake.sh /usr/local/bin/emmoni-bake
COPY .build/emmoni.dump /tmp/emmoni.dump
RUN install -d -o postgres -g postgres /srv/pgdata \
 && su postgres -c 'emmoni-bake /tmp/emmoni.dump'

FROM postgres:17@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3
ENV PGDATA=/srv/pgdata
COPY --from=postgrest /bin/postgrest /usr/local/bin/postgrest
COPY --from=bake --chown=postgres:postgres /srv/pgdata /srv/pgdata
COPY entrypoint.sh /usr/local/bin/emmoni-api
ARG EMMONI_BUILD=dev
ENV EMMONI_BUILD=${EMMONI_BUILD} \
    PGRST_DB_URI="postgres://emmoni_web@/emmoni?host=/var/run/postgresql" \
    PGRST_DB_SCHEMAS=api \
    PGRST_DB_ANON_ROLE=emmoni_web \
    PGRST_DB_MAX_ROWS=100 \
    PGRST_DB_POOL=8 \
    PGRST_DB_CHANNEL_ENABLED=false \
    PGRST_DB_AGGREGATES_ENABLED=false \
    PGRST_LOG_LEVEL=error \
    PGRST_SERVER_CORS_ALLOWED_ORIGINS="https://olavostauros.github.io" \
    PORT=8080
USER postgres
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/emmoni-api"]
