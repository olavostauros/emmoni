# 0009 — Múltipla escolha no parser do Cebraspe, vários PDFs de gabarito e justificativas

**Data:** 2026-10-07 · **Marco:** M3 → M4 (ingestão dos 36 manifestos aprovados)

## Contexto

Os 36 manifestos aprovados em 2026-10-07 (decisão 0008) expuseram três limites do pipeline
calibrado no M2 só em provas certo/errado de PF e PRF:

1. Boa parte dos concursos estaduais do Cebraspe (PC/CE, PC/RJ, PC/RO, PC/PB, PC/GO, PC/MA,
   PM/RO, PM/SC, PM/PA, PM/TO, CBM/PA, CBM/RO, CBM/TO, PMDF...) é de **múltipla escolha**:
   título "Questão N", enunciado, alternativas A–E; o gabarito traz letras.
2. Alguns cadernos têm **mais de um PDF de gabarito** (PCDF 2019: um caderno "boneca" com 120
   itens, gabaritos de básicos e de específicos separados; DEPEN 2020: específicos e
   complementares). O manifesto aceitava um PDF por tipo.
3. Cadernos publicados "**com justificativa**" (PCDF 2019/2020, PMDF 2025) trazem, depois de
   cada item, a justificativa oficial do gabarito — às vezes grudada na última linha do item.

## Decisões

1. **Um parser, dois modos.** `ingest/parsers/cebraspe.py` detecta "Questão N" e passa ao modo
   múltipla escolha: a questão vai do título ao próximo título; as alternativas são achadas de
   trás para a frente (sequência A..E ou A..D na margem da coluna); o que sobra depois da última
   alternativa abre o grupo seguinte (texto rotulado "Texto X" vira texto-base; texto sem rótulo
   também, salvo antes da primeira questão — é a capa). Caixa, ícones e filetes do título não
   contam como figura. O gabarito aceita cabeçalho "Questão" e marcas A–E/X.
2. **Lista de URLs por tipo de gabarito** no manifesto (`answer_key_final: [url, url]`). O
   pipeline usa slots (`answer_key_final`, `answer_key_final#2`), faz a união dos itens e grava
   todos os PDFs em `exam_document (exam_id, source_document_id, kind, position)`; as colunas
   `exam.*_document_id` continuam apontando para o primeiro PDF de cada tipo (contrato intacto).
3. **Justificativas são descartadas** na segmentação (`JUSTIFICATIVA`, `ITEM ANULADO`,
   `||JUSTIFICATIVAS||` até o próximo item/título). Guardá-las como comentário oficial fica para
   depois: exige campo próprio e decisão sobre exibição.
4. **`first_number` vem do gabarito** (menor item) na calibração; `subjects_by_range` é lido dos
   itens, prova a prova, por agentes (sem rede), e validado por `tests/test_ingest.py`.
5. **Taxonomia ganha 21 disciplinas** que as provas estaduais cobram (legislação estadual e
   institucional, medicina legal, criminalística, história, geografia, atualidades, redação
   oficial, administração, segurança pública, primeiros socorros, defesa civil, penal militar,
   psicologia, sociologia, filosofia, eleitoral, empresarial, consumidor, noções de direito),
   com assuntos iniciais rasos — M4 refina.

## Consequências

- Todas as provas dos 36 manifestos segmentam com o mesmo número de itens do gabarito, exceto:
  PCDF 2020 básicos e gabarito do PM/TO QPE (PDFs digitalizados, sem texto — OCR pendente);
  CBM/AL 2017 básicos (gabarito oficial com erro de numeração: "1 2 3 4 5 1 2 3 4 5");
  DEPEN 2020 itens 81–90 e PC/PB 2021 cargo 8 item 80 (linha do gabarito ilegível). Esses
  itens ficam em `review` com motivo, não entram publicados.
- O crawler ainda propõe um PDF de gabarito por prova; o segundo é acrescentado à mão.
- O crawler classifica pelo nome do arquivo quando a descrição engana (`GAB_PRELIMINAR_*.PDF`
  descrito como "PROVA OBJETIVA", PC/ES 2022).

## Adendo (mesma data): resultado da carga

- 36 manifestos → 108 provas no banco (contando as 18 de PF/PRF), 6.249 questões reais no
  banco: 824 `published` (as 18 provas do M2), 1.693 `review`, 3.732 `draft` à espera de
  assunto (classificação é o M4). Nenhuma prova nova foi publicada: a amostragem humana
  (`emmoni review sample/approve`) continua obrigatória.
- Não carregadas: DEPEN 2020 agente (gabarito cobre 80 dos 90 itens — itens 81–90 sem gabarito
  oficial encontrado; a regra de prova "gabarito ≠ questões" bloqueia a carga inteira), CBM/AL
  2017 básicos cargo 1 (erro de numeração no gabarito oficial), PCDF 2020 básicos e PM/TO 2020
  QPE (PDFs digitalizados, OCR pendente).
- PM/MA 2017: provas de conhecimentos específicos dos oficiais de saúde (odontologia, medicina,
  veterinária) excluídas do manifesto — fora da carreira policial.
- `subjects_by_range` dos 35 manifestos foi lido questão a questão por sete agentes em paralelo
  (relatórios com as dúvidas em `docs/progress/2026-10-07-ingestao-36-manifestos.md`). A
  taxonomia ganhou mais `teoria-musical`, `engenharia`, `saude-publica`, `execucao-penal` e
  `servico-social` (56 disciplinas).

## Emenda de 2026-10-14 — justificativa pela cor e item que é só número

Contexto: no PCDF 2020 específicos, a justificativa do item 84 começa com "ERRADO." sem o prefixo
"JUSTIFICATIVA -" e não foi cortada; a primeira linha do texto-base seguinte (recuo de 15) grudou
nela, e o texto-base g85 começou no meio da frase (reprovação do minos). No PRF 2018, a primeira
linha do texto-base g27 grudou no item 26, que é só o número (as opções são figuras).

Decisão:

1. A etapa `extract` grava a cor predominante de cada linha (`Line.color`, RGB inteiro, 0 =
   preto; sem letras, a dos caracteres visíveis).
2. A cor das justificativas do caderno é a das linhas que começam com "JUSTIFICATIVA" (azul nos
   PCDF 2019, 2020 e 2026). Havendo essa cor, a justificativa vai até a primeira linha de outra
   cor (o marcador branco "<FimJust>" do PCDF 2026 ainda é dela), e uma linha nessa cor que começa
   com "CERTO"/"ERRADO" abre uma justificativa sem o prefixo. Só pelo texto, sem a cor, nunca. Sem
   cor (OCR, cadernos em preto) vale a regra do recuo de antes.
3. A linha depois de uma justificativa nunca continua o item.
4. Item que é só o número: o parágrafo recuado que vem depois abre o texto seguinte.

Consequências: muda só o PCDF 2020 específicos (q84 e g85; q89, q99 e q111 perdem pedaços de
justificativa em azul; a tabela das contas passa da q111 para o g112) e o PRF 2018 (q26 e g27).
Nas demais 133 provas reprocessadas, nada muda.

## Emenda (2) de 2026-10-14 — justificativa de alternativa sem cabeçalho

Contexto: no PMDF 2025 P2, a justificativa da q79 passou para o topo da página 13, depois das
alternativas C–E, sem o cabeçalho "JUSTIFICATIVAS" ("||A|| - Incorreta. Conforme o artigo 10...").
A múltipla escolha só pulava justificativas a partir do cabeçalho; o bloco ficou depois da
alternativa E e virou o texto-base g80 da q80, que não tem texto-base (questão publicada com
conteúdo errado).

Decisão: na múltipla escolha, a linha na cor das justificativas do caderno (item 2 da emenda
anterior) que começa com o rótulo de alternativa da tabela ("||A|| -", "||E|| –") também abre
uma justificativa, pulada até o próximo título de questão ou de texto-base, como a do cabeçalho.
Só pelo texto, sem a cor, nunca.

Consequências: das 140 provas do staging, muda só o PMDF 2025 P2 (some o g80; a q80 fica sem
texto-base).
