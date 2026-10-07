Você classifica questões de concursos públicos brasileiros (carreiras policiais) em assuntos de uma
taxonomia fechada. Cada tarefa traz a disciplina da questão (`subject_name`), os assuntos permitidos
(`allowed_topics`, identificador → nome), o texto-base quando há (`passage_md`) e o enunciado
(`statement_md`).

Regras:
- Escolha de 1 a 3 assuntos de `allowed_topics`, do mais específico que se aplique. Nunca invente
  identificador nem use assunto de outra disciplina.
- Dê a cada assunto uma confiança entre 0 e 1. Use menos de 0,6 quando nenhum assunto da lista
  descrever bem a questão.
- Se faltar na lista um assunto adequado, sugira um nome em `suggested_topic`; senão, deixe vazio.
- Não resolva a questão e não julgue o gabarito: só classifique o conteúdo cobrado.

Grave as respostas em `classify-answers.json` ao lado deste arquivo, um objeto cuja chave é o
número da questão (como string) e cujo valor segue `answer_format`. Depois rode a etapa `classify`
de novo: ela valida as respostas e grava `topics.json`.
