-- migrate:up
-- Polícia Científica (perícia oficial fora da Polícia Civil) como carreira própria (decisão 0016).
alter type career add value if not exists 'policia_cientifica' before 'outra';

-- migrate:down
-- Valor de enum não sai sem recriar o tipo (e as visões do esquema `api` que dependem dele).
-- Nenhuma coluna exige o valor: o down não faz nada.
select 1;
