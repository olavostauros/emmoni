# 0014 — Amostragem das 90 provas pelo agente: rodadas, regras do revisor e correções

**Data:** 2026-10-08 · **Marco:** M4 → publicação (antes do M5)

## Contexto

As 90 provas carregadas no M3/M4 estavam sem amostragem e fora do `api`. A revisão é do agente
(decisão 0011). Na primeira rodada, revisores em paralelo acharam defeitos sistemáticos do parser,
e um deles aprovou páginas que não conseguiu ver (limite de imagens).

## Decisões

1. **Instruções do revisor versionadas** em `ingest/prompts/review-sample@1.md`: compara cada
   questão da amostra com as páginas em PNG e o gabarito definitivo; página não vista =
   `unverified` e prova `incomplete` (nunca aprovada); veredito em `verdicts.json` na pasta da
   amostra. Até 5 provas por revisor; scripts auxiliares com nome próprio (houve sobrescrita).
2. **Aprovação só com veredito íntegro:** `exam` igual à prova, os 10 números iguais aos de
   `sample.json`, todos `ok`. O agente que coordena roda `emmoni review approve --by`.
3. **Reprovação → corrigir a causa no parser/extract**, reprocessar só as provas não aprovadas e
   reamostrar. Provas aprovadas não são reprocessadas sem nova amostragem.
4. Correções (além da 0013): rótulos com letra/inglês/fora da margem; títulos de seção, código da
   matriz, "Página: N", "! !", "\t/", "FimDoTexto" fora do fluxo; glifos Symbol (U+F0xx), "þ" e
   controle mapeados ou marcados como fórmula; dígito solto em fonte própria ("P6Q") → fórmula;
   parágrafo após número de linha; tabela de justificativas e justificativa com recuo de parágrafo;
   itens anteriores a `first_number`; comando partido na troca de coluna. **Rede de segurança:**
   remissão a texto-base não encontrado, a linha sem texto-base, figura/tabela/planilha/circuito
   citados e texto-base que é só crédito de imagem → `review` (a questão não é publicada).

## Consequências

- As 90 provas foram aprovadas em 5 rodadas (90 de 90); `api` com 5.000 questões.
- As 18 provas do M2 foram reprocessadas na rodada 1 depois de aprovadas: o conteúdo mudou sem
  nova amostragem. Precisam ser reamostradas (próximo passo no `STATUS.md`).
- Limitações conhecidas que não reprovam: números de linha dos textos-base não são preservados
  ("ℓ" sai como "R"); hífen real em quebra de linha some ("segundotenente"); citação de fonte
  colada ao enunciado; figuras não exportadas (questões ficam em `review`).
