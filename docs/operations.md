# Operação

## Crawling diário

`emmoni crawl --all` percorre as fontes de `ingest/sources.yaml`, grava o estado em `crawl.*` e
escreve propostas em `ingest/manifests/_pending/`. O comando respeita `next_fetch_at`: rodar mais
de uma vez por dia não aumenta a carga nos sites (páginas que não venceram são relidas do cache em
`data/crawl/`). Rodar uma vez por dia garante o critério do MISSION.md de "até 7 dias".

Pré-requisitos: Postgres no ar (`make db-up`), migrações aplicadas (`make migrate`), catálogo
carregado (`make catalog`) e um `.env` com `DATABASE_URL` e `EMMONI_CRAWL_CONTACT` **real** (o
cliente HTTP recusa o contato de exemplo).

### Timer do systemd (usuário)

`~/.config/systemd/user/emmoni-crawl.service`:

```ini
[Unit]
Description=emmoni: descoberta de provas nas fontes oficiais

[Service]
Type=oneshot
WorkingDirectory=%h/Work/emmoni
ExecStart=/usr/bin/make crawl
```

`~/.config/systemd/user/emmoni-crawl.timer`:

```ini
[Unit]
Description=emmoni: crawl diário

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

```sh
systemctl --user daemon-reload
systemctl --user enable --now emmoni-crawl.timer
journalctl --user -u emmoni-crawl.service   # relatório de cada execução
```

### cron

```
17 6 * * *  cd $HOME/Work/emmoni && make crawl >> data/crawl/crawl.log 2>&1
```

## Depois de cada execução

1. `emmoni manifests pending` lista as propostas; `emmoni manifests show <slug>` mostra uma.
2. Conferir a proposta na página oficial (`source_url`) e o bloco `evidence`.
3. `emmoni manifests approve <slug>` move para `ingest/manifests/`. Ajustar ali `name`,
   `first_number`, `applied_on` e `subjects_by_range` (lendo o caderno) antes de
   `emmoni ingest <slug>`.
4. `emmoni manifests reject <slug> --reason "..."` para o que não interessa; o crawler não volta a
   propor.
5. O relatório lista **órgãos candidatos ao catálogo** (prefixos policiais sem alias em
   `db/catalog.yaml`) e **documentos novos em concursos aprovados** (ex.: gabarito definitivo
   publicado depois do preliminar): o manifesto aprovado é editado à mão.
6. Commitar `ingest/manifests/` (pendentes, aprovados e rejeitados ficam no git).

O código de saída é 1 quando algum host bloqueou (403/captcha); erros pontuais (um concurso com
HTTP 500, por exemplo) ficam só no relatório e são tentados de novo no dia seguinte. Não contorne
bloqueios (AGENTS.md).
