# 0008 — Órgãos estaduais e polícia penal no catálogo; apelidos de cargo

**Data:** 2026-10-07 · **Marco:** M3

## Contexto

A decisão 0007 deixou os órgãos policiais que o Cebraspe lista (PC, PM, CBM, DEPEN, SEAP) como
"candidatos": 49 eventos ficavam só no relatório, sem proposta, e o critério do MISSION.md
("manifesto pendente em até 7 dias") não valia para eles. Além disso, o `make crawl` documentado
para o agendamento não exportava `EMMONI_CRAWL_CONTACT`, e um erro de configuração era gravado em
`crawl.page` como se fosse erro da página.

## Decisões

1. **Entram no catálogo** (`db/catalog.yaml`) os órgãos em escopo que o crawler viu: PC de AL, CE,
   ES, GO, MA, MG, PB, PE, RJ, RO e SE; PM de AL, DF, MA, PA, RO, SC e TO; CBM de AL, MA, PA, RO e
   TO; DEPEN (`depen`) e SEAP-MA (`seapma`, polícia penal). Slugs sem hífen, como `pcdf`. Entrar no
   catálogo só faz o crawler **propor**; ingerir continua exigindo parser calibrado e taxonomia.
   SDS/PE (2016) fica de fora: secretaria que organizou concursos de PC e de Polícia Científica.
2. **Cargos têm `aliases`** (`Position.aliases`), como os órgãos: `PRACA`, `PRACAS`, `CADETE`,
   `ASPIRANTE`, `TENENTE`, `CFO`, `OFICIAIS` mapeiam para `soldado`/`oficial` das forças militares.
   Confiança 0,9 (nome completo 1,0; primeira palavra 0,8). Não vão para o banco.
3. **Regras novas do crawler do Cebraspe:** `Caderno de provas` (2016–2017) é prova objetiva;
   `SEM EFEITO` e `CURSO DE INSTRUÇÃO` excluem o documento; prova com rótulo genérico
   (`CONHECIMENTOS GERAIS`, `... PARA TODOS OS CARGOS`) em concurso com vários cargos vale para
   todos os cargos do concurso que estão no catálogo (confiança × 0,7). Rótulo que nomeia um grupo
   (`... DE PERITO CRIMINAL FEDERAL`) não é genérico.
4. **Erro de configuração aborta a execução** antes de qualquer requisição e não grava nada;
   o Makefile exporta `EMMONI_CRAWL_CONTACT` para `make crawl`.

## Consequências

- Execução real de 2026-10-07: 35 propostas pendentes (eram 3), 0 requisições na reexecução.
- Treze concursos novos entraram em `fixtures/crawl/cebraspe/` (reduzidos aos campos lidos); a
  listagem de fixture foi reduzida aos eventos com fixture.
- Na listagem reduzida, eventos sem irmão no mesmo ano (PM_PA_23_CFP sem o CFO) recebem slug
  sem sufixo (`pmpa-2023`), diferente da execução real (`pmpa-2023-cfp`): consequência do
  desempate da decisão 0007, item 8, não um defeito.
