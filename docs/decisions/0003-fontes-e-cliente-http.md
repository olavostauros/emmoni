# 0003 — Primeira fonte permitida (Cebraspe) e cliente HTTP de cortesia

**Data:** 2026-10-07 · **Marco:** M2

## Contexto

O M2 ingere as provas de PF e PRF aplicadas pelo Cebraspe. A etapa `fetch` e a busca manual dos
PDFs para os manifestos já acessam a rede; as regras de cortesia (SPECIFICATION.md §7.1) valem desde
o primeiro acesso, não só a partir do crawler do M3.

## Decisões

1. **`cebraspe` entra em `ingest/sources.yaml`** com os prefixos `https://www.cebraspe.org.br/concursos/`
   e `https://cdn.cebraspe.org.br/`. É o site oficial da banca, que publica provas e gabaritos.
   `auto_approve: false`.
2. **Denylist inicial**: qconcursos.com, tecconcursos.com.br, grancursosonline.com.br, gran.com.br,
   estrategiaconcursos.com.br, estrategia.com, direcaoconcursos.com.br, aprovaconcursos.com.br,
   questoesestrategicas.com.br, pciconcursos.com.br, folhadirigida.com.br — agregadores, cursinhos e
   repositórios de provas não oficiais. Vale para subdomínios.
3. **`ingest/crawlers/http.py` é implementado já no M2** e é o único caminho para a rede, inclusive
   para a etapa `fetch`. Além das regras da §7.1:
   - só `https`;
   - redirecionamentos são seguidos à mão, e o destino passa pelas mesmas checagens;
   - `robots.txt` segue a RFC 9309 (4xx → sem restrições; 5xx/falha → tudo proibido); 403 no
     próprio `robots.txt` também para o host;
   - recusa iniciar sem `EMMONI_CRAWL_CONTACT` real (o valor de exemplo é rejeitado).

## Consequências

- O M3 reaproveita o cliente; falta ao M3 o estado persistente (`crawl.page`, `next_fetch_at`) e o
  crawler em si.
- Os manifestos do M2 são escritos à mão, mas as URLs são descobertas com o mesmo cliente.
