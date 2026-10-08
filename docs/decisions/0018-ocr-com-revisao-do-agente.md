# 0018 — OCR na etapa `extract`, com revisão linha a linha pelo agente

**Data:** 2026-10-08 · **Marco:** M5

## Contexto

Dois documentos aprovados não tinham texto: o caderno de conhecimentos básicos do PCDF 2020 (texto
em curvas, sem fonte) e o gabarito definitivo do PM/TO 2020 QPE (imagem). O Tesseract `por` lê bem o
corpo do texto, mas erra cerca de uma palavra por parágrafo ("Golás", "artigzo", "CBI1A2-I" no lugar
de "CB1A2-I"), perde negrito e itálico, descarta os números de item em negrito na margem e confunde
letras do gabarito ("C" → "c", "[", "6"). Uma troca A↔D no gabarito passaria por todas as regras.

## Decisões

1. **OCR só onde falta texto.** Se alguma página do PDF não tem texto, o `extract` roda
   `ocrmypdf --skip-text -l por` (páginas com texto ficam intactas) e lê a cópia, guardada em
   `data/ocr/<sha256>.pdf`. Nenhum PDF já aprovado tem página sem texto: nada muda neles.
2. **Limpeza de layout nas páginas digitalizadas**: desenhos do tamanho de uma letra ou dentro de uma
   linha lida não são figuras (cada letra em curvas é um desenho); corpos de fonte perto da mediana
   da página viram a mediana e não há índice/expoente (o OCR oscila de 7,5 a 8,9 pt na mesma
   frase); número miúdo solto (página no rodapé) sai.
3. **Números de item perdidos**: a faixa da margem onde ficam os números já lidos passa por um OCR só
   de dígitos (`--psm 6`, 300 dpi). O número entra na linha da mesma altura que não tem número, e só
   se couber na sequência entre os vizinhos conhecidos.
4. **Revisão obrigatória pelo agente, linha a linha** (não por amostra): o agente compara as linhas
   que viram conteúdo (enunciados, comandos, textos-base, créditos) com a imagem da página e grava as
   correções em `ingest/ocr/<sha256>.yaml` (`page`, `ocr`, `text` em Markdown restrito,
   `proofread_by`). No gabarito, **todas** as marcas são conferidas. A correção cuja linha original
   não aparece mais falha o `extract` (OCR mudou → revisar de novo). Transcrever o gabarito da
   imagem do PDF oficial não é "decidir gabarito" (§7.4): a fonte continua sendo o PDF.
5. **Proveniência**: `extracted_by` ganha `+ocrmypdf+tesseract-por` e, com revisão,
   `+revisado:<modelo>` (ex.: `cebraspe-parser@1+ocrmypdf+tesseract-por+revisado:claude-opus-5-5`).
6. A amostragem por prova (decisão 0005) continua valendo por cima da revisão.

## Consequências

- PCDF 2020 básicos: 50 itens, 40 linhas corrigidas; PM/TO 2020 QPE: gabarito com 60 marcas, 9
  linhas corrigidas.
- O Tesseract com `por` passa a ser exigido para reprocessar esses dois documentos; o teste de ponta
  a ponta do OCR pula quando ele não está instalado.
- Achados de passagem no parser do Cebraspe:
  - "do expediente forense" não é referência a um documento (`IMPLICIT_REF`);
  - a linha que fecha o crédito de um texto ("Internet: <...> (com adaptações).") encerra o
    parágrafo (`CREDIT_END`), tanto em `_paragraphs` quanto em `_choice_paragraphs`. Sem isso, o
    comando da múltipla escolha vinha colado ao crédito (PM/TO 2020 q22 e q23, recusadas na
    amostra). A regra muda 47 questões de 16 provas já aprovadas (só a quebra de parágrafo); elas
    seguem publicadas com o staging antigo até serem reprocessadas e reamostradas.
