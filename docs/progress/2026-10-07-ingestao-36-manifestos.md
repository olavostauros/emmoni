# 2026-10-07 — Ingestão dos 36 manifestos aprovados (múltipla escolha, vários gabaritos)

**Marco:** M3 fechado → preparação do M4

## O que foi feito
- Parser do Cebraspe (`ingest/parsers/cebraspe.py`): modo **múltipla escolha** ("Questão N",
  alternativas A–E, textos rotulados como texto-base, capa descartada, caixas/ícones/filetes do
  título não são figura); **justificativas** oficiais descartadas (`JUSTIFICATIVA`, `ITEM
  ANULADO`, `||JUSTIFICATIVAS||`); gabarito aceita cabeçalho "Questão", marcas A–E e `*E`;
  início da prova no título de seção quando falta "PROVA OBJETIVA" (2017); `PROVA OBJETIVA P1`.
- **Vários PDFs por tipo de gabarito** (decisão 0009): `Documents.urls()`, slots no pipeline,
  tabela `exam_document` (migração `20261007210000`), `load` grava todos; proposals/crawl usam
  `urls()`. Crawler classifica `GAB_PRELIMINAR_*`/`GAB_DEFINITIVO_*` pelo nome do arquivo.
- `validate`: alternativa sem texto → review; gabarito sem alternativa correspondente → review e
  marca retida (o banco exige gabarito entre as alternativas). `load`: placeholder explícito para
  alternativa só com figura.
- Calibração dos 36 manifestos: `first_number` pelo gabarito; `subjects_by_range` lido questão a
  questão por sete agentes (sem rede); 5 disciplinas novas além das 21 da decisão 0008.
- Manifestos corrigidos à mão: PCDF 2019 (dois gabaritos), DEPEN 2020 (específicos +
  complementares), PC/ES 2022 (caderno de gerais era o gabarito preliminar), PM/MA 2017 (provas
  de saúde excluídas).
- Carga: 103 provas novas → 5.425 questões novas (`draft`/`review`); total real no banco 6.249.

## Verificação
- `make gates`: **passou** — 306 testes; ruff, mypy e checagem do seed limpos; roundtrip de 10
  migrações; 7 checks sem violação.
- Toda prova carregada tem o mesmo número de questões do gabarito (validate bloqueia o resto).
- **Não verificado:** amostragem humana das 103 provas (nenhuma publicada); leitura lado a lado
  com o PDF das questões de múltipla escolha (só conferi PC/CE 2025, PC/RJ 2021, PCDF 2020 e
  2019 por amostra no terminal); as dúvidas de classificação listadas pelos agentes (abaixo).

## Dúvidas de disciplina registradas pelos agentes (para o M4)
- Blocos regionais ("história e geografia de X", "realidade do DF/RIDE") quebrados questão a
  questão entre `historia`/`geografia`/`atualidades`; talvez mereçam `conhecimentos-regionais`.
- Lei de Execução Penal aparece em `legislacao-penal-especial` fora do DEPEN (PC/MA, PC/PE,
  PC/RO); migrar para `execucao-penal` na reclassificação.
- Crimes do CTB: ora `legislacao-de-transito` (GO/MA/PE), ora `legislacao-penal-especial`
  (PM PA/RO/SC). Padronizar no M4.
- `legislacao-institucional` usado também para DEPEN (regulamento penitenciário federal) e
  `legislacao-estadual` para a Lei 4.878/65 (PCDF): ampliar as descrições.
- Perícias em PC/PB (patologia, psiquiatria e odontologia legal → `medicina-legal`; engenharia
  → `engenharia`) e sensoriamento remoto: disciplinas aproximadas.
- Raciocínio lógico × matemática seguiu o cabeçalho do bloco da prova.

## Problemas encontrados
- Linhas de grade do gabarito ilegíveis em casos isolados (PC/PB 2021 cargo 8 item 80);
  erro oficial de numeração (CBM/AL 2017 básicos cargo 1); DEPEN 2020 itens 81–90 sem gabarito.
- PDFs digitalizados (PCDF 2020 básicos, PM/TO 2020 QPE gabarito): OCR ainda não implementado;
  `tesseract` só tem o idioma `eng` nesta máquina.
- O crawler propõe um gabarito por prova; o segundo entra à mão. Proposta pendente de regra
  antiga não é removida de `_pending/` (ver STATUS).

## Decisões
- [0009](../decisions/0009-multipla-escolha-e-varios-gabaritos.md)

## Próximo passo
- M4: taxonomia e classificação (3.732 questões `draft` só por falta de assunto) e amostragem
  humana das 103 provas (`emmoni review sample`).
