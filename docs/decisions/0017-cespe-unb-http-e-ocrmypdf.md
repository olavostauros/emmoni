# 0017 — `cespe.unb.br` por HTTP e `ocrmypdf` no projeto

**Data:** 2026-10-08 · **Marco:** M5

## Contexto

As provas do Cebraspe anteriores a 2014 (DPF 2004–2013, PRF 2013 e outras) estão só no site antigo,
`www.cespe.unb.br`, que responde apenas em HTTP (a porta 443 recusa conexão). O cliente era só HTTPS
(decisão 0003) e a inclusão ficou para o dono do projeto (decisão 0016). O dono autorizou o acesso
por HTTP em 2026-10-08.

O OCR (PDFs escaneados: PCDF 2020 básicos, PM/TO 2020 QPE) dependia de `ocrmypdf` e do idioma `por`
do Tesseract, que faltavam na máquina.

## Decisões

1. **Exceção ao HTTPS por fonte**: campo `allow_http` em `ingest/sources.yaml` (padrão `false`).
   Prefixo `http://` só é aceito em fonte com `allow_http: true` (validado ao carregar), e o cliente
   só pede URL `http://` que caia num prefixo dessa fonte, inclusive em redirecionamentos. O
   `robots.txt` é buscado pelo mesmo esquema da URL. As demais regras de cortesia não mudam.
2. **Fonte `cespe-unb`**: prefixo `http://www.cespe.unb.br/concursos/`, `allow_http: true`,
   `auto_approve: false`. O `robots.txt` do host permite `/concursos/`.
3. **Fonte sem crawler**: `crawler` pode ser `null`. Fonte assim serve só à etapa `fetch`, com
   URLs postas nos manifestos; `emmoni crawl --all` a pula. Um crawler para o site antigo fica para
   quando houver volume que o justifique.
4. **`ocrmypdf` vira dependência Python do projeto** (`uv add ocrmypdf`; não há pacote no
   repositório oficial do Arch). O Tesseract e o idioma `por` continuam pacotes do sistema.

## Consequências

- Conteúdo baixado por HTTP pode ser adulterado no caminho. Mitigação: o hash do PDF fica gravado
  (como para toda fonte) e a amostragem do agente confere o conteúdo contra a página do PDF.
- Destrava os manifestos de concursos policiais antigos do Cebraspe (PF, PRF, PC e PM) sem crawler.
