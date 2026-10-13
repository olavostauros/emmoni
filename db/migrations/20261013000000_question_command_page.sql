-- migrate:up
-- Página onde começa o comando do grupo (certo/errado do Cebraspe), quando o parser a conhece.
-- Só serve à amostra de revisão: o comando pode estar numa página anterior à do item. Fica fora
-- do esquema `api` e da impressão digital da aprovação. Nula nas questões carregadas antes desta
-- migração, até o próximo `load`.
alter table question
  add column command_page smallint check (command_page > 0);

-- migrate:down
alter table question drop column command_page;
