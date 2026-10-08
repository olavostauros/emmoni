# Checks de qualidade

Cada arquivo `NNN_<nome>.sql` é uma consulta que retorna as linhas que **violam** uma regra
(SPECIFICATION.md §8). `emmoni check` roda todos, em transação somente leitura; qualquer linha
retornada faz o comando sair com código ≠ 0.
