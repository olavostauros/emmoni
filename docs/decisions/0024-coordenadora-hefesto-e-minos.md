# 0024 — Sessão coordenadora e os subagentes hefesto e minos

**Data:** 2026-10-13 · **Marco:** M5

## Contexto

O papel "Banco de dados" do `AGENTS.md` era feito pela própria sessão principal, que construía e,
desde a decisão 0011, também revisava e aprovava o que tinha produzido. Só a revisão de assuntos
exigia contexto separado. O deploy e a auditoria já tinham identidade própria (atlas e cerberus,
decisão 0022); o banco de dados não tinha.

## Decisão

1. A sessão principal passa a ser a **coordenadora**: orienta, despacha, controla quem usa o banco
   (decisão 0019), fecha o ciclo produção → revisão, registra o progresso e faz commit/PR. Não
   constrói nem aprova.
2. **hefesto** (`.claude/agents/hefesto.md`) é o papel "Banco de dados": esquema, migrações,
   crawler, ingestão, classificação, contrato e seed. Produz e propõe; não aprova.
3. **minos** (`.claude/agents/minos.md`) faz as três revisões da decisão 0011 em contexto próprio,
   sempre separado de quem produziu. Só julga; edita apenas os vereditos de `amostra.json` e aprova
   pelos comandos `emmoni`.
4. O revisor fica registrado com nome e modelo: `minos (claude-opus-5-5)` em `approved_by`,
   `reviewed_by` e na mensagem de commit das aprovações de manifesto.

## Consequências

- A separação da decisão 0011 §3 vale para as três revisões, não só para a de assuntos: quem
  aprova uma prova nunca é a mesma instância que escreveu o parser.
- Subagentes não veem a conversa: a coordenadora escreve pedidos completos, o que custa contexto
  e tempo a cada despacho.
- Registros antigos com `approved_by` só com o modelo continuam válidos; o campo é texto livre.
- O agente de front-end (Plantão) continua fora deste repositório.
