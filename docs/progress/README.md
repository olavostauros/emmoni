# Progresso

Registro do progresso do agente de banco de dados. Serve para retomar o trabalho entre sessões
e para que outras pessoas e agentes (ex.: o de front-end) saibam em que ponto o projeto está.

## Arquivos

- **`STATUS.md`** — o estado **atual**, sempre sobrescrito. Quem abrir o projeto lê este arquivo
  primeiro.
- **`AAAA-MM-DD-<assunto>.md`** — um registro por sessão de trabalho (ou por entrega relevante).
  Nunca é editado depois; correções entram num registro novo.

## Formato do `STATUS.md`

```markdown
# Status — atualizado em AAAA-MM-DD

**Marco atual:** M? — <nome> (SPECIFICATIONS.md §10)

## Feito neste marco
- ...

## Em andamento
- ...

## Próximos passos
1. ...

## Bloqueios e perguntas em aberto
- ... (o que depende de decisão humana)

## Números
- Questões publicadas: N · em revisão: N · provas ingeridas: N
- Propostas do crawler pendentes: N
- Contrato do front-end: vX.Y
```

## Formato de um registro de sessão

```markdown
# AAAA-MM-DD — <assunto>

**Marco:** M?

## O que foi feito
- ... (com caminhos de arquivos e commits)

## Verificação
- `make gates`: passou / falhou (colar o resumo da saída)
- O que **não** foi verificado, e por quê

## Decisões
- ... (link para docs/decisions/NNNN-*.md quando houver)

## Problemas encontrados
- ...

## Próximo passo
- ...
```

## Regras

- Atualize o `STATUS.md` e crie o registro da sessão **antes de encerrar** qualquer sessão de
  trabalho.
- Seja honesto: gates falhando, etapas puladas e testes não rodados são registrados como tais.
- Datas absolutas (AAAA-MM-DD), nunca "ontem" ou "semana passada".
