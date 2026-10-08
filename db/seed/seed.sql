-- GERADO por scripts/build_seed.py — não edite à mão (make seed-build).
-- Questões fictícias para desenvolvimento do front-end (SPECIFICATION.md §6).

begin;

delete from contest where slug like 'seed-%';

delete from source_document where url like 'https://seed.emmoni.invalid/%';


insert into exam_board (slug, name, short_name) values
  ('cebraspe', 'Centro Brasileiro de Pesquisa em Avaliação e Seleção e de Promoção de Eventos', 'Cebraspe'),
  ('fgv', 'Fundação Getulio Vargas', 'FGV'),
  ('vunesp', 'Fundação para o Vestibular da Universidade Estadual Paulista', 'Vunesp')
on conflict (slug) do update set name = excluded.name, short_name = excluded.short_name;

insert into agency (slug, name, short_name, career, level, state) values
  ('pf', 'Polícia Federal', 'PF', 'pf', 'federal', null),
  ('prf', 'Polícia Rodoviária Federal', 'PRF', 'prf', 'federal', null),
  ('pc-sp', 'Polícia Civil do Estado de São Paulo', 'PC-SP', 'policia_civil', 'estadual', 'SP'),
  ('pc-rj', 'Polícia Civil do Estado do Rio de Janeiro', 'PC-RJ', 'policia_civil', 'estadual', 'RJ'),
  ('pm-sp', 'Polícia Militar do Estado de São Paulo', 'PM-SP', 'policia_militar', 'estadual', 'SP')
on conflict (slug) do update set name = excluded.name, short_name = excluded.short_name;

insert into position (agency_id, slug, name, education_level)
select id, 'agente', 'Agente de Polícia Federal', 'superior' from agency where slug = 'pf'
on conflict (agency_id, slug) do update set name = excluded.name;

insert into position (agency_id, slug, name, education_level)
select id, 'policial-rodoviario-federal', 'Policial Rodoviário Federal', 'superior' from agency where slug = 'prf'
on conflict (agency_id, slug) do update set name = excluded.name;

insert into position (agency_id, slug, name, education_level)
select id, 'investigador', 'Investigador de Polícia', 'superior' from agency where slug = 'pc-sp'
on conflict (agency_id, slug) do update set name = excluded.name;

insert into position (agency_id, slug, name, education_level)
select id, 'inspetor', 'Inspetor de Polícia Civil', 'superior' from agency where slug = 'pc-rj'
on conflict (agency_id, slug) do update set name = excluded.name;

insert into position (agency_id, slug, name, education_level)
select id, 'soldado', 'Soldado PM de 2ª Classe', 'medio' from agency where slug = 'pm-sp'
on conflict (agency_id, slug) do update set name = excluded.name;

insert into asset (sha256, mime_type, width, height, alt_text, storage_key) values
  ('da551c8e5be5f45863f5befa198002e3f2ebb6fb4857df032137892f76d9d258', 'image/svg+xml', 320, 200, 'Planilha com a coluna A (Equipe: Alfa, Bravo, Charlie) e a coluna B (Ocorrências: 10, 20 e 30 nas células B2, B3 e B4); a célula B5 está destacada e vazia.', 'da551c8e5be5f45863f5befa198002e3f2ebb6fb4857df032137892f76d9d258.svg'),
  ('0ff23f212b37f3b0b9239f154213c1e46627dea208056a2631adddf75359b12d', 'image/svg+xml', 400, 90, 'Cinco quadros em sequência com os números 2, 6, 18, 54 e um ponto de interrogação.', '0ff23f212b37f3b0b9239f154213c1e46627dea208056a2631adddf75359b12d.svg')
on conflict (sha256) do nothing;

insert into source_document (kind, url, sha256, page_count, fetched_at) values
  ('exam', 'https://seed.emmoni.invalid/seed-pf-2025/agente.pdf', '69a925fa19f58eb4bf5b0b5608c48acc6b6b15239edeb1edc5e0bb35a9851492', 8, '2026-10-07T00:00:00Z');

insert into contest (slug, agency_id, exam_board_id, year, notice_number, name)
select 'seed-pf-2025', a.id, b.id, 2025, '1/2025 (fictício)', 'PF 2025 — Agente (seed)'
  from agency a, exam_board b where a.slug = 'pf' and b.slug = 'cebraspe';
insert into exam (contest_id, slug, name, applied_on, canonical_booklet, exam_document_id, publish_status)
select c.id, 'agente', 'Agente de Polícia Federal — prova objetiva', '2025-06-15', '1', d.id, 'published'
  from contest c, source_document d where c.slug = 'seed-pf-2025' and d.url = 'https://seed.emmoni.invalid/seed-pf-2025/agente.pdf';
insert into exam_position (exam_id, position_id)
select e.id, p.id from exam e join contest c on c.id = e.contest_id
  join position p on p.agency_id = c.agency_id
 where c.slug = 'seed-pf-2025' and p.slug = 'agente';

insert into source_document (kind, url, sha256, page_count, fetched_at) values
  ('exam', 'https://seed.emmoni.invalid/seed-prf-2024/policial.pdf', '14ca7ce56834027a63704c4296bcbab904ac5b132fbf1ada4f4fb51517f86fcb', 8, '2026-10-07T00:00:00Z');

insert into contest (slug, agency_id, exam_board_id, year, notice_number, name)
select 'seed-prf-2024', a.id, b.id, 2024, '1/2024 (fictício)', 'PRF 2024 — Policial Rodoviário Federal (seed)'
  from agency a, exam_board b where a.slug = 'prf' and b.slug = 'cebraspe';
insert into exam (contest_id, slug, name, applied_on, canonical_booklet, exam_document_id, publish_status)
select c.id, 'policial', 'Policial Rodoviário Federal — prova objetiva', '2024-08-18', '1', d.id, 'published'
  from contest c, source_document d where c.slug = 'seed-prf-2024' and d.url = 'https://seed.emmoni.invalid/seed-prf-2024/policial.pdf';
insert into exam_position (exam_id, position_id)
select e.id, p.id from exam e join contest c on c.id = e.contest_id
  join position p on p.agency_id = c.agency_id
 where c.slug = 'seed-prf-2024' and p.slug = 'policial-rodoviario-federal';

insert into source_document (kind, url, sha256, page_count, fetched_at) values
  ('exam', 'https://seed.emmoni.invalid/seed-pcsp-2025/investigador.pdf', '628d5634ad8aa6e2179bb1e635825699e40d5451467653b8682961beec1c61b9', 8, '2026-10-07T00:00:00Z');

insert into contest (slug, agency_id, exam_board_id, year, notice_number, name)
select 'seed-pcsp-2025', a.id, b.id, 2025, '1/2025 (fictício)', 'PC-SP 2025 — Investigador (seed)'
  from agency a, exam_board b where a.slug = 'pc-sp' and b.slug = 'vunesp';
insert into exam (contest_id, slug, name, applied_on, canonical_booklet, exam_document_id, publish_status)
select c.id, 'investigador', 'Investigador de Polícia — prova objetiva', '2025-03-23', '1', d.id, 'published'
  from contest c, source_document d where c.slug = 'seed-pcsp-2025' and d.url = 'https://seed.emmoni.invalid/seed-pcsp-2025/investigador.pdf';
insert into exam_position (exam_id, position_id)
select e.id, p.id from exam e join contest c on c.id = e.contest_id
  join position p on p.agency_id = c.agency_id
 where c.slug = 'seed-pcsp-2025' and p.slug = 'investigador';

insert into source_document (kind, url, sha256, page_count, fetched_at) values
  ('exam', 'https://seed.emmoni.invalid/seed-pcrj-2024/inspetor.pdf', '1ebe9ec60173d25a9b31d671aa792041e1838e898d8a4932ae68d794638acaed', 8, '2026-10-07T00:00:00Z');

insert into contest (slug, agency_id, exam_board_id, year, notice_number, name)
select 'seed-pcrj-2024', a.id, b.id, 2024, '1/2024 (fictício)', 'PC-RJ 2024 — Inspetor (seed)'
  from agency a, exam_board b where a.slug = 'pc-rj' and b.slug = 'fgv';
insert into exam (contest_id, slug, name, applied_on, canonical_booklet, exam_document_id, publish_status)
select c.id, 'inspetor', 'Inspetor de Polícia Civil — prova objetiva', '2024-11-10', '1', d.id, 'published'
  from contest c, source_document d where c.slug = 'seed-pcrj-2024' and d.url = 'https://seed.emmoni.invalid/seed-pcrj-2024/inspetor.pdf';
insert into exam_position (exam_id, position_id)
select e.id, p.id from exam e join contest c on c.id = e.contest_id
  join position p on p.agency_id = c.agency_id
 where c.slug = 'seed-pcrj-2024' and p.slug = 'inspetor';

insert into source_document (kind, url, sha256, page_count, fetched_at) values
  ('exam', 'https://seed.emmoni.invalid/seed-pmsp-2024/soldado.pdf', '3fa4a3d945a7bff18891d2e58a0e04ee96c7c57206092f92b93cb33b0faf97b5', 8, '2026-10-07T00:00:00Z');

insert into contest (slug, agency_id, exam_board_id, year, notice_number, name)
select 'seed-pmsp-2024', a.id, b.id, 2024, '2/2024 (fictício)', 'PM-SP 2024 — Soldado (seed)'
  from agency a, exam_board b where a.slug = 'pm-sp' and b.slug = 'vunesp';
insert into exam (contest_id, slug, name, applied_on, canonical_booklet, exam_document_id, publish_status)
select c.id, 'soldado', 'Soldado PM de 2ª Classe — prova objetiva', '2024-05-05', '1', d.id, 'published'
  from contest c, source_document d where c.slug = 'seed-pmsp-2024' and d.url = 'https://seed.emmoni.invalid/seed-pmsp-2024/soldado.pdf';
insert into exam_position (exam_id, position_id)
select e.id, p.id from exam e join contest c on c.id = e.contest_id
  join position p on p.agency_id = c.agency_id
 where c.slug = 'seed-pmsp-2024' and p.slug = 'soldado';

insert into passage (id, exam_id, body_md, source_page) values
  ('d784bd34-cd44-5e00-a678-82bdafe7e0da', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 'A investigação criminal moderna depende cada vez mais da análise de dados. Bancos de informações, registros telefônicos e rastros digitais permitem que as equipes reconstruam, com precisão crescente, a dinâmica de um delito. Contudo, a tecnologia não substitui o trabalho de campo: é o investigador quem formula hipóteses, confronta versões e decide quais evidências merecem atenção. Os dados, por si sós, não falam; precisam ser interrogados.', 1),
  ('2c8ec3ce-4bf3-5a3b-a078-e3a8a37bd88b', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 'A tabela a seguir mostra o número de autuações registradas em um posto de fiscalização no primeiro trimestre de um ano.

| Mês | Autuações |
|---|---:|
| Janeiro | 200 |
| Fevereiro | 250 |
| Março | 240 |', 1),
  ('e1e9d266-cbea-50a3-b81f-459885b60a5d', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 'O trabalho policial é frequentemente retratado como uma sucessão de perseguições e confrontos. A rotina real, porém, é feita sobretudo de escuta, registro e paciência. Um boletim de ocorrência bem redigido pode ser mais decisivo para a solução de um caso do que uma diligência espetacular, porque é nele que se preservam os detalhes que a memória, com o tempo, apaga.', 1);

insert into question (id, exam_id, number, type, subject_id, passage_id, statement_md, answer_preliminary, answer_final, answer_status, statement_hash, source_page, extracted_by, publish_status) values
  ('3de39644-b866-5bdd-a7c2-e2f1615abea0', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 1, 'true_false', (select id from subject where slug = 'lingua-portuguesa'), 'd784bd34-cd44-5e00-a678-82bdafe7e0da', 'De acordo com o texto, a tecnologia tornou o trabalho de campo dispensável na investigação criminal.', 'E', 'E', 'valid', '50000c59c4b9a0a563c1d3abb3864cdcca3be4421b3273b9a98aa373d1d825d6', 1, 'seed@1', 'published'),
  ('671a5ac0-11b6-5ecb-b5af-b8dc8f8bbcc1', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 2, 'true_false', (select id from subject where slug = 'lingua-portuguesa'), 'd784bd34-cd44-5e00-a678-82bdafe7e0da', 'No trecho “Os dados, por si sós, não falam”, a palavra “sós” concorda em número com “dados”, razão pela qual está flexionada no plural.', 'C', 'C', 'valid', 'e01489ce70308f3b843e7357fe1e2b158f792e893316b9a294e736f728e27a00', 1, 'seed@1', 'published'),
  ('07812252-f7eb-5162-a4bc-3e8de38cd68b', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 3, 'true_false', (select id from subject where slug = 'lingua-portuguesa'), 'd784bd34-cd44-5e00-a678-82bdafe7e0da', 'Os dois-pontos empregados logo após “trabalho de campo” introduzem uma explicação do que se afirma na oração anterior.', 'C', 'C', 'valid', '168bf0068cb9c0590e202bf71bf3b217fc4641dea8ebd90e9f7d3fe761bc94b4', 1, 'seed@1', 'published'),
  ('f01c1abf-8a9b-5328-886e-085590137100', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 4, 'true_false', (select id from subject where slug = 'lingua-portuguesa'), 'd784bd34-cd44-5e00-a678-82bdafe7e0da', 'A substituição de “Contudo” por **Portanto** preservaria o sentido original do texto.', 'E', 'E', 'valid', '8b88f75658498a3519bfa68c9d4412de86f26513bd492b2fed55574f61d3627e', 1, 'seed@1', 'published'),
  ('a5823f4f-3d35-51d5-922e-e07057942c13', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 5, 'true_false', (select id from subject where slug = 'direito-constitucional'), null, 'Segundo a Constituição Federal de 1988, a Polícia Federal é instituída por lei como órgão permanente, organizado e mantido pela União e estruturado em carreira.', 'C', 'C', 'valid', '6d94106c97a5f6b95ffebff174e51cfaf5720cdc2e80de850a63f3d923d7a6f0', 2, 'seed@1', 'published'),
  ('52603986-2bae-5f57-a13d-dc64b889acce', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 6, 'true_false', (select id from subject where slug = 'direito-constitucional'), null, 'O *habeas data* é o remédio constitucional adequado para assegurar o direito de locomoção de quem sofre ameaça de prisão ilegal.', 'E', 'E', 'valid', '3f32d3ab891479cdaac29681fa51b17c6bd9f40e1c8a4cf923b6047bc9a90a33', 2, 'seed@1', 'published'),
  ('a2c9db11-b15d-537a-a907-619616e80300', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 7, 'true_false', (select id from subject where slug = 'direito-constitucional'), null, 'A casa é asilo inviolável do indivíduo, mas nela se pode penetrar, sem consentimento do morador, em caso de flagrante delito, ainda que durante a noite.', 'C', 'C', 'valid', '9bc2d524aac2bd61eaf22b3337937966421ded672a423df4dedfb0110f5df79b', 2, 'seed@1', 'published'),
  ('b07bee3e-f3eb-5071-8e25-2af52f0571ae', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 8, 'true_false', (select id from subject where slug = 'direito-penal'), null, 'Considera-se praticado o crime no momento da ação ou omissão, ainda que outro seja o momento do resultado.', 'C', 'C', 'valid', '247c220f6d3ab67971697ce03ab17e5d3a9b3c4190228b3b234c2bfd07291a90', 2, 'seed@1', 'published'),
  ('c8380680-da2f-5c52-ae36-86ff5f9c9e97', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 9, 'true_false', (select id from subject where slug = 'direito-penal'), null, 'No crime de furto, a pena é aumentada de um terço se o fato é praticado durante o repouso noturno.', 'C', 'C', 'valid', '257f3abbdaedf5b3b95c21f6b47c89ccd2ddf552333185a5a5d67ec8263955ea', 3, 'seed@1', 'published'),
  ('caba977a-89c6-539b-9d59-fea0219fcf0a', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 10, 'true_false', (select id from subject where slug = 'direito-penal'), null, 'Para a configuração do crime de roubo, é indispensável que a violência ou a grave ameaça seja dirigida contra o próprio titular do patrimônio subtraído.', 'C', 'E', 'changed', '97d1484654ae3f1e7eda919c03da911c0c8f72cd22bc1966046bb70e907520a1', 3, 'seed@1', 'published'),
  ('17c6d808-c105-5cfd-b395-9530df3c71cf', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 11, 'true_false', (select id from subject where slug = 'direito-processual-penal'), null, 'O inquérito policial é procedimento indispensável ao oferecimento da denúncia pelo Ministério Público.', 'E', 'E', 'valid', 'cadf1f5c371f98ade30161a7a1e2fecc86beeedd7c04a0f392376f7156eb1f28', 3, 'seed@1', 'published'),
  ('80154778-7a6f-5c58-9b04-92d5509b050e', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 12, 'true_false', (select id from subject where slug = 'direito-processual-penal'), null, 'A autoridade policial não poderá mandar arquivar autos de inquérito.', 'C', 'C', 'valid', '4a6a2b295bcd444b13248f778877e8177535197e68b09622aee98d0c36839b62', 3, 'seed@1', 'published'),
  ('ec2df32f-9d99-595d-8e61-6f0280edf03e', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 13, 'true_false', (select id from subject where slug = 'informatica'), null, '![Planilha com a coluna A (Equipe: Alfa, Bravo, Charlie) e a coluna B (Ocorrências: 10, 20 e 30 nas células B2, B3 e B4); a célula B5 está destacada e vazia.](asset:da551c8e5be5f45863f5befa198002e3f2ebb6fb4857df032137892f76d9d258)

Considerando a planilha mostrada na figura, a fórmula `=MÉDIA(B2:B4)`, inserida na célula B5, resultará no valor 20.', 'C', 'C', 'valid', 'e3ed24d47cf040fbc662b275cee6129531955fc7a40134863e91f0621026a5b5', 4, 'seed@1', 'published'),
  ('48404960-dd49-503d-a572-0d983e61c87a', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pf-2025'), 14, 'true_false', (select id from subject where slug = 'informatica'), null, '*Phishing* é uma técnica em que o atacante se passa por instituição confiável para induzir a vítima a fornecer dados sensíveis.', 'C', 'C', 'valid', 'fba0e3c1ce4247941ea76da74d5cba1948efc41f000e56f9cd5e44d30b04c243', 4, 'seed@1', 'published'),
  ('9837a453-1b7a-5d25-9e2f-2888e4ca8c6f', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 1, 'true_false', (select id from subject where slug = 'raciocinio-logico'), null, 'A negação da proposição “Todos os condutores foram multados” é “Nenhum condutor foi multado”.', 'E', 'E', 'valid', '5699c9fa7d6124860d682fdcd717c5f0f2800a7b0c28a74a52919b0f65920cac', 1, 'seed@1', 'published'),
  ('f3dcd382-3cda-5c21-beeb-04e7078ba361', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 2, 'true_false', (select id from subject where slug = 'raciocinio-logico'), null, 'A proposição “Se chove, então a pista fica escorregadia” é equivalente a “Se a pista não fica escorregadia, então não chove”.', 'C', 'C', 'valid', '040da0b56b115b22b15c965d6f5db0adf883381a0c96202608faaf3b3bcc5bce', 1, 'seed@1', 'published'),
  ('2bc00fa6-c204-5ddb-896c-c49bf37aa4ee', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 3, 'true_false', (select id from subject where slug = 'matematica'), '2c8ec3ce-4bf3-5a3b-a078-e3a8a37bd88b', 'Com base na tabela, o número de autuações em fevereiro foi 25% superior ao de janeiro.', 'C', 'C', 'valid', 'cc4a17b4c2c74191f81d7b47d3143da9f21093da002a19e2abe9c4c725c2d060', 1, 'seed@1', 'published'),
  ('432cadf9-d52c-53f6-99f2-6d94dff5af39', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 4, 'true_false', (select id from subject where slug = 'matematica'), '2c8ec3ce-4bf3-5a3b-a078-e3a8a37bd88b', 'Com base na tabela, a média mensal de autuações no trimestre foi superior a 230.', 'E', 'E', 'valid', '8cd8b1cd5145512b156da84080cb17cdc3a4cc604e5ec99f21b615c55194e46c', 1, 'seed@1', 'published'),
  ('ee10b29e-bf3b-599e-be9c-1f79d68cb021', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 5, 'true_false', (select id from subject where slug = 'direito-constitucional'), null, 'A Polícia Rodoviária Federal destina-se, na forma da lei, ao patrulhamento ostensivo das rodovias federais.', 'C', 'C', 'valid', '6fc474878e447518136bf6c30d147f329eec11cd8613304f4e37cd6f105376fa', 2, 'seed@1', 'published'),
  ('42f48100-b3bf-5937-93e9-3ee8c5964189', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 6, 'true_false', (select id from subject where slug = 'direito-constitucional'), null, 'É livre a manifestação do pensamento, sendo permitido o anonimato.', 'E', 'E', 'valid', '6667a6db30d82186b796e7f547e337d4d511fcf15c375f9b397cc6efa537d719', 2, 'seed@1', 'published'),
  ('ef3c617b-e5fd-5ec1-9b12-65317047666d', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 7, 'true_false', (select id from subject where slug = 'direito-administrativo'), null, 'A autoexecutoriedade permite à administração pública executar suas próprias decisões sem prévia autorização do Poder Judiciário, nos casos previstos em lei ou em situações de urgência.', 'C', 'C', 'valid', 'bc112b7499f1e5b54924b373b15c1b69768f7e703a92744c9ec1c8c0e787e024', 2, 'seed@1', 'published'),
  ('6bf0aa67-9ff4-5030-b232-3ba9dd83b31b', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 8, 'true_false', (select id from subject where slug = 'direito-administrativo'), null, 'O poder disciplinar é exercido pela administração sobre todos os particulares, independentemente de qualquer vínculo com o Estado.', 'E', 'E', 'valid', '7e6663571394219ad0929ec41575557ecae355751117529d5fad37d70da3ba1d', 2, 'seed@1', 'published'),
  ('b6cc32e3-5dab-55be-adfb-9dbf50439693', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 9, 'true_false', (select id from subject where slug = 'direito-administrativo'), null, 'A presunção de legitimidade dos atos administrativos é absoluta e não admite prova em contrário.', 'E', 'E', 'valid', 'f1ccb5a8585d339cd00e79c89d4e73e2bf68220bc7d78a102a8dcc57f001a855', 3, 'seed@1', 'published'),
  ('7b909ce8-f2aa-5b01-88df-36a75f3372a9', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 10, 'true_false', (select id from subject where slug = 'direito-penal'), null, 'Homicídio culposo é aquele em que o agente quis o resultado ou assumiu o risco de produzi-lo.', 'E', 'E', 'valid', '8c638ed56dd4b2dc86afe25205d0240224f7614482bc683a241bd2f105c6462d', 3, 'seed@1', 'published'),
  ('679324f9-8c3e-5fb4-87a4-5aab65f61304', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 11, 'true_false', (select id from subject where slug = 'lingua-portuguesa'), null, 'Na frase “Haviam muitos veículos na rodovia”, o verbo haver está corretamente flexionado.', 'E', 'E', 'valid', '25026f9c888f15530869c734fc7643e632e7d762f70672c390066bd6848314a8', 3, 'seed@1', 'published'),
  ('10284b72-20bf-5894-a44f-2bd556234c22', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 12, 'true_false', (select id from subject where slug = 'lingua-portuguesa'), null, 'Em “Refiro-me à fiscalização das rodovias”, o emprego do sinal indicativo de crase é obrigatório.', 'C', 'C', 'valid', 'f76258ccedc0cb0f591246ec471234b6393d4d5bf07e23fd38a77e915d58b6f7', 3, 'seed@1', 'published'),
  ('a5373b39-f9d4-520d-bbf3-ec5ad2f23258', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-prf-2024'), 13, 'true_false', (select id from subject where slug = 'informatica'), null, 'Um *firewall* impede, por si só, qualquer tipo de infecção por vírus em um computador.', 'E', null, 'annulled', 'c068241a3e0b2fc87f4502a581ab8d940d709bc856965ec2c1559dcaf5c6584b', 4, 'seed@1', 'published'),
  ('b9a87fee-3ad8-52f7-bfb2-397fedc1b2f4', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 1, 'multiple_choice', (select id from subject where slug = 'lingua-portuguesa'), null, 'Assinale a alternativa em que a concordância verbal está de acordo com a norma-padrão.', 'D', 'D', 'valid', '237902824a8dbb24d768ba8ec2f7be25f2ef74df7c7474524c2e967de576ba28', 1, 'seed@1', 'published'),
  ('b6ef081f-d54b-561e-a582-da1a793ac75b', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 2, 'multiple_choice', (select id from subject where slug = 'lingua-portuguesa'), null, 'Assinale a alternativa em que o sinal indicativo de crase está empregado corretamente.', 'B', 'B', 'valid', '148cdf2289523cd433df3e0dd8f684f88dc8daaf102fef8f52407ebd1fceb45e', 1, 'seed@1', 'published'),
  ('31317796-fc00-5272-8a38-4b9cb3c6aafc', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 3, 'multiple_choice', (select id from subject where slug = 'lingua-portuguesa'), null, 'Assinale a alternativa pontuada de acordo com a norma-padrão.', 'C', 'C', 'valid', '8ad09a3c47202883f1370b67fed23471f7d266999a85da0c939bd847e4a2cdad', 1, 'seed@1', 'published'),
  ('85cbd34d-be3d-55ac-90a5-b8e11695afda', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 4, 'multiple_choice', (select id from subject where slug = 'direito-constitucional'), null, 'De acordo com a Constituição Federal, às polícias civis, dirigidas por delegados de polícia de carreira, incumbem, ressalvada a competência da União,', 'B', 'B', 'valid', '53e3b4ac811d870fd4967076f06f36318a26557bfb4a08b05dd6750e0dbf688e', 1, 'seed@1', 'published'),
  ('0142575a-0fd5-500c-b7a1-6bba87d16dc7', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 5, 'multiple_choice', (select id from subject where slug = 'direito-constitucional'), null, 'O remédio constitucional cabível para proteger direito líquido e certo, não amparado por *habeas corpus* ou *habeas data*, quando o responsável pela ilegalidade for autoridade pública, é o', 'B', 'B', 'valid', '72b15b426a086f3b5e5610a363818630060d7eeb4d0c7b2aeb9bb522240a3772', 2, 'seed@1', 'published'),
  ('2371fddb-e84d-59bd-81c6-e47b7b1d787f', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 6, 'multiple_choice', (select id from subject where slug = 'direito-penal'), null, 'A lei posterior que, de qualquer modo, favorecer o agente', 'C', 'C', 'valid', 'b9531848815c6530de66b1f49957fa1013bf829dc9b9991c3948b35e998d933c', 2, 'seed@1', 'published'),
  ('ea9203e6-932a-5740-a6c4-baa7f7fe430f', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 7, 'multiple_choice', (select id from subject where slug = 'direito-penal'), null, 'Subtrair, para si, coisa alheia móvel, mediante grave ameaça à pessoa, configura o crime de', 'B', 'B', 'valid', '7c33955ae457c642b5630c0d1bd87739626e066266fedb00665a588f992dde09', 2, 'seed@1', 'published'),
  ('5a7e83c3-ffdc-5ee9-9940-aa352fbb0681', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 8, 'multiple_choice', (select id from subject where slug = 'direito-processual-penal'), null, 'Nos termos do Código de Processo Penal, considera-se em flagrante delito quem', 'B', 'B', 'valid', 'c5c592f6efe4d9c2868bd018971a433deeca489469f4741113a7343a929e10c0', 2, 'seed@1', 'published'),
  ('69b5e911-0a27-5078-9348-3f8e115ace61', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 9, 'multiple_choice', (select id from subject where slug = 'direito-processual-penal'), null, 'Sobre o inquérito policial, é correto afirmar que', 'C', 'C', 'valid', '2e3c3fa89179008b7d8ed54a596c27bdf6afa752105a36b8d548ff3fc45487a0', 3, 'seed@1', 'published'),
  ('12c6fc02-f0b5-5ff4-965c-3aaf2925395a', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 10, 'multiple_choice', (select id from subject where slug = 'informatica'), null, 'O protocolo utilizado para a transferência de páginas *web* de forma criptografada é o', 'C', 'C', 'valid', '64e6af9766e35cd9fcfc74ccc387aab35ad83635014793b84b3fdd96817fa998', 3, 'seed@1', 'published'),
  ('3f482796-07bd-5708-b931-0ee4f34a669e', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 11, 'multiple_choice', (select id from subject where slug = 'informatica'), null, 'O tipo de código malicioso que cifra os dados da vítima e exige pagamento para liberá-los é o', 'B', 'B', 'valid', 'c8da551b0e46679b8e3df7d3de932b8b9fbecfff909a1022efbb58f978b905ea', 3, 'seed@1', 'published'),
  ('263d00f2-986d-5e81-9f73-e65ff7560dac', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 12, 'multiple_choice', (select id from subject where slug = 'raciocinio-logico'), null, '![Cinco quadros em sequência com os números 2, 6, 18, 54 e um ponto de interrogação.](asset:0ff23f212b37f3b0b9239f154213c1e46627dea208056a2631adddf75359b12d)

A figura mostra os quatro primeiros termos de uma sequência. Mantido o mesmo padrão, o termo que substitui o ponto de interrogação é', 'C', 'C', 'valid', '3edb2f56841e92a644e238e8b857b539c87bd7a50f397182fe8f8463783ee95b', 3, 'seed@1', 'published'),
  ('d127c588-8ef5-5d87-b59c-b6b51de0e90a', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcsp-2025'), 13, 'multiple_choice', (select id from subject where slug = 'matematica'), null, 'Um lote de 80 inquéritos foi distribuído entre duas delegacias. A primeira recebeu 35% do lote. A segunda recebeu', 'C', 'C', 'valid', '5be378401d4b701b553db82f2009bc5c82ae21f033b93d01015864652a6073e0', 4, 'seed@1', 'published'),
  ('a22d7464-04f9-59c4-8c50-80056eb1f230', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 1, 'multiple_choice', (select id from subject where slug = 'lingua-portuguesa'), 'e1e9d266-cbea-50a3-b81f-459885b60a5d', 'Segundo o texto, a rotina real do trabalho policial caracteriza-se principalmente por', 'B', 'B', 'valid', '5b70126851dbb40803265d7fa7bc43a388c4d018f77e395ba95d2d2f473ad78b', 1, 'seed@1', 'published'),
  ('50f4dc03-323c-5ba9-bc3c-789049abd52c', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 2, 'multiple_choice', (select id from subject where slug = 'lingua-portuguesa'), 'e1e9d266-cbea-50a3-b81f-459885b60a5d', 'No trecho “porque é nele que se preservam os detalhes”, o pronome “nele” retoma', 'C', 'C', 'valid', 'af550a719319757f985eebe7b69bbbf66b2df91edc1e9bd81a69926be59b7492', 1, 'seed@1', 'published'),
  ('9ab71328-e723-51a5-ac3e-50f09cd29892', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 3, 'multiple_choice', (select id from subject where slug = 'lingua-portuguesa'), null, 'A frase em que o termo sublinhado exerce a função de adjunto adverbial de tempo é', 'A', 'A', 'valid', '3baf8df79f62cb3cc774c498d42eac398f2330a4ef009cac5feb95ae39a97207', 1, 'seed@1', 'published'),
  ('b9d58714-43a4-541e-b67a-06cb2a8d5cab', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 4, 'multiple_choice', (select id from subject where slug = 'direito-constitucional'), null, 'Segundo a Constituição Federal, a segurança pública é', 'B', 'B', 'valid', 'eb7a53bfffda9d7256d04a29fc32be3f8f0fffd6d6db9b8db9acae007e38a76f', 1, 'seed@1', 'published'),
  ('f3443914-9b11-5bd7-ba93-5f635899a966', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 5, 'multiple_choice', (select id from subject where slug = 'direito-constitucional'), null, 'Todos podem reunir-se pacificamente, sem armas, em locais abertos ao público, desde que', 'B', 'B', 'valid', '825a3e4bdd14c3d00e99f57f5337bfae1f506aa9fa1e86de5fac9a2446dd3973', 2, 'seed@1', 'published'),
  ('7f31d81d-61c5-5fb8-9b7b-6bbed8aada20', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 6, 'multiple_choice', (select id from subject where slug = 'direito-penal'), null, 'Quando o agente, voluntariamente, desiste de prosseguir na execução do crime, ocorre', 'C', 'C', 'valid', '2981bdcc9fc7a1d60c584b6c6e2910471253e95c31f116133590b31d1764ca53', 2, 'seed@1', 'published'),
  ('8c4cf665-55ab-5a5e-9914-d0ab8ce746d9', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 7, 'multiple_choice', (select id from subject where slug = 'direito-penal'), null, 'O homicídio praticado mediante paga ou promessa de recompensa é classificado como', 'C', 'C', 'valid', '17a4b6d834bf4cdf315b88339f092e95290ddd0ae8d8309fe8819a544d017ac3', 2, 'seed@1', 'published'),
  ('ced692d1-338c-508f-9553-cc69c701b529', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 8, 'multiple_choice', (select id from subject where slug = 'direito-processual-penal'), null, 'A prisão de qualquer pessoa e o local onde se encontre devem ser comunicados imediatamente', 'B', 'B', 'valid', '284c325fa4771f8aed7fca4ad87f75daba6c0ba6bcf987911035bbe0aec9e035', 2, 'seed@1', 'published'),
  ('5eb67fab-a68f-5aa5-a874-8440a1ebaf98', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 9, 'multiple_choice', (select id from subject where slug = 'direito-administrativo'), null, 'O poder conferido à administração para condicionar e restringir o uso e o gozo de bens, atividades e direitos individuais em benefício da coletividade é o poder', 'D', 'D', 'valid', '68a5db01b671cdde842589e6379ca450f05f95fbb8fb97507b3394cb3a535add', 3, 'seed@1', 'published'),
  ('2318c91a-629e-58f5-b937-8ade0b79b75c', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 10, 'multiple_choice', (select id from subject where slug = 'direito-administrativo'), null, 'O atributo do ato administrativo que permite sua imposição a terceiros, independentemente de sua concordância, é a', 'A', 'A', 'valid', 'eedd354a57011577df15a93d05e688881594e58fab3e38f896886f9c1f00ff0b', 3, 'seed@1', 'published'),
  ('813b66da-10bb-5eb0-a150-cd43b4e53f1b', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 11, 'multiple_choice', (select id from subject where slug = 'informatica'), null, 'Em uma planilha eletrônica, a fórmula `=SE(A1>=7;"Aprovado";"Reprovado")` retornará, quando A1 contiver o valor 6,', 'B', 'B', 'valid', '6d01369a43959b19e8428670532e325cbb5a9300c7c7bb48cc582b20ae9b96c2', 3, 'seed@1', 'published'),
  ('79872685-f56a-5638-b886-eb55d8d50e20', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 12, 'multiple_choice', (select id from subject where slug = 'raciocinio-logico'), null, 'Se é verdade que “Nenhum inspetor é negligente” e que “Algum servidor é inspetor”, então é necessariamente verdade que', 'A', 'A', 'valid', '428bb14952bd6b5a861507410dee747ee2c0161374afa1c4f0b409ddb0b96805', 3, 'seed@1', 'published'),
  ('ffd004ca-ad63-553d-a200-6d573aaf0b1b', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pcrj-2024'), 13, 'multiple_choice', (select id from subject where slug = 'legislacao-penal-especial'), null, 'Segundo a Lei nº 11.343/2006, a quem adquire ou traz consigo droga para consumo pessoal **não** é prevista a', 'D', 'D', 'valid', 'e7dbe978c6c1079b548cec56fda6dce02be5ac965f805941d9aca7adadb15808', 4, 'seed@1', 'published'),
  ('3d753b55-74ae-5fb7-86d7-7651cf5aec2d', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pmsp-2024'), 1, 'multiple_choice', (select id from subject where slug = 'lingua-portuguesa'), null, 'Assinale a alternativa em que a palavra está grafada corretamente.', 'C', 'C', 'valid', '8a47cd15c8963110f0e89d077d7e25208aed8de3390dd890e385696c0ea88962', 1, 'seed@1', 'published'),
  ('e7f7aab6-145e-5157-8def-c5abe17aafe8', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pmsp-2024'), 2, 'multiple_choice', (select id from subject where slug = 'lingua-portuguesa'), null, 'Assinale a alternativa correta quanto à concordância nominal.', 'C', 'C', 'valid', '8a0a3eb90fafdd52cd7a4c7739f16946a193dee371c30c387234eb0630905517', 1, 'seed@1', 'published'),
  ('33408219-51fa-5038-b5d7-bb0bbc61e1fd', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pmsp-2024'), 3, 'multiple_choice', (select id from subject where slug = 'direito-constitucional'), null, 'Às polícias militares cabem, segundo a Constituição Federal,', 'A', 'A', 'valid', 'cacd8e33a5e656d1c076e0d0b7c8a83715aba6a2c61c282d1fb86a80ea06e5c8', 1, 'seed@1', 'published'),
  ('e79db1c4-10dc-57e0-996d-373fee4de1a8', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pmsp-2024'), 4, 'multiple_choice', (select id from subject where slug = 'direito-constitucional'), null, 'São direitos sociais, conforme o art. 6º da Constituição Federal, entre outros,', 'A', 'A', 'valid', '843d233bacb8b699874f5c65a17ca5a4216f921cddc4e80753fad6c88d832a45', 1, 'seed@1', 'published'),
  ('b89e8e25-11e5-5fed-b949-45e784ce2c75', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pmsp-2024'), 5, 'multiple_choice', (select id from subject where slug = 'direito-penal'), null, 'Entende-se em legítima defesa quem, usando moderadamente dos meios necessários, repele', 'B', 'B', 'valid', 'f771db9d26964fec9fd0a5ca47354007db053a13a43bd18a69b63373cbc159e5', 2, 'seed@1', 'published'),
  ('2ccdbd7e-fd70-5f17-b271-f9f32d1317d1', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pmsp-2024'), 6, 'multiple_choice', (select id from subject where slug = 'direito-penal'), null, 'O crime de furto distingue-se do roubo porque, no furto,', 'B', 'B', 'valid', '5ea6ca17db8f6818818bdf1403963ec0816436a1281d8c1fa2001f48aaec76e8', 2, 'seed@1', 'published'),
  ('d5652a9a-6b0d-5b6c-9868-de58a3a31df3', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pmsp-2024'), 7, 'multiple_choice', (select id from subject where slug = 'matematica'), null, 'Uma viatura percorre 240 km com 30 litros de combustível. Mantido o mesmo consumo, quantos litros serão necessários para percorrer 400 km?', 'B', 'B', 'valid', '217d8e2adf487e1eee843d51ddb31d6e67750841d46bd53bdd63f33dfeda8959', 2, 'seed@1', 'published'),
  ('b893fc53-9653-586c-8ad4-fadeb55876ef', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pmsp-2024'), 8, 'multiple_choice', (select id from subject where slug = 'matematica'), null, 'Um batalhão tem 120 soldados, dos quais 30% são mulheres. O número de homens é', 'B', 'B', 'valid', '37e2b5ca9e48c4c712f5947cdc513af216ff0cac0c6bb236ea33ea47906657e5', 2, 'seed@1', 'published'),
  ('9e5c546d-68f5-569c-b93a-1673300e2914', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pmsp-2024'), 9, 'multiple_choice', (select id from subject where slug = 'raciocinio-logico'), null, 'Considere a sequência 3, 7, 11, 15, … O 10º termo dessa sequência é', 'A', 'A', 'valid', '9877010e92e851c60dbb0bb1975aaffe68fb575b6ac05b090b4410784d7ac30f', 3, 'seed@1', 'published'),
  ('fb100307-a070-500b-8473-bdc42ce844eb', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pmsp-2024'), 10, 'multiple_choice', (select id from subject where slug = 'informatica'), null, 'No Windows, o atalho de teclado utilizado para copiar um item selecionado é', 'C', 'C', 'valid', 'a99ba4a9ac4d0cb7d890311cdbb002262954c009b783573eca6dec9e014ca553', 3, 'seed@1', 'published'),
  ('4d246322-7c15-5dc9-9452-5a8dd21dc42d', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pmsp-2024'), 11, 'multiple_choice', (select id from subject where slug = 'informatica'), null, 'Para enviar uma mensagem de correio eletrônico a um destinatário sem que os demais destinatários vejam seu endereço, deve-se utilizar o campo', 'C', 'C', 'valid', 'ed749b67ac6ce95f9a4c2f2f626bae70115f54bb0cfbc5c13942f4e6312e2dd9', 3, 'seed@1', 'published'),
  ('365d9de4-95cf-50d9-9268-0aba9fe04645', (select e.id from exam e join contest c on c.id = e.contest_id where c.slug = 'seed-pmsp-2024'), 12, 'multiple_choice', (select id from subject where slug = 'direito-constitucional'), null, 'A Constituição Federal estabelece que ninguém será submetido a tortura nem a tratamento desumano ou degradante. Essa garantia está prevista entre', 'A', 'A', 'valid', 'b3297693ba8d808d0b2631c2e95cfa46e6d1a5d5ea44b8c78ddb609d36591fdb', 3, 'seed@1', 'published');

insert into question_option (question_id, letter, body_md) values
  ('b9a87fee-3ad8-52f7-bfb2-397fedc1b2f4', 'A', 'Fazem dois anos que o inquérito foi instaurado.'),
  ('b9a87fee-3ad8-52f7-bfb2-397fedc1b2f4', 'B', 'Existe, nos autos, provas suficientes para a denúncia.'),
  ('b9a87fee-3ad8-52f7-bfb2-397fedc1b2f4', 'C', 'Houveram diversas diligências no bairro.'),
  ('b9a87fee-3ad8-52f7-bfb2-397fedc1b2f4', 'D', 'Faltam três testemunhas para concluir a oitiva.'),
  ('b9a87fee-3ad8-52f7-bfb2-397fedc1b2f4', 'E', 'Chegou, ao fim da tarde, os peritos do instituto.'),
  ('b6ef081f-d54b-561e-a582-da1a793ac75b', 'A', 'O delegado referiu-se à todos os envolvidos.'),
  ('b6ef081f-d54b-561e-a582-da1a793ac75b', 'B', 'A equipe chegou à delegacia antes do amanhecer.'),
  ('b6ef081f-d54b-561e-a582-da1a793ac75b', 'C', 'Os documentos foram entregues à ele.'),
  ('b6ef081f-d54b-561e-a582-da1a793ac75b', 'D', 'O suspeito começou à confessar.'),
  ('b6ef081f-d54b-561e-a582-da1a793ac75b', 'E', 'Ficou frente à frente com o depoente.'),
  ('31317796-fc00-5272-8a38-4b9cb3c6aafc', 'A', 'Os policiais, chegaram ao local rapidamente.'),
  ('31317796-fc00-5272-8a38-4b9cb3c6aafc', 'B', 'O investigador que trabalha no plantão, redigiu o relatório.'),
  ('31317796-fc00-5272-8a38-4b9cb3c6aafc', 'C', 'Ontem à noite, a equipe cumpriu o mandado de busca.'),
  ('31317796-fc00-5272-8a38-4b9cb3c6aafc', 'D', 'A testemunha disse, que não viu nada.'),
  ('31317796-fc00-5272-8a38-4b9cb3c6aafc', 'E', 'O laudo pericial, foi anexado ao inquérito.'),
  ('85cbd34d-be3d-55ac-90a5-b8e11695afda', 'A', 'o policiamento ostensivo e a preservação da ordem pública.'),
  ('85cbd34d-be3d-55ac-90a5-b8e11695afda', 'B', 'as funções de polícia judiciária e a apuração de infrações penais, exceto as militares.'),
  ('85cbd34d-be3d-55ac-90a5-b8e11695afda', 'C', 'a execução de atividades de defesa civil.'),
  ('85cbd34d-be3d-55ac-90a5-b8e11695afda', 'D', 'o patrulhamento ostensivo das ferrovias federais.'),
  ('85cbd34d-be3d-55ac-90a5-b8e11695afda', 'E', 'a segurança dos estabelecimentos penais.'),
  ('0142575a-0fd5-500c-b7a1-6bba87d16dc7', 'A', 'mandado de injunção.'),
  ('0142575a-0fd5-500c-b7a1-6bba87d16dc7', 'B', 'mandado de segurança.'),
  ('0142575a-0fd5-500c-b7a1-6bba87d16dc7', 'C', 'ação popular.'),
  ('0142575a-0fd5-500c-b7a1-6bba87d16dc7', 'D', '*habeas corpus*.'),
  ('0142575a-0fd5-500c-b7a1-6bba87d16dc7', 'E', 'ação civil pública.'),
  ('2371fddb-e84d-59bd-81c6-e47b7b1d787f', 'A', 'aplica-se somente aos fatos ainda não julgados.'),
  ('2371fddb-e84d-59bd-81c6-e47b7b1d787f', 'B', 'não se aplica aos fatos anteriores, em respeito à coisa julgada.'),
  ('2371fddb-e84d-59bd-81c6-e47b7b1d787f', 'C', 'aplica-se aos fatos anteriores, ainda que decididos por sentença condenatória transitada em julgado.'),
  ('2371fddb-e84d-59bd-81c6-e47b7b1d787f', 'D', 'aplica-se apenas se o condenado ainda não tiver iniciado o cumprimento da pena.'),
  ('2371fddb-e84d-59bd-81c6-e47b7b1d787f', 'E', 'depende de autorização do juiz da execução para ser aplicada.'),
  ('ea9203e6-932a-5740-a6c4-baa7f7fe430f', 'A', 'furto.'),
  ('ea9203e6-932a-5740-a6c4-baa7f7fe430f', 'B', 'roubo.'),
  ('ea9203e6-932a-5740-a6c4-baa7f7fe430f', 'C', 'extorsão.'),
  ('ea9203e6-932a-5740-a6c4-baa7f7fe430f', 'D', 'apropriação indébita.'),
  ('ea9203e6-932a-5740-a6c4-baa7f7fe430f', 'E', 'estelionato.'),
  ('5a7e83c3-ffdc-5ee9-9940-aa352fbb0681', 'A', 'é apontado como autor do crime em denúncia anônima recebida uma semana após o fato.'),
  ('5a7e83c3-ffdc-5ee9-9940-aa352fbb0681', 'B', 'está cometendo a infração penal.'),
  ('5a7e83c3-ffdc-5ee9-9940-aa352fbb0681', 'C', 'confessa espontaneamente o crime dias depois.'),
  ('5a7e83c3-ffdc-5ee9-9940-aa352fbb0681', 'D', 'é reconhecido por fotografia um mês após o fato.'),
  ('5a7e83c3-ffdc-5ee9-9940-aa352fbb0681', 'E', 'possui antecedentes criminais pelo mesmo tipo de delito.'),
  ('69b5e911-0a27-5078-9348-3f8e115ace61', 'A', 'é imprescindível para a propositura da ação penal.'),
  ('69b5e911-0a27-5078-9348-3f8e115ace61', 'B', 'pode ser arquivado pela autoridade policial.'),
  ('69b5e911-0a27-5078-9348-3f8e115ace61', 'C', 'tem natureza inquisitiva e caráter informativo.'),
  ('69b5e911-0a27-5078-9348-3f8e115ace61', 'D', 'está sujeito ao contraditório pleno, sob pena de nulidade.'),
  ('69b5e911-0a27-5078-9348-3f8e115ace61', 'E', 'só pode ser instaurado mediante requisição judicial.'),
  ('12c6fc02-f0b5-5ff4-965c-3aaf2925395a', 'A', 'FTP.'),
  ('12c6fc02-f0b5-5ff4-965c-3aaf2925395a', 'B', 'SMTP.'),
  ('12c6fc02-f0b5-5ff4-965c-3aaf2925395a', 'C', 'HTTPS.'),
  ('12c6fc02-f0b5-5ff4-965c-3aaf2925395a', 'D', 'POP3.'),
  ('12c6fc02-f0b5-5ff4-965c-3aaf2925395a', 'E', 'DNS.'),
  ('3f482796-07bd-5708-b931-0ee4f34a669e', 'A', '*spyware*.'),
  ('3f482796-07bd-5708-b931-0ee4f34a669e', 'B', '*ransomware*.'),
  ('3f482796-07bd-5708-b931-0ee4f34a669e', 'C', '*adware*.'),
  ('3f482796-07bd-5708-b931-0ee4f34a669e', 'D', '*keylogger*.'),
  ('3f482796-07bd-5708-b931-0ee4f34a669e', 'E', '*worm*.'),
  ('263d00f2-986d-5e81-9f73-e65ff7560dac', 'A', '108'),
  ('263d00f2-986d-5e81-9f73-e65ff7560dac', 'B', '148'),
  ('263d00f2-986d-5e81-9f73-e65ff7560dac', 'C', '162'),
  ('263d00f2-986d-5e81-9f73-e65ff7560dac', 'D', '216'),
  ('263d00f2-986d-5e81-9f73-e65ff7560dac', 'E', '72'),
  ('d127c588-8ef5-5d87-b59c-b6b51de0e90a', 'A', '28 inquéritos.'),
  ('d127c588-8ef5-5d87-b59c-b6b51de0e90a', 'B', '45 inquéritos.'),
  ('d127c588-8ef5-5d87-b59c-b6b51de0e90a', 'C', '52 inquéritos.'),
  ('d127c588-8ef5-5d87-b59c-b6b51de0e90a', 'D', '48 inquéritos.'),
  ('d127c588-8ef5-5d87-b59c-b6b51de0e90a', 'E', '35 inquéritos.'),
  ('a22d7464-04f9-59c4-8c50-80056eb1f230', 'A', 'perseguições e confrontos.'),
  ('a22d7464-04f9-59c4-8c50-80056eb1f230', 'B', 'escuta, registro e paciência.'),
  ('a22d7464-04f9-59c4-8c50-80056eb1f230', 'C', 'diligências espetaculares.'),
  ('a22d7464-04f9-59c4-8c50-80056eb1f230', 'D', 'improvisação.'),
  ('a22d7464-04f9-59c4-8c50-80056eb1f230', 'E', 'uso intensivo da força.'),
  ('50f4dc03-323c-5ba9-bc3c-789049abd52c', 'A', 'o trabalho policial.'),
  ('50f4dc03-323c-5ba9-bc3c-789049abd52c', 'B', 'o caso.'),
  ('50f4dc03-323c-5ba9-bc3c-789049abd52c', 'C', 'o boletim de ocorrência.'),
  ('50f4dc03-323c-5ba9-bc3c-789049abd52c', 'D', 'a diligência.'),
  ('50f4dc03-323c-5ba9-bc3c-789049abd52c', 'E', 'o tempo.'),
  ('9ab71328-e723-51a5-ac3e-50f09cd29892', 'A', '<u>Ontem</u>, o inspetor ouviu as testemunhas.'),
  ('9ab71328-e723-51a5-ac3e-50f09cd29892', 'B', 'O inspetor ouviu <u>as testemunhas</u>.'),
  ('9ab71328-e723-51a5-ac3e-50f09cd29892', 'C', '<u>O inspetor</u> ouviu as testemunhas ontem.'),
  ('9ab71328-e723-51a5-ac3e-50f09cd29892', 'D', 'O inspetor <u>ouviu</u> as testemunhas.'),
  ('9ab71328-e723-51a5-ac3e-50f09cd29892', 'E', 'As testemunhas foram ouvidas <u>pelo inspetor</u>.'),
  ('b9d58714-43a4-541e-b67a-06cb2a8d5cab', 'A', 'dever exclusivo da União.'),
  ('b9d58714-43a4-541e-b67a-06cb2a8d5cab', 'B', 'dever do Estado, direito e responsabilidade de todos.'),
  ('b9d58714-43a4-541e-b67a-06cb2a8d5cab', 'C', 'atribuição exclusiva das polícias militares.'),
  ('b9d58714-43a4-541e-b67a-06cb2a8d5cab', 'D', 'responsabilidade apenas dos municípios.'),
  ('b9d58714-43a4-541e-b67a-06cb2a8d5cab', 'E', 'dever do Estado, sem participação da sociedade.'),
  ('f3443914-9b11-5bd7-ba93-5f635899a966', 'A', 'haja autorização prévia da autoridade policial.'),
  ('f3443914-9b11-5bd7-ba93-5f635899a966', 'B', 'não frustrem outra reunião anteriormente convocada para o mesmo local, sendo apenas exigido prévio aviso à autoridade competente.'),
  ('f3443914-9b11-5bd7-ba93-5f635899a966', 'C', 'a reunião ocorra somente em dias úteis.'),
  ('f3443914-9b11-5bd7-ba93-5f635899a966', 'D', 'o número de participantes não ultrapasse cem pessoas.'),
  ('f3443914-9b11-5bd7-ba93-5f635899a966', 'E', 'a reunião seja comunicada ao Poder Judiciário com trinta dias de antecedência.'),
  ('7f31d81d-61c5-5fb8-9b7b-6bbed8aada20', 'A', 'arrependimento posterior.'),
  ('7f31d81d-61c5-5fb8-9b7b-6bbed8aada20', 'B', 'crime impossível.'),
  ('7f31d81d-61c5-5fb8-9b7b-6bbed8aada20', 'C', 'desistência voluntária.'),
  ('7f31d81d-61c5-5fb8-9b7b-6bbed8aada20', 'D', 'tentativa perfeita.'),
  ('7f31d81d-61c5-5fb8-9b7b-6bbed8aada20', 'E', 'arrependimento eficaz.'),
  ('8c4cf665-55ab-5a5e-9914-d0ab8ce746d9', 'A', 'privilegiado.'),
  ('8c4cf665-55ab-5a5e-9914-d0ab8ce746d9', 'B', 'culposo.'),
  ('8c4cf665-55ab-5a5e-9914-d0ab8ce746d9', 'C', 'qualificado.'),
  ('8c4cf665-55ab-5a5e-9914-d0ab8ce746d9', 'D', 'simples.'),
  ('8c4cf665-55ab-5a5e-9914-d0ab8ce746d9', 'E', 'preterdoloso.'),
  ('ced692d1-338c-508f-9553-cc69c701b529', 'A', 'apenas à família do preso.'),
  ('ced692d1-338c-508f-9553-cc69c701b529', 'B', 'ao juiz competente, ao Ministério Público e à família do preso ou à pessoa por ele indicada.'),
  ('ced692d1-338c-508f-9553-cc69c701b529', 'C', 'somente ao Ministério Público.'),
  ('ced692d1-338c-508f-9553-cc69c701b529', 'D', 'ao juiz competente, no prazo de cinco dias.'),
  ('ced692d1-338c-508f-9553-cc69c701b529', 'E', 'exclusivamente à Defensoria Pública.'),
  ('5eb67fab-a68f-5aa5-a874-8440a1ebaf98', 'A', 'hierárquico.'),
  ('5eb67fab-a68f-5aa5-a874-8440a1ebaf98', 'B', 'disciplinar.'),
  ('5eb67fab-a68f-5aa5-a874-8440a1ebaf98', 'C', 'regulamentar.'),
  ('5eb67fab-a68f-5aa5-a874-8440a1ebaf98', 'D', 'de polícia.'),
  ('5eb67fab-a68f-5aa5-a874-8440a1ebaf98', 'E', 'normativo.'),
  ('2318c91a-629e-58f5-b937-8ade0b79b75c', 'A', 'imperatividade.'),
  ('2318c91a-629e-58f5-b937-8ade0b79b75c', 'B', 'tipicidade.'),
  ('2318c91a-629e-58f5-b937-8ade0b79b75c', 'C', 'motivação.'),
  ('2318c91a-629e-58f5-b937-8ade0b79b75c', 'D', 'publicidade.'),
  ('2318c91a-629e-58f5-b937-8ade0b79b75c', 'E', 'finalidade.'),
  ('813b66da-10bb-5eb0-a150-cd43b4e53f1b', 'A', 'Aprovado.'),
  ('813b66da-10bb-5eb0-a150-cd43b4e53f1b', 'B', 'Reprovado.'),
  ('813b66da-10bb-5eb0-a150-cd43b4e53f1b', 'C', '6.'),
  ('813b66da-10bb-5eb0-a150-cd43b4e53f1b', 'D', '7.'),
  ('813b66da-10bb-5eb0-a150-cd43b4e53f1b', 'E', 'VERDADEIRO.'),
  ('79872685-f56a-5638-b886-eb55d8d50e20', 'A', 'algum servidor não é negligente.'),
  ('79872685-f56a-5638-b886-eb55d8d50e20', 'B', 'todo servidor é inspetor.'),
  ('79872685-f56a-5638-b886-eb55d8d50e20', 'C', 'nenhum servidor é negligente.'),
  ('79872685-f56a-5638-b886-eb55d8d50e20', 'D', 'algum negligente é inspetor.'),
  ('79872685-f56a-5638-b886-eb55d8d50e20', 'E', 'todo negligente é servidor.'),
  ('ffd004ca-ad63-553d-a200-6d573aaf0b1b', 'A', 'advertência sobre os efeitos das drogas.'),
  ('ffd004ca-ad63-553d-a200-6d573aaf0b1b', 'B', 'prestação de serviços à comunidade.'),
  ('ffd004ca-ad63-553d-a200-6d573aaf0b1b', 'C', 'medida educativa de comparecimento a programa ou curso educativo.'),
  ('ffd004ca-ad63-553d-a200-6d573aaf0b1b', 'D', 'pena privativa de liberdade.'),
  ('ffd004ca-ad63-553d-a200-6d573aaf0b1b', 'E', 'aplicação isolada ou cumulativa das medidas previstas.'),
  ('3d753b55-74ae-5fb7-86d7-7651cf5aec2d', 'A', 'excessão'),
  ('3d753b55-74ae-5fb7-86d7-7651cf5aec2d', 'B', 'previlégio'),
  ('3d753b55-74ae-5fb7-86d7-7651cf5aec2d', 'C', 'exceção'),
  ('3d753b55-74ae-5fb7-86d7-7651cf5aec2d', 'D', 'beneficiente'),
  ('e7f7aab6-145e-5157-8def-c5abe17aafe8', 'A', 'Seguem anexo os documentos.'),
  ('e7f7aab6-145e-5157-8def-c5abe17aafe8', 'B', 'É proibida entrada de pessoas estranhas.'),
  ('e7f7aab6-145e-5157-8def-c5abe17aafe8', 'C', 'Ela mesma redigiu o relatório.'),
  ('e7f7aab6-145e-5157-8def-c5abe17aafe8', 'D', 'Ficaram bastantes satisfeitos os comandantes.'),
  ('33408219-51fa-5038-b5d7-bb0bbc61e1fd', 'A', 'a polícia ostensiva e a preservação da ordem pública.'),
  ('33408219-51fa-5038-b5d7-bb0bbc61e1fd', 'B', 'as funções de polícia judiciária da União.'),
  ('33408219-51fa-5038-b5d7-bb0bbc61e1fd', 'C', 'a apuração das infrações penais militares federais.'),
  ('33408219-51fa-5038-b5d7-bb0bbc61e1fd', 'D', 'o patrulhamento ostensivo das rodovias federais.'),
  ('e79db1c4-10dc-57e0-996d-373fee4de1a8', 'A', 'a educação, a saúde e a segurança.'),
  ('e79db1c4-10dc-57e0-996d-373fee4de1a8', 'B', 'o *habeas corpus* e o mandado de segurança.'),
  ('e79db1c4-10dc-57e0-996d-373fee4de1a8', 'C', 'a nacionalidade e a cidadania.'),
  ('e79db1c4-10dc-57e0-996d-373fee4de1a8', 'D', 'o voto e a elegibilidade.'),
  ('b89e8e25-11e5-5fed-b949-45e784ce2c75', 'A', 'agressão futura e incerta.'),
  ('b89e8e25-11e5-5fed-b949-45e784ce2c75', 'B', 'injusta agressão, atual ou iminente, a direito seu ou de outrem.'),
  ('b89e8e25-11e5-5fed-b949-45e784ce2c75', 'C', 'qualquer agressão, ainda que justa.'),
  ('b89e8e25-11e5-5fed-b949-45e784ce2c75', 'D', 'perigo atual que não provocou por sua vontade.'),
  ('2ccdbd7e-fd70-5f17-b271-f9f32d1317d1', 'A', 'há emprego de violência contra a pessoa.'),
  ('2ccdbd7e-fd70-5f17-b271-f9f32d1317d1', 'B', 'não há violência ou grave ameaça contra a pessoa.'),
  ('2ccdbd7e-fd70-5f17-b271-f9f32d1317d1', 'C', 'a coisa subtraída é imóvel.'),
  ('2ccdbd7e-fd70-5f17-b271-f9f32d1317d1', 'D', 'a vítima entrega a coisa voluntariamente.'),
  ('d5652a9a-6b0d-5b6c-9868-de58a3a31df3', 'A', '45'),
  ('d5652a9a-6b0d-5b6c-9868-de58a3a31df3', 'B', '50'),
  ('d5652a9a-6b0d-5b6c-9868-de58a3a31df3', 'C', '55'),
  ('d5652a9a-6b0d-5b6c-9868-de58a3a31df3', 'D', '60'),
  ('b893fc53-9653-586c-8ad4-fadeb55876ef', 'A', '36'),
  ('b893fc53-9653-586c-8ad4-fadeb55876ef', 'B', '84'),
  ('b893fc53-9653-586c-8ad4-fadeb55876ef', 'C', '90'),
  ('b893fc53-9653-586c-8ad4-fadeb55876ef', 'D', '80'),
  ('9e5c546d-68f5-569c-b93a-1673300e2914', 'A', '39'),
  ('9e5c546d-68f5-569c-b93a-1673300e2914', 'B', '43'),
  ('9e5c546d-68f5-569c-b93a-1673300e2914', 'C', '40'),
  ('9e5c546d-68f5-569c-b93a-1673300e2914', 'D', '41'),
  ('fb100307-a070-500b-8473-bdc42ce844eb', 'A', 'Ctrl+V'),
  ('fb100307-a070-500b-8473-bdc42ce844eb', 'B', 'Ctrl+X'),
  ('fb100307-a070-500b-8473-bdc42ce844eb', 'C', 'Ctrl+C'),
  ('fb100307-a070-500b-8473-bdc42ce844eb', 'D', 'Ctrl+Z'),
  ('4d246322-7c15-5dc9-9452-5a8dd21dc42d', 'A', 'Para'),
  ('4d246322-7c15-5dc9-9452-5a8dd21dc42d', 'B', 'Cc'),
  ('4d246322-7c15-5dc9-9452-5a8dd21dc42d', 'C', 'Cco'),
  ('4d246322-7c15-5dc9-9452-5a8dd21dc42d', 'D', 'Assunto'),
  ('365d9de4-95cf-50d9-9268-0aba9fe04645', 'A', 'os direitos e garantias fundamentais.'),
  ('365d9de4-95cf-50d9-9268-0aba9fe04645', 'B', 'as normas de organização dos Poderes.'),
  ('365d9de4-95cf-50d9-9268-0aba9fe04645', 'C', 'as disposições sobre o sistema tributário.'),
  ('365d9de4-95cf-50d9-9268-0aba9fe04645', 'D', 'as regras da ordem econômica.');

insert into question_topic (question_id, topic_id, origin, confidence) values
  ('3de39644-b866-5bdd-a7c2-e2f1615abea0', (select id from topic where path = 'lingua_portuguesa.interpretacao_de_texto'), 'manual', null),
  ('671a5ac0-11b6-5ecb-b5af-b8dc8f8bbcc1', (select id from topic where path = 'lingua_portuguesa.concordancia.nominal'), 'manual', null),
  ('07812252-f7eb-5162-a4bc-3e8de38cd68b', (select id from topic where path = 'lingua_portuguesa.pontuacao'), 'manual', null),
  ('f01c1abf-8a9b-5328-886e-085590137100', (select id from topic where path = 'lingua_portuguesa.coesao_e_coerencia.conectivos'), 'manual', null),
  ('a5823f4f-3d35-51d5-922e-e07057942c13', (select id from topic where path = 'direito_constitucional.seguranca_publica.orgaos_policiais'), 'manual', null),
  ('52603986-2bae-5f57-a13d-dc64b889acce', (select id from topic where path = 'direito_constitucional.direitos_e_garantias_fundamentais.remedios_constitucionais'), 'manual', null),
  ('a2c9db11-b15d-537a-a907-619616e80300', (select id from topic where path = 'direito_constitucional.direitos_e_garantias_fundamentais.direitos_individuais'), 'manual', null),
  ('b07bee3e-f3eb-5071-8e25-2af52f0571ae', (select id from topic where path = 'direito_penal.aplicacao_da_lei_penal.tempo_do_crime'), 'manual', null),
  ('c8380680-da2f-5c52-ae36-86ff5f9c9e97', (select id from topic where path = 'direito_penal.crimes_contra_o_patrimonio.furto'), 'manual', null),
  ('caba977a-89c6-539b-9d59-fea0219fcf0a', (select id from topic where path = 'direito_penal.crimes_contra_o_patrimonio.roubo'), 'manual', null),
  ('17c6d808-c105-5cfd-b395-9530df3c71cf', (select id from topic where path = 'direito_processual_penal.inquerito_policial'), 'manual', null),
  ('80154778-7a6f-5c58-9b04-92d5509b050e', (select id from topic where path = 'direito_processual_penal.inquerito_policial'), 'manual', null),
  ('ec2df32f-9d99-595d-8e61-6f0280edf03e', (select id from topic where path = 'informatica.planilhas_eletronicas'), 'manual', null),
  ('48404960-dd49-503d-a572-0d983e61c87a', (select id from topic where path = 'informatica.seguranca_da_informacao.golpes_e_ataques'), 'manual', null),
  ('9837a453-1b7a-5d25-9e2f-2888e4ca8c6f', (select id from topic where path = 'raciocinio_logico.logica_proposicional.negacao'), 'manual', null),
  ('f3dcd382-3cda-5c21-beeb-04e7078ba361', (select id from topic where path = 'raciocinio_logico.logica_proposicional.equivalencias'), 'manual', null),
  ('2bc00fa6-c204-5ddb-896c-c49bf37aa4ee', (select id from topic where path = 'matematica.porcentagem'), 'manual', null),
  ('432cadf9-d52c-53f6-99f2-6d94dff5af39', (select id from topic where path = 'matematica.estatistica_basica.media'), 'manual', null),
  ('ee10b29e-bf3b-599e-be9c-1f79d68cb021', (select id from topic where path = 'direito_constitucional.seguranca_publica.orgaos_policiais'), 'manual', null),
  ('42f48100-b3bf-5937-93e9-3ee8c5964189', (select id from topic where path = 'direito_constitucional.direitos_e_garantias_fundamentais.direitos_individuais'), 'manual', null),
  ('ef3c617b-e5fd-5ec1-9b12-65317047666d', (select id from topic where path = 'direito_administrativo.atos_administrativos.atributos'), 'manual', null),
  ('6bf0aa67-9ff4-5030-b232-3ba9dd83b31b', (select id from topic where path = 'direito_administrativo.poderes_administrativos.poder_disciplinar'), 'manual', null),
  ('b6cc32e3-5dab-55be-adfb-9dbf50439693', (select id from topic where path = 'direito_administrativo.atos_administrativos.atributos'), 'manual', null),
  ('7b909ce8-f2aa-5b01-88df-36a75f3372a9', (select id from topic where path = 'direito_penal.teoria_do_crime.dolo_e_culpa'), 'manual', null),
  ('679324f9-8c3e-5fb4-87a4-5aab65f61304', (select id from topic where path = 'lingua_portuguesa.concordancia.verbal'), 'manual', null),
  ('10284b72-20bf-5894-a44f-2bd556234c22', (select id from topic where path = 'lingua_portuguesa.crase'), 'manual', null),
  ('a5373b39-f9d4-520d-bbf3-ec5ad2f23258', (select id from topic where path = 'informatica.seguranca_da_informacao.mecanismos_de_protecao'), 'manual', null),
  ('b9a87fee-3ad8-52f7-bfb2-397fedc1b2f4', (select id from topic where path = 'lingua_portuguesa.concordancia.verbal'), 'manual', null),
  ('b6ef081f-d54b-561e-a582-da1a793ac75b', (select id from topic where path = 'lingua_portuguesa.crase'), 'manual', null),
  ('31317796-fc00-5272-8a38-4b9cb3c6aafc', (select id from topic where path = 'lingua_portuguesa.pontuacao'), 'manual', null),
  ('85cbd34d-be3d-55ac-90a5-b8e11695afda', (select id from topic where path = 'direito_constitucional.seguranca_publica.orgaos_policiais'), 'manual', null),
  ('0142575a-0fd5-500c-b7a1-6bba87d16dc7', (select id from topic where path = 'direito_constitucional.direitos_e_garantias_fundamentais.remedios_constitucionais'), 'manual', null),
  ('2371fddb-e84d-59bd-81c6-e47b7b1d787f', (select id from topic where path = 'direito_penal.aplicacao_da_lei_penal.lei_penal_no_tempo'), 'manual', null),
  ('ea9203e6-932a-5740-a6c4-baa7f7fe430f', (select id from topic where path = 'direito_penal.crimes_contra_o_patrimonio.roubo'), 'manual', null),
  ('5a7e83c3-ffdc-5ee9-9940-aa352fbb0681', (select id from topic where path = 'direito_processual_penal.prisao.prisao_em_flagrante'), 'manual', null),
  ('69b5e911-0a27-5078-9348-3f8e115ace61', (select id from topic where path = 'direito_processual_penal.inquerito_policial'), 'manual', null),
  ('12c6fc02-f0b5-5ff4-965c-3aaf2925395a', (select id from topic where path = 'informatica.redes_e_internet.protocolos'), 'manual', null),
  ('3f482796-07bd-5708-b931-0ee4f34a669e', (select id from topic where path = 'informatica.seguranca_da_informacao.malware'), 'manual', null),
  ('263d00f2-986d-5e81-9f73-e65ff7560dac', (select id from topic where path = 'raciocinio_logico.sequencias'), 'manual', null),
  ('d127c588-8ef5-5d87-b59c-b6b51de0e90a', (select id from topic where path = 'matematica.porcentagem'), 'manual', null),
  ('a22d7464-04f9-59c4-8c50-80056eb1f230', (select id from topic where path = 'lingua_portuguesa.interpretacao_de_texto'), 'manual', null),
  ('50f4dc03-323c-5ba9-bc3c-789049abd52c', (select id from topic where path = 'lingua_portuguesa.coesao_e_coerencia.referenciacao'), 'manual', null),
  ('9ab71328-e723-51a5-ac3e-50f09cd29892', (select id from topic where path = 'lingua_portuguesa.sintaxe.termos_da_oracao'), 'manual', null),
  ('b9d58714-43a4-541e-b67a-06cb2a8d5cab', (select id from topic where path = 'direito_constitucional.seguranca_publica'), 'manual', null),
  ('f3443914-9b11-5bd7-ba93-5f635899a966', (select id from topic where path = 'direito_constitucional.direitos_e_garantias_fundamentais.direitos_individuais'), 'manual', null),
  ('7f31d81d-61c5-5fb8-9b7b-6bbed8aada20', (select id from topic where path = 'direito_penal.teoria_do_crime.iter_criminis'), 'manual', null),
  ('8c4cf665-55ab-5a5e-9914-d0ab8ce746d9', (select id from topic where path = 'direito_penal.crimes_contra_a_pessoa.homicidio'), 'manual', null),
  ('ced692d1-338c-508f-9553-cc69c701b529', (select id from topic where path = 'direito_processual_penal.prisao.prisao_em_flagrante'), 'manual', null),
  ('5eb67fab-a68f-5aa5-a874-8440a1ebaf98', (select id from topic where path = 'direito_administrativo.poderes_administrativos.poder_de_policia'), 'manual', null),
  ('2318c91a-629e-58f5-b937-8ade0b79b75c', (select id from topic where path = 'direito_administrativo.atos_administrativos.atributos'), 'manual', null),
  ('813b66da-10bb-5eb0-a150-cd43b4e53f1b', (select id from topic where path = 'informatica.planilhas_eletronicas'), 'manual', null),
  ('79872685-f56a-5638-b886-eb55d8d50e20', (select id from topic where path = 'raciocinio_logico.logica_de_argumentacao'), 'manual', null),
  ('ffd004ca-ad63-553d-a200-6d573aaf0b1b', (select id from topic where path = 'legislacao_penal_especial.lei_de_drogas'), 'manual', null),
  ('3d753b55-74ae-5fb7-86d7-7651cf5aec2d', (select id from topic where path = 'lingua_portuguesa.ortografia'), 'manual', null),
  ('e7f7aab6-145e-5157-8def-c5abe17aafe8', (select id from topic where path = 'lingua_portuguesa.concordancia.nominal'), 'manual', null),
  ('33408219-51fa-5038-b5d7-bb0bbc61e1fd', (select id from topic where path = 'direito_constitucional.seguranca_publica.orgaos_policiais'), 'manual', null),
  ('e79db1c4-10dc-57e0-996d-373fee4de1a8', (select id from topic where path = 'direito_constitucional.direitos_e_garantias_fundamentais.direitos_sociais'), 'manual', null),
  ('b89e8e25-11e5-5fed-b949-45e784ce2c75', (select id from topic where path = 'direito_penal.teoria_do_crime.excludentes_de_ilicitude'), 'manual', null),
  ('2ccdbd7e-fd70-5f17-b271-f9f32d1317d1', (select id from topic where path = 'direito_penal.crimes_contra_o_patrimonio.furto'), 'manual', null),
  ('2ccdbd7e-fd70-5f17-b271-f9f32d1317d1', (select id from topic where path = 'direito_penal.crimes_contra_o_patrimonio.roubo'), 'manual', null),
  ('d5652a9a-6b0d-5b6c-9868-de58a3a31df3', (select id from topic where path = 'matematica.razao_e_proporcao'), 'manual', null),
  ('b893fc53-9653-586c-8ad4-fadeb55876ef', (select id from topic where path = 'matematica.porcentagem'), 'manual', null),
  ('9e5c546d-68f5-569c-b93a-1673300e2914', (select id from topic where path = 'raciocinio_logico.sequencias'), 'manual', null),
  ('fb100307-a070-500b-8473-bdc42ce844eb', (select id from topic where path = 'informatica.sistemas_operacionais.windows'), 'manual', null),
  ('4d246322-7c15-5dc9-9452-5a8dd21dc42d', (select id from topic where path = 'informatica.redes_e_internet.correio_eletronico'), 'manual', null),
  ('365d9de4-95cf-50d9-9268-0aba9fe04645', (select id from topic where path = 'direito_constitucional.direitos_e_garantias_fundamentais.direitos_individuais'), 'manual', null);

insert into question_asset (question_id, asset_id, position) values
  ('ec2df32f-9d99-595d-8e61-6f0280edf03e', (select id from asset where sha256 = 'da551c8e5be5f45863f5befa198002e3f2ebb6fb4857df032137892f76d9d258'), 0),
  ('263d00f2-986d-5e81-9f73-e65ff7560dac', (select id from asset where sha256 = '0ff23f212b37f3b0b9239f154213c1e46627dea208056a2631adddf75359b12d'), 0);

commit;
