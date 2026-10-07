"""Gera db/seed/seed.sql (SPECIFICATIONS.md §6).

As questões abaixo foram escritas para o seed: não vêm de provas reais. Concursos, provas e
documentos são fictícios e marcados (slug `seed-`, URLs em `seed.emmoni.invalid`). Bancas,
órgãos e cargos são reais, porque o catálogo é o mesmo que a ingestão vai usar.

Uso: uv run python scripts/build_seed.py [--check]
"""

import hashlib
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ingest.content import asset_refs, statement_hash

ROOT = Path(__file__).resolve().parent.parent
SEED_SQL = ROOT / "db" / "seed" / "seed.sql"
ASSETS_DIR = ROOT / "db" / "seed" / "assets"
NAMESPACE = uuid.UUID("6f1d3c52-8a0b-4b7e-9c55-2e7d1f0a9b31")
FETCHED_AT = "2026-10-07T00:00:00Z"


def sha256_file(name: str) -> str:
    return hashlib.sha256((ASSETS_DIR / name).read_bytes()).hexdigest()


ASSETS = {
    "planilha": {
        "file": "planilha.svg",
        "alt": "Planilha com a coluna A (Equipe: Alfa, Bravo, Charlie) e a coluna B "
        "(Ocorrências: 10, 20 e 30 nas células B2, B3 e B4); a célula B5 está destacada e vazia.",
        "width": 320,
        "height": 200,
    },
    "sequencia": {
        "file": "sequencia.svg",
        "alt": "Cinco quadros em sequência com os números 2, 6, 18, 54 e um ponto de interrogação.",
        "width": 400,
        "height": 90,
    },
}
for _asset in ASSETS.values():
    _asset["sha256"] = sha256_file(str(_asset["file"]))


def img(key: str) -> str:
    a = ASSETS[key]
    return f"![{a['alt']}](asset:{a['sha256']})"


EXAM_BOARDS = [
    (
        "cebraspe",
        "Centro Brasileiro de Pesquisa em Avaliação e Seleção e de Promoção de Eventos",
        "Cebraspe",
    ),
    ("fgv", "Fundação Getulio Vargas", "FGV"),
    ("vunesp", "Fundação para o Vestibular da Universidade Estadual Paulista", "Vunesp"),
]

# slug, nome, sigla, carreira, esfera, UF
AGENCIES = [
    ("pf", "Polícia Federal", "PF", "pf", "federal", None),
    ("prf", "Polícia Rodoviária Federal", "PRF", "prf", "federal", None),
    ("pc-sp", "Polícia Civil do Estado de São Paulo", "PC-SP", "policia_civil", "estadual", "SP"),
    (
        "pc-rj",
        "Polícia Civil do Estado do Rio de Janeiro",
        "PC-RJ",
        "policia_civil",
        "estadual",
        "RJ",
    ),
    (
        "pm-sp",
        "Polícia Militar do Estado de São Paulo",
        "PM-SP",
        "policia_militar",
        "estadual",
        "SP",
    ),
]

# órgão, slug, nome, escolaridade
POSITIONS = [
    ("pf", "agente", "Agente de Polícia Federal", "superior"),
    ("prf", "policial-rodoviario-federal", "Policial Rodoviário Federal", "superior"),
    ("pc-sp", "investigador", "Investigador de Polícia", "superior"),
    ("pc-rj", "inspetor", "Inspetor de Polícia Civil", "superior"),
    ("pm-sp", "soldado", "Soldado PM de 2ª Classe", "medio"),
]


@dataclass
class Q:
    subject: str
    topics: list[str]
    statement: str
    answer: str  # gabarito definitivo; para anulada, o preliminar
    options: list[str] = field(default_factory=list)
    passage: str | None = None
    preliminary: str | None = None  # só quando diferente do definitivo
    annulled: bool = False


@dataclass
class Contest:
    slug: str
    agency: str
    board: str
    year: int
    notice: str
    name: str
    exam_slug: str
    exam_name: str
    applied_on: str
    position: str
    passages: dict[str, str]
    questions: list[Q]


P = "lingua-portuguesa"
DC = "direito-constitucional"
DP = "direito-penal"
DPP = "direito-processual-penal"
DA = "direito-administrativo"
LPE = "legislacao-penal-especial"
INF = "informatica"
RL = "raciocinio-logico"
MAT = "matematica"

CONTESTS = [
    Contest(
        slug="seed-pf-2025",
        agency="pf",
        board="cebraspe",
        year=2025,
        notice="1/2025 (fictício)",
        name="PF 2025 — Agente (seed)",
        exam_slug="agente",
        exam_name="Agente de Polícia Federal — prova objetiva",
        applied_on="2025-06-15",
        position="agente",
        passages={
            "dados": (
                "A investigação criminal moderna depende cada vez mais da análise de dados. "
                "Bancos de informações, registros telefônicos e rastros digitais permitem que as "
                "equipes reconstruam, com precisão crescente, a dinâmica de um delito. Contudo, a "
                "tecnologia não substitui o trabalho de campo: é o investigador quem formula "
                "hipóteses, confronta versões e decide quais evidências merecem atenção. Os dados, "
                "por si sós, não falam; precisam ser interrogados."
            )
        },
        questions=[
            Q(
                P,
                ["interpretacao_de_texto"],
                "De acordo com o texto, a tecnologia tornou o trabalho de campo dispensável na "
                "investigação criminal.",
                "E",
                passage="dados",
            ),
            Q(
                P,
                ["concordancia.nominal"],
                "No trecho “Os dados, por si sós, não falam”, a palavra “sós” concorda em número com "
                "“dados”, razão pela qual está flexionada no plural.",
                "C",
                passage="dados",
            ),
            Q(
                P,
                ["pontuacao"],
                "Os dois-pontos empregados logo após “trabalho de campo” introduzem uma explicação "
                "do que se afirma na oração anterior.",
                "C",
                passage="dados",
            ),
            Q(
                P,
                ["coesao_e_coerencia.conectivos"],
                "A substituição de “Contudo” por **Portanto** preservaria o sentido original do "
                "texto.",
                "E",
                passage="dados",
            ),
            Q(
                DC,
                ["seguranca_publica.orgaos_policiais"],
                "Segundo a Constituição Federal de 1988, a Polícia Federal é instituída por lei como "
                "órgão permanente, organizado e mantido pela União e estruturado em carreira.",
                "C",
            ),
            Q(
                DC,
                ["direitos_e_garantias_fundamentais.remedios_constitucionais"],
                "O *habeas data* é o remédio constitucional adequado para assegurar o direito de "
                "locomoção de quem sofre ameaça de prisão ilegal.",
                "E",
            ),
            Q(
                DC,
                ["direitos_e_garantias_fundamentais.direitos_individuais"],
                "A casa é asilo inviolável do indivíduo, mas nela se pode penetrar, sem "
                "consentimento do morador, em caso de flagrante delito, ainda que durante a noite.",
                "C",
            ),
            Q(
                DP,
                ["aplicacao_da_lei_penal.tempo_do_crime"],
                "Considera-se praticado o crime no momento da ação ou omissão, ainda que outro seja "
                "o momento do resultado.",
                "C",
            ),
            Q(
                DP,
                ["crimes_contra_o_patrimonio.furto"],
                "No crime de furto, a pena é aumentada de um terço se o fato é praticado durante o "
                "repouso noturno.",
                "C",
            ),
            Q(
                DP,
                ["crimes_contra_o_patrimonio.roubo"],
                "Para a configuração do crime de roubo, é indispensável que a violência ou a grave "
                "ameaça seja dirigida contra o próprio titular do patrimônio subtraído.",
                "E",
                preliminary="C",
            ),
            Q(
                DPP,
                ["inquerito_policial"],
                "O inquérito policial é procedimento indispensável ao oferecimento da denúncia pelo "
                "Ministério Público.",
                "E",
            ),
            Q(
                DPP,
                ["inquerito_policial"],
                "A autoridade policial não poderá mandar arquivar autos de inquérito.",
                "C",
            ),
            Q(
                INF,
                ["planilhas_eletronicas"],
                f"{img('planilha')}\n\nConsiderando a planilha mostrada na figura, a fórmula "
                "`=MÉDIA(B2:B4)`, inserida na célula B5, resultará no valor 20.",
                "C",
            ),
            Q(
                INF,
                ["seguranca_da_informacao.golpes_e_ataques"],
                "*Phishing* é uma técnica em que o atacante se passa por instituição confiável para "
                "induzir a vítima a fornecer dados sensíveis.",
                "C",
            ),
        ],
    ),
    Contest(
        slug="seed-prf-2024",
        agency="prf",
        board="cebraspe",
        year=2024,
        notice="1/2024 (fictício)",
        name="PRF 2024 — Policial Rodoviário Federal (seed)",
        exam_slug="policial",
        exam_name="Policial Rodoviário Federal — prova objetiva",
        applied_on="2024-08-18",
        position="policial-rodoviario-federal",
        passages={
            "autuacoes": (
                "A tabela a seguir mostra o número de autuações registradas em um posto de "
                "fiscalização no primeiro trimestre de um ano.\n\n"
                "| Mês | Autuações |\n"
                "|---|---:|\n"
                "| Janeiro | 200 |\n"
                "| Fevereiro | 250 |\n"
                "| Março | 240 |"
            )
        },
        questions=[
            Q(
                RL,
                ["logica_proposicional.negacao"],
                "A negação da proposição “Todos os condutores foram multados” é “Nenhum condutor "
                "foi multado”.",
                "E",
            ),
            Q(
                RL,
                ["logica_proposicional.equivalencias"],
                "A proposição “Se chove, então a pista fica escorregadia” é equivalente a “Se a "
                "pista não fica escorregadia, então não chove”.",
                "C",
            ),
            Q(
                MAT,
                ["porcentagem"],
                "Com base na tabela, o número de autuações em fevereiro foi 25% superior ao de "
                "janeiro.",
                "C",
                passage="autuacoes",
            ),
            Q(
                MAT,
                ["estatistica_basica.media"],
                "Com base na tabela, a média mensal de autuações no trimestre foi superior a 230.",
                "E",
                passage="autuacoes",
            ),
            Q(
                DC,
                ["seguranca_publica.orgaos_policiais"],
                "A Polícia Rodoviária Federal destina-se, na forma da lei, ao patrulhamento "
                "ostensivo das rodovias federais.",
                "C",
            ),
            Q(
                DC,
                ["direitos_e_garantias_fundamentais.direitos_individuais"],
                "É livre a manifestação do pensamento, sendo permitido o anonimato.",
                "E",
            ),
            Q(
                DA,
                ["atos_administrativos.atributos"],
                "A autoexecutoriedade permite à administração pública executar suas próprias "
                "decisões sem prévia autorização do Poder Judiciário, nos casos previstos em lei ou "
                "em situações de urgência.",
                "C",
            ),
            Q(
                DA,
                ["poderes_administrativos.poder_disciplinar"],
                "O poder disciplinar é exercido pela administração sobre todos os particulares, "
                "independentemente de qualquer vínculo com o Estado.",
                "E",
            ),
            Q(
                DA,
                ["atos_administrativos.atributos"],
                "A presunção de legitimidade dos atos administrativos é absoluta e não admite prova "
                "em contrário.",
                "E",
            ),
            Q(
                DP,
                ["teoria_do_crime.dolo_e_culpa"],
                "Homicídio culposo é aquele em que o agente quis o resultado ou assumiu o risco de "
                "produzi-lo.",
                "E",
            ),
            Q(
                P,
                ["concordancia.verbal"],
                "Na frase “Haviam muitos veículos na rodovia”, o verbo haver está corretamente "
                "flexionado.",
                "E",
            ),
            Q(
                P,
                ["crase"],
                "Em “Refiro-me à fiscalização das rodovias”, o emprego do sinal indicativo de crase "
                "é obrigatório.",
                "C",
            ),
            Q(
                INF,
                ["seguranca_da_informacao.mecanismos_de_protecao"],
                "Um *firewall* impede, por si só, qualquer tipo de infecção por vírus em um "
                "computador.",
                "E",
                annulled=True,
            ),
        ],
    ),
    Contest(
        slug="seed-pcsp-2025",
        agency="pc-sp",
        board="vunesp",
        year=2025,
        notice="1/2025 (fictício)",
        name="PC-SP 2025 — Investigador (seed)",
        exam_slug="investigador",
        exam_name="Investigador de Polícia — prova objetiva",
        applied_on="2025-03-23",
        position="investigador",
        passages={},
        questions=[
            Q(
                P,
                ["concordancia.verbal"],
                "Assinale a alternativa em que a concordância verbal está de acordo com a "
                "norma-padrão.",
                "D",
                options=[
                    "Fazem dois anos que o inquérito foi instaurado.",
                    "Existe, nos autos, provas suficientes para a denúncia.",
                    "Houveram diversas diligências no bairro.",
                    "Faltam três testemunhas para concluir a oitiva.",
                    "Chegou, ao fim da tarde, os peritos do instituto.",
                ],
            ),
            Q(
                P,
                ["crase"],
                "Assinale a alternativa em que o sinal indicativo de crase está empregado "
                "corretamente.",
                "B",
                options=[
                    "O delegado referiu-se à todos os envolvidos.",
                    "A equipe chegou à delegacia antes do amanhecer.",
                    "Os documentos foram entregues à ele.",
                    "O suspeito começou à confessar.",
                    "Ficou frente à frente com o depoente.",
                ],
            ),
            Q(
                P,
                ["pontuacao"],
                "Assinale a alternativa pontuada de acordo com a norma-padrão.",
                "C",
                options=[
                    "Os policiais, chegaram ao local rapidamente.",
                    "O investigador que trabalha no plantão, redigiu o relatório.",
                    "Ontem à noite, a equipe cumpriu o mandado de busca.",
                    "A testemunha disse, que não viu nada.",
                    "O laudo pericial, foi anexado ao inquérito.",
                ],
            ),
            Q(
                DC,
                ["seguranca_publica.orgaos_policiais"],
                "De acordo com a Constituição Federal, às polícias civis, dirigidas por delegados de "
                "polícia de carreira, incumbem, ressalvada a competência da União,",
                "B",
                options=[
                    "o policiamento ostensivo e a preservação da ordem pública.",
                    "as funções de polícia judiciária e a apuração de infrações penais, exceto as "
                    "militares.",
                    "a execução de atividades de defesa civil.",
                    "o patrulhamento ostensivo das ferrovias federais.",
                    "a segurança dos estabelecimentos penais.",
                ],
            ),
            Q(
                DC,
                ["direitos_e_garantias_fundamentais.remedios_constitucionais"],
                "O remédio constitucional cabível para proteger direito líquido e certo, não "
                "amparado por *habeas corpus* ou *habeas data*, quando o responsável pela "
                "ilegalidade for autoridade pública, é o",
                "B",
                options=[
                    "mandado de injunção.",
                    "mandado de segurança.",
                    "ação popular.",
                    "*habeas corpus*.",
                    "ação civil pública.",
                ],
            ),
            Q(
                DP,
                ["aplicacao_da_lei_penal.lei_penal_no_tempo"],
                "A lei posterior que, de qualquer modo, favorecer o agente",
                "C",
                options=[
                    "aplica-se somente aos fatos ainda não julgados.",
                    "não se aplica aos fatos anteriores, em respeito à coisa julgada.",
                    "aplica-se aos fatos anteriores, ainda que decididos por sentença condenatória "
                    "transitada em julgado.",
                    "aplica-se apenas se o condenado ainda não tiver iniciado o cumprimento da pena.",
                    "depende de autorização do juiz da execução para ser aplicada.",
                ],
            ),
            Q(
                DP,
                ["crimes_contra_o_patrimonio.roubo"],
                "Subtrair, para si, coisa alheia móvel, mediante grave ameaça à pessoa, configura o "
                "crime de",
                "B",
                options=[
                    "furto.",
                    "roubo.",
                    "extorsão.",
                    "apropriação indébita.",
                    "estelionato.",
                ],
            ),
            Q(
                DPP,
                ["prisao.prisao_em_flagrante"],
                "Nos termos do Código de Processo Penal, considera-se em flagrante delito quem",
                "B",
                options=[
                    "é apontado como autor do crime em denúncia anônima recebida uma semana após o "
                    "fato.",
                    "está cometendo a infração penal.",
                    "confessa espontaneamente o crime dias depois.",
                    "é reconhecido por fotografia um mês após o fato.",
                    "possui antecedentes criminais pelo mesmo tipo de delito.",
                ],
            ),
            Q(
                DPP,
                ["inquerito_policial"],
                "Sobre o inquérito policial, é correto afirmar que",
                "C",
                options=[
                    "é imprescindível para a propositura da ação penal.",
                    "pode ser arquivado pela autoridade policial.",
                    "tem natureza inquisitiva e caráter informativo.",
                    "está sujeito ao contraditório pleno, sob pena de nulidade.",
                    "só pode ser instaurado mediante requisição judicial.",
                ],
            ),
            Q(
                INF,
                ["redes_e_internet.protocolos"],
                "O protocolo utilizado para a transferência de páginas *web* de forma criptografada "
                "é o",
                "C",
                options=["FTP.", "SMTP.", "HTTPS.", "POP3.", "DNS."],
            ),
            Q(
                INF,
                ["seguranca_da_informacao.malware"],
                "O tipo de código malicioso que cifra os dados da vítima e exige pagamento para "
                "liberá-los é o",
                "B",
                options=[
                    "*spyware*.",
                    "*ransomware*.",
                    "*adware*.",
                    "*keylogger*.",
                    "*worm*.",
                ],
            ),
            Q(
                RL,
                ["sequencias"],
                f"{img('sequencia')}\n\nA figura mostra os quatro primeiros termos de uma "
                "sequência. Mantido o mesmo padrão, o termo que substitui o ponto de interrogação é",
                "C",
                options=["108", "148", "162", "216", "72"],
            ),
            Q(
                MAT,
                ["porcentagem"],
                "Um lote de 80 inquéritos foi distribuído entre duas delegacias. A primeira recebeu "
                "35% do lote. A segunda recebeu",
                "C",
                options=[
                    "28 inquéritos.",
                    "45 inquéritos.",
                    "52 inquéritos.",
                    "48 inquéritos.",
                    "35 inquéritos.",
                ],
            ),
        ],
    ),
    Contest(
        slug="seed-pcrj-2024",
        agency="pc-rj",
        board="fgv",
        year=2024,
        notice="1/2024 (fictício)",
        name="PC-RJ 2024 — Inspetor (seed)",
        exam_slug="inspetor",
        exam_name="Inspetor de Polícia Civil — prova objetiva",
        applied_on="2024-11-10",
        position="inspetor",
        passages={
            "rotina": (
                "O trabalho policial é frequentemente retratado como uma sucessão de perseguições "
                "e confrontos. A rotina real, porém, é feita sobretudo de escuta, registro e "
                "paciência. Um boletim de ocorrência bem redigido pode ser mais decisivo para a "
                "solução de um caso do que uma diligência espetacular, porque é nele que se "
                "preservam os detalhes que a memória, com o tempo, apaga."
            )
        },
        questions=[
            Q(
                P,
                ["interpretacao_de_texto"],
                "Segundo o texto, a rotina real do trabalho policial caracteriza-se principalmente "
                "por",
                "B",
                passage="rotina",
                options=[
                    "perseguições e confrontos.",
                    "escuta, registro e paciência.",
                    "diligências espetaculares.",
                    "improvisação.",
                    "uso intensivo da força.",
                ],
            ),
            Q(
                P,
                ["coesao_e_coerencia.referenciacao"],
                "No trecho “porque é nele que se preservam os detalhes”, o pronome “nele” retoma",
                "C",
                passage="rotina",
                options=[
                    "o trabalho policial.",
                    "o caso.",
                    "o boletim de ocorrência.",
                    "a diligência.",
                    "o tempo.",
                ],
            ),
            Q(
                P,
                ["sintaxe.termos_da_oracao"],
                "A frase em que o termo sublinhado exerce a função de adjunto adverbial de tempo é",
                "A",
                options=[
                    "<u>Ontem</u>, o inspetor ouviu as testemunhas.",
                    "O inspetor ouviu <u>as testemunhas</u>.",
                    "<u>O inspetor</u> ouviu as testemunhas ontem.",
                    "O inspetor <u>ouviu</u> as testemunhas.",
                    "As testemunhas foram ouvidas <u>pelo inspetor</u>.",
                ],
            ),
            Q(
                DC,
                ["seguranca_publica"],
                "Segundo a Constituição Federal, a segurança pública é",
                "B",
                options=[
                    "dever exclusivo da União.",
                    "dever do Estado, direito e responsabilidade de todos.",
                    "atribuição exclusiva das polícias militares.",
                    "responsabilidade apenas dos municípios.",
                    "dever do Estado, sem participação da sociedade.",
                ],
            ),
            Q(
                DC,
                ["direitos_e_garantias_fundamentais.direitos_individuais"],
                "Todos podem reunir-se pacificamente, sem armas, em locais abertos ao público, desde "
                "que",
                "B",
                options=[
                    "haja autorização prévia da autoridade policial.",
                    "não frustrem outra reunião anteriormente convocada para o mesmo local, sendo "
                    "apenas exigido prévio aviso à autoridade competente.",
                    "a reunião ocorra somente em dias úteis.",
                    "o número de participantes não ultrapasse cem pessoas.",
                    "a reunião seja comunicada ao Poder Judiciário com trinta dias de antecedência.",
                ],
            ),
            Q(
                DP,
                ["teoria_do_crime.iter_criminis"],
                "Quando o agente, voluntariamente, desiste de prosseguir na execução do crime, "
                "ocorre",
                "C",
                options=[
                    "arrependimento posterior.",
                    "crime impossível.",
                    "desistência voluntária.",
                    "tentativa perfeita.",
                    "arrependimento eficaz.",
                ],
            ),
            Q(
                DP,
                ["crimes_contra_a_pessoa.homicidio"],
                "O homicídio praticado mediante paga ou promessa de recompensa é classificado como",
                "C",
                options=["privilegiado.", "culposo.", "qualificado.", "simples.", "preterdoloso."],
            ),
            Q(
                DPP,
                ["prisao.prisao_em_flagrante"],
                "A prisão de qualquer pessoa e o local onde se encontre devem ser comunicados "
                "imediatamente",
                "B",
                options=[
                    "apenas à família do preso.",
                    "ao juiz competente, ao Ministério Público e à família do preso ou à pessoa por "
                    "ele indicada.",
                    "somente ao Ministério Público.",
                    "ao juiz competente, no prazo de cinco dias.",
                    "exclusivamente à Defensoria Pública.",
                ],
            ),
            Q(
                DA,
                ["poderes_administrativos.poder_de_policia"],
                "O poder conferido à administração para condicionar e restringir o uso e o gozo de "
                "bens, atividades e direitos individuais em benefício da coletividade é o poder",
                "D",
                options=[
                    "hierárquico.",
                    "disciplinar.",
                    "regulamentar.",
                    "de polícia.",
                    "normativo.",
                ],
            ),
            Q(
                DA,
                ["atos_administrativos.atributos"],
                "O atributo do ato administrativo que permite sua imposição a terceiros, "
                "independentemente de sua concordância, é a",
                "A",
                options=[
                    "imperatividade.",
                    "tipicidade.",
                    "motivação.",
                    "publicidade.",
                    "finalidade.",
                ],
            ),
            Q(
                INF,
                ["planilhas_eletronicas"],
                'Em uma planilha eletrônica, a fórmula `=SE(A1>=7;"Aprovado";"Reprovado")` '
                "retornará, quando A1 contiver o valor 6,",
                "B",
                options=[
                    "Aprovado.",
                    "Reprovado.",
                    "6.",
                    "7.",
                    "VERDADEIRO.",
                ],
            ),
            Q(
                RL,
                ["logica_de_argumentacao"],
                "Se é verdade que “Nenhum inspetor é negligente” e que “Algum servidor é inspetor”, "
                "então é necessariamente verdade que",
                "A",
                options=[
                    "algum servidor não é negligente.",
                    "todo servidor é inspetor.",
                    "nenhum servidor é negligente.",
                    "algum negligente é inspetor.",
                    "todo negligente é servidor.",
                ],
            ),
            Q(
                LPE,
                ["lei_de_drogas"],
                "Segundo a Lei nº 11.343/2006, a quem adquire ou traz consigo droga para consumo "
                "pessoal **não** é prevista a",
                "D",
                options=[
                    "advertência sobre os efeitos das drogas.",
                    "prestação de serviços à comunidade.",
                    "medida educativa de comparecimento a programa ou curso educativo.",
                    "pena privativa de liberdade.",
                    "aplicação isolada ou cumulativa das medidas previstas.",
                ],
            ),
        ],
    ),
    Contest(
        slug="seed-pmsp-2024",
        agency="pm-sp",
        board="vunesp",
        year=2024,
        notice="2/2024 (fictício)",
        name="PM-SP 2024 — Soldado (seed)",
        exam_slug="soldado",
        exam_name="Soldado PM de 2ª Classe — prova objetiva",
        applied_on="2024-05-05",
        position="soldado",
        passages={},
        questions=[
            Q(
                P,
                ["ortografia"],
                "Assinale a alternativa em que a palavra está grafada corretamente.",
                "C",
                options=["excessão", "previlégio", "exceção", "beneficiente"],
            ),
            Q(
                P,
                ["concordancia.nominal"],
                "Assinale a alternativa correta quanto à concordância nominal.",
                "C",
                options=[
                    "Seguem anexo os documentos.",
                    "É proibida entrada de pessoas estranhas.",
                    "Ela mesma redigiu o relatório.",
                    "Ficaram bastantes satisfeitos os comandantes.",
                ],
            ),
            Q(
                DC,
                ["seguranca_publica.orgaos_policiais"],
                "Às polícias militares cabem, segundo a Constituição Federal,",
                "A",
                options=[
                    "a polícia ostensiva e a preservação da ordem pública.",
                    "as funções de polícia judiciária da União.",
                    "a apuração das infrações penais militares federais.",
                    "o patrulhamento ostensivo das rodovias federais.",
                ],
            ),
            Q(
                DC,
                ["direitos_e_garantias_fundamentais.direitos_sociais"],
                "São direitos sociais, conforme o art. 6º da Constituição Federal, entre outros,",
                "A",
                options=[
                    "a educação, a saúde e a segurança.",
                    "o *habeas corpus* e o mandado de segurança.",
                    "a nacionalidade e a cidadania.",
                    "o voto e a elegibilidade.",
                ],
            ),
            Q(
                DP,
                ["teoria_do_crime.excludentes_de_ilicitude"],
                "Entende-se em legítima defesa quem, usando moderadamente dos meios necessários, "
                "repele",
                "B",
                options=[
                    "agressão futura e incerta.",
                    "injusta agressão, atual ou iminente, a direito seu ou de outrem.",
                    "qualquer agressão, ainda que justa.",
                    "perigo atual que não provocou por sua vontade.",
                ],
            ),
            Q(
                DP,
                ["crimes_contra_o_patrimonio.furto", "crimes_contra_o_patrimonio.roubo"],
                "O crime de furto distingue-se do roubo porque, no furto,",
                "B",
                options=[
                    "há emprego de violência contra a pessoa.",
                    "não há violência ou grave ameaça contra a pessoa.",
                    "a coisa subtraída é imóvel.",
                    "a vítima entrega a coisa voluntariamente.",
                ],
            ),
            Q(
                MAT,
                ["razao_e_proporcao"],
                "Uma viatura percorre 240 km com 30 litros de combustível. Mantido o mesmo consumo, "
                "quantos litros serão necessários para percorrer 400 km?",
                "B",
                options=["45", "50", "55", "60"],
            ),
            Q(
                MAT,
                ["porcentagem"],
                "Um batalhão tem 120 soldados, dos quais 30% são mulheres. O número de homens é",
                "B",
                options=["36", "84", "90", "80"],
            ),
            Q(
                RL,
                ["sequencias"],
                "Considere a sequência 3, 7, 11, 15, … O 10º termo dessa sequência é",
                "A",
                options=["39", "43", "40", "41"],
            ),
            Q(
                INF,
                ["sistemas_operacionais.windows"],
                "No Windows, o atalho de teclado utilizado para copiar um item selecionado é",
                "C",
                options=["Ctrl+V", "Ctrl+X", "Ctrl+C", "Ctrl+Z"],
            ),
            Q(
                INF,
                ["redes_e_internet.correio_eletronico"],
                "Para enviar uma mensagem de correio eletrônico a um destinatário sem que os demais "
                "destinatários vejam seu endereço, deve-se utilizar o campo",
                "C",
                options=["Para", "Cc", "Cco", "Assunto"],
            ),
            Q(
                DC,
                ["direitos_e_garantias_fundamentais.direitos_individuais"],
                "A Constituição Federal estabelece que ninguém será submetido a tortura nem a "
                "tratamento desumano ou degradante. Essa garantia está prevista entre",
                "A",
                options=[
                    "os direitos e garantias fundamentais.",
                    "as normas de organização dos Poderes.",
                    "as disposições sobre o sistema tributário.",
                    "as regras da ordem econômica.",
                ],
            ),
        ],
    ),
]


def lit(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def row(*values: object) -> str:
    return "(" + ", ".join(lit(v) for v in values) + ")"


def insert(table: str, columns: str, rows: list[str], suffix: str = "") -> str:
    return f"insert into {table} ({columns}) values\n  " + ",\n  ".join(rows) + f"{suffix};\n"


def subject_label(slug: str) -> str:
    return slug.replace("-", "_")


def build() -> str:
    out = [
        "-- GERADO por scripts/build_seed.py — não edite à mão (make seed-build).\n"
        "-- Questões fictícias para desenvolvimento do front-end (SPECIFICATIONS.md §6).\n",
        "begin;\n",
        "delete from contest where slug like 'seed-%';\n",
        "delete from source_document where url like 'https://seed.emmoni.invalid/%';\n\n",
        insert(
            "exam_board",
            "slug, name, short_name",
            [row(*b) for b in EXAM_BOARDS],
            "\non conflict (slug) do update set name = excluded.name, short_name = excluded.short_name",
        ),
        insert(
            "agency",
            "slug, name, short_name, career, level, state",
            [row(*a) for a in AGENCIES],
            "\non conflict (slug) do update set name = excluded.name, short_name = excluded.short_name",
        ),
    ]
    for agency, slug, name, education in POSITIONS:
        out.append(
            "insert into position (agency_id, slug, name, education_level)\n"
            f"select id, {lit(slug)}, {lit(name)}, {lit(education)} from agency where slug = "
            f"{lit(agency)}\non conflict (agency_id, slug) do update set name = excluded.name;\n"
        )
    out.append(
        insert(
            "asset",
            "sha256, mime_type, width, height, alt_text, storage_key",
            [
                row(
                    a["sha256"],
                    "image/svg+xml",
                    a["width"],
                    a["height"],
                    a["alt"],
                    f"{a['sha256']}.svg",
                )
                for a in ASSETS.values()
            ],
            "\non conflict (sha256) do nothing",
        )
    )

    passages, questions, options, topics, q_assets, p_assets = [], [], [], [], [], []
    for contest in CONTESTS:
        doc_url = f"https://seed.emmoni.invalid/{contest.slug}/{contest.exam_slug}.pdf"
        out.append(
            insert(
                "source_document",
                "kind, url, sha256, page_count, fetched_at",
                [row("exam", doc_url, hashlib.sha256(doc_url.encode()).hexdigest(), 8, FETCHED_AT)],
            )
        )
        out.append(
            "insert into contest (slug, agency_id, exam_board_id, year, notice_number, name)\n"
            f"select {lit(contest.slug)}, a.id, b.id, {contest.year}, {lit(contest.notice)}, "
            f"{lit(contest.name)}\n  from agency a, exam_board b where a.slug = "
            f"{lit(contest.agency)} and b.slug = {lit(contest.board)};\n"
            "insert into exam (contest_id, slug, name, applied_on, canonical_booklet, "
            "exam_document_id, publish_status)\n"
            f"select c.id, {lit(contest.exam_slug)}, {lit(contest.exam_name)}, "
            f"{lit(contest.applied_on)}, '1', d.id, 'published'\n"
            f"  from contest c, source_document d where c.slug = {lit(contest.slug)} and d.url = "
            f"{lit(doc_url)};\n"
            "insert into exam_position (exam_id, position_id)\n"
            "select e.id, p.id from exam e join contest c on c.id = e.contest_id\n"
            "  join position p on p.agency_id = c.agency_id\n"
            f" where c.slug = {lit(contest.slug)} and p.slug = {lit(contest.position)};\n"
        )
        exam_ref = (
            f"(select e.id from exam e join contest c on c.id = e.contest_id where c.slug = "
            f"{lit(contest.slug)})"
        )
        passage_ids = {}
        for key, body in contest.passages.items():
            pid = uuid.uuid5(NAMESPACE, f"{contest.slug}/passage/{key}")
            passage_ids[key] = pid
            passages.append(f"({lit(str(pid))}, {exam_ref}, {lit(body)}, 1)")
            for sha in asset_refs(body):
                p_assets.append(
                    f"({lit(str(pid))}, (select id from asset where sha256 = {lit(sha)}))"
                )

        for number, q in enumerate(contest.questions, start=1):
            qid = uuid.uuid5(NAMESPACE, f"{contest.slug}/{contest.exam_slug}/{number}")
            qtype = "multiple_choice" if q.options else "true_false"
            preliminary = q.preliminary or q.answer
            final = None if q.annulled else q.answer
            status = "annulled" if q.annulled else ("changed" if q.preliminary else "valid")
            passage = passage_ids[q.passage] if q.passage else None
            questions.append(
                f"({lit(str(qid))}, {exam_ref}, {number}, {lit(qtype)}, "
                f"(select id from subject where slug = {lit(q.subject)}), "
                f"{lit(str(passage) if passage else None)}, {lit(q.statement)}, "
                f"{lit(preliminary)}, {lit(final)}, {lit(status)}, "
                f"{lit(statement_hash(q.statement, q.options, contest.passages.get(q.passage or '')))}, {(number - 1) // 4 + 1}, 'seed@1', "
                "'published')"
            )
            for letter, body in zip("ABCDE", q.options, strict=False):
                options.append(row(str(qid), letter, body))
            for topic in q.topics:
                path = f"{subject_label(q.subject)}.{topic}"
                topics.append(
                    f"({lit(str(qid))}, (select id from topic where path = {lit(path)}), "
                    "'manual', null)"
                )
            refs = asset_refs(q.statement) + [s for o in q.options for s in asset_refs(o)]
            for position, sha in enumerate(dict.fromkeys(refs)):
                q_assets.append(
                    f"({lit(str(qid))}, (select id from asset where sha256 = {lit(sha)}), "
                    f"{position})"
                )

    out.append(insert("passage", "id, exam_id, body_md, source_page", passages))
    if p_assets:
        out.append(insert("passage_asset", "passage_id, asset_id", p_assets))
    out.append(
        insert(
            "question",
            "id, exam_id, number, type, subject_id, passage_id, statement_md, answer_preliminary, "
            "answer_final, answer_status, statement_hash, source_page, extracted_by, "
            "publish_status",
            questions,
        )
    )
    out.append(insert("question_option", "question_id, letter, body_md", options))
    out.append(insert("question_topic", "question_id, topic_id, origin, confidence", topics))
    out.append(insert("question_asset", "question_id, asset_id, position", q_assets))
    out.append("commit;\n")
    return "\n".join(out)


def main() -> int:
    sql = build()
    if "--check" in sys.argv:
        if not SEED_SQL.exists() or SEED_SQL.read_text() != sql:
            print("seed.sql desatualizado: rode `make seed-build`", file=sys.stderr)
            return 1
        return 0
    SEED_SQL.write_text(sql)
    total = sum(len(c.questions) for c in CONTESTS)
    print(f"seed: {total} questões em {len(CONTESTS)} concursos → {SEED_SQL.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
