# 0015 — Reamostragem das 18 provas do M2

**Data:** 2026-10-08 · **Marco:** antes do M5

## Contexto

As 18 provas do M2 (PF 2018/2021/2025, PRF 2018/2021) foram reprocessadas na rodada 1 da decisão
0014 depois de aprovadas, e não foram reamostradas. Na reamostragem (4 revisores em contexto
separado, `ingest/prompts/review-sample@1.md`), 15 foram aprovadas e 3 reprovadas, todas do PF 2018:
agente (comando partido na troca de coluna; itens do segundo bloco sem o texto 12A1AAA), escrivão
(comando partido antes do rótulo: "...do texto" | "13A1AAA, julgue") e papiloscopista (itens 6–11
são os períodos consecutivos de um parágrafo; o item 8, "Nessas situações...", depende do 7).

## Decisões

1. **Prova publicada que reprova na reamostragem volta para `review`** (`exam.publish_status`) até
   ser corrigida, reprocessada e aprovada de novo. Não fica no `api` com defeito conhecido.
2. As provas reprovadas são reprocessadas desde o `extract`: o staging delas era da rodada 1, e as
   correções das rodadas 2–5 já resolviam os defeitos do agente.
3. Comando partido na troca de coluna: a continuação pode começar pelo rótulo do texto (dígito),
   não só por minúscula. Basta não começar por maiúscula.
4. **Itens que são períodos consecutivos de um parágrafo** ("Os itens a seguir apresentam, de forma
   consecutiva, os períodos...") → flag `consecutive_items` → `review`. Cada item depende dos
   outros, que não estão no texto-base; montar o parágrafo a partir dos itens fica para depois.
   No corpus atual só ocorre no PF 2018 (papiloscopista).

## Consequências

- As duas correções do parser só mudam a saída das duas provas visadas (comparação da segmentação
  de todas as provas antes e depois da mudança).
- O staging de 17 provas já aprovadas não bate com o parser atual (correções posteriores à
  aprovação). Reprocessá-las exige nova amostragem (decisão 0014, item 3).
