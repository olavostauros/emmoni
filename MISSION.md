# MISSION — emmoni

## O nome

**emmoni** é o codinome do projeto. Faz referência à obsessão dos concurseiros: pessoas que
organizam a vida em torno de passar numa prova de concurso, que resolvem milhares de questões,
que refazem a mesma prova três vezes e que sabem de cor o estilo de cada banca. O projeto existe
para servir essa obsessão — com dados confiáveis, completos e fáceis de encontrar.

## A missão do produto

Construir o melhor **banco de questões de provas de concurso para carreiras policiais** do Brasil,
exposto por um site onde o concurseiro encontra exatamente as questões que precisa estudar:
por banca, órgão, cargo, ano, disciplina e assunto.

Carreiras no escopo (núcleo):

- Polícia Federal (PF) — agente, escrivão, papiloscopista, delegado, perito
- Polícia Rodoviária Federal (PRF)
- Polícias Civis estaduais e do DF (PC/PCDF) — agente/investigador, escrivão, inspetor, delegado, perito
- Polícias Militares e Corpos de Bombeiros Militares (PM/CBM) — soldado, oficial
- Polícia Penal federal e estaduais (antigo agente penitenciário)
- Polícia Legislativa (Câmara, Senado, Assembleias)
- Guardas Municipais (escopo secundário)

## A missão atual do agente: o banco de dados

O trabalho é dividido entre agentes. **Este agente constrói o banco de dados.** O front-end (o site)
será construído por **outro agente** e vai consumir o que for entregue aqui.

Entregas desta fase:

1. **Modelo de dados** — esquema que representa questões, alternativas, gabaritos, provas, concursos,
   bancas, órgãos, cargos, disciplinas e assuntos (taxonomia hierárquica), textos-base compartilhados
   entre questões, imagens e a fonte de cada dado.
2. **Migrações** versionadas e reproduzíveis.
3. **Descoberta automática (crawler)** — percorrer os sites oficiais das bancas e dos órgãos para
   encontrar provas, gabaritos e editais de concursos policiais assim que forem publicados, sem
   depender de alguém procurar os links à mão. O crawler propõe; a ingestão só processa o que foi
   aprovado.
4. **Pipeline de ingestão** — download das provas e gabaritos (PDFs oficiais das bancas e órgãos),
   extração das questões, normalização, classificação por disciplina/assunto, deduplicação e carga.
5. **Qualidade dos dados** — validações automáticas (toda questão tem gabarito, alternativas
   consistentes com o tipo, ano/banca/órgão preenchidos, sem duplicatas) e um relatório de cobertura.
6. **Contrato para o front-end** — documentação do esquema e das consultas que o site vai precisar
   (busca com filtros, busca textual, paginação, contagens por filtro), além de dados de exemplo
   (seed) para o agente de front-end desenvolver sem depender da ingestão completa.

## Critérios de sucesso

- Um concurseiro consegue filtrar "Cebraspe + PF + Língua Portuguesa + 2021" e receber questões
  corretas, completas e com gabarito definitivo.
- Toda questão é rastreável até a prova de origem (documento, página, número da questão).
- Questões anuladas e com gabarito alterado após recurso estão marcadas como tal.
- A ingestão pode ser rodada de novo sem gerar duplicatas (idempotente).
- Uma prova de concurso policial publicada no site de uma banca coberta aparece como manifesto
  pendente de aprovação em até 7 dias, sem intervenção humana.
- O crawler é um bom cidadão da web: respeita `robots.txt`, limites de requisição e bloqueios, e
  nunca acessa sites concorrentes de questões.
- O agente de front-end consegue trabalhar só com o contrato e o seed, sem ler o código da ingestão.

## Fora do escopo desta fase

- Interface do site, design, autenticação de usuários (responsabilidade do agente de front-end).
- Comentários/resoluções de questões escritos por professores.
- Estatísticas de desempenho do usuário (acertos, cadernos, simulados) — virão depois, mas o
  modelo não deve impedir que existam.
