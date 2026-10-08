# 0012 — Pontas soltas do M3: gabarito por bloco, propostas obsoletas e SDS/PE

**Data:** 2026-10-08 · **Marco:** M3 (fechamento das pendências)

## Contexto

O M3 foi dado como pronto em 2026-10-07, mas deixou quatro pendências registradas no
`STATUS.md` e nas decisões 0007–0009:

1. PCDF 2019 tem um caderno único e dois gabaritos definitivos (básicos e específicos). O
   manifesto já aceita uma lista de PDFs por tipo (decisão 0009), mas o crawler propunha só um, e
   o segundo era acrescentado à mão na aprovação.
2. Proposta pendente que deixa de ser proposta (a regra mudou) ficava em `_pending/`:
   `pmto-2020-qps` foi rejeitada à mão em 2026-10-07 só para sair de lá.
3. SDS/PE (2016) ficou fora do catálogo: a secretaria organizou um concurso da PC-PE e outro da
   Polícia Científica.
4. `isGuid: true` na API do Cebraspe não tinha sido visto.

## Decisões

1. **Caderno único, um gabarito por bloco.** Quando o concurso tem **uma** prova cujo rótulo não
   cita bloco nem cargo (`PROVA OBJETIVA`), já casada com o gabarito de um bloco, os gabaritos
   do mesmo tipo de outros blocos (`CONHECIMENTOS BÁSICOS`/`ESPECÍFICOS`) que ficaram sem prova
   entram na mesma prova, básicos antes de específicos (`answer_key_final: [CB1, 001]`). Fora
   desse padrão nada muda: DEPEN 2020 (complementares de nível superior para o cargo 8) continua
   exigindo o acréscimo à mão, porque saber o nível do cargo não está nos dados da API.
2. **O crawler apaga propostas obsoletas.** `_pending/` é do crawler (decisão 0007): ao fim da
   execução, a proposta da mesma fonte cujo concurso foi **visto e lido** e não rendeu proposta
   com aquele slug é apagada (o relatório diz por quê: sem prova com gabarito, fora do escopo ou
   novo slug). Concurso que sumiu da listagem, detalhe com erro ou host bloqueado não apagam nada.
   O git guarda o arquivo; `_rejected/` volta a significar só "alguém decidiu que não".
3. **SDS/PE 2016 entra como alias de evento da PC-PE** (`SDS_PE_16_CIVIL` em `pcpe`). Um alias
   genérico `SDS_PE` traria o concurso da Polícia Científica para a PC-PE, que tem cargos de
   perito no catálogo — atribuição errada. `SDS_PE_16_CIENTIFICA` continua órgão candidato.
4. **`isGuid`**: na execução de 2026-10-08, os 4.229 arquivos em cache têm `isGuid: false`. A URL
   para `true` (decisão 0004) segue sem verificação real; nada muda.

## Consequências

- A proposta de PCDF 2019 gerada das fixtures é igual ao manifesto aprovado nos gabaritos
  (teste `test_single_booklet_gets_one_answer_key_per_block`).
- Execução real de 2026-10-08: proposta nova `pcpe-2016` (delegado, agente, escrivão,
  conhecimentos gerais); nenhuma proposta obsoleta havia em `_pending/`.
- Na proposta `pcpe-2016`, `conhecimentos-gerais` (caderno 258) vai para os três cargos pela
  regra de rótulo genérico (decisão 0008), mas o delegado tem caderno próprio (257): quem aprovar
  tira `delegado` dessa prova.
- DEPEN 2015, como DPF 2014, responde 500 no detalhe; tentado de novo a cada dia.
