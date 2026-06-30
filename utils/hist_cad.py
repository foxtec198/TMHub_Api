from os import getenv
from datetime import datetime as dt
from time import sleep
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from rapidfuzz import process, fuzz
load_dotenv();


engine = create_engine(getenv("DB_URI"))
historico = [
    {
        "data": "04/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'HÉLVIO ESTEVES',
        "reserva": 'CLAUDIMARY REJIANE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'ATESTADO MÉDICO',
        "reserva": 'ATESTADO MÉDICO',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSINÉIA MARTINIANO',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA - BIBLIOTECA',
        "reserva": 'ELAINE POTIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'TJ CÍVIL LONDRINA',
        "reserva": 'ROSÂNGELA BIRAL',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'LUANA BONIFÁCIO',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'MOACIR CAMARGO',
        "reserva": 'EDNA APARECIDA',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'AMÉRICA SABINO',
        "reserva": 'DAYANE DOS SANTOS',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'JULIANO STINGHEN',
        "reserva": 'NAIARA CRISTINA',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'IGNÊS CORSO',
        "reserva": 'FRANCIELE CARVALHO',
        "motivo": 'ATESTADO CIRÚRGICO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'NOEMI MALANGA',
        "reserva": 'LAÍS CAVALCANTE',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'TJ CRIMINAL LONDRINA',
        "reserva": 'ABIQUEILA PEREIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'VILMA ELISA',
        "reserva": 'LARISSA NATALINA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'TEREZA CANHADA',
        "reserva": 'JÉSSICA TRINDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'JANAÍNA RIBEIRO DE ASSIS',
        "local": 'FALTOU SEM JUSTIFICATIVA',
        "reserva": 'FALTOU SEM JUSTIFICATIVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'MÉLVIN JONNES',
        "reserva": 'CAROL DANDARA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'CMEI MARISA ARRUDA',
        "reserva": 'JONATHAS',
        "motivo": 'ATESTADO ATÉ DIA 06.05',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'JEFFERSON',
        "local": 'APARECIDO HONORATO',
        "reserva": None,
        "motivo": 'LIMPEZA PESADA',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'JÚNIOR ALVES',
        "local": 'APARECIDO HONORATO',
        "reserva": None,
        "motivo": 'LIMPEZA PESADA',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'SECRETARIA - MORINGÃO',
        "reserva": None,
        "motivo": 'LIMPEZA PESADA',
        "obs": None
    },
    {
        "data": "04/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'SECRETARIA - MORINGÃO',
        "reserva": None,
        "motivo": 'LIMPEZA PESADA',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'JOSÉ GASPARINI - ANEXO',
        "reserva": 'SUELI RODRIGUES DE SOUZA',
        "motivo": 'ATESTADO ATÉ DIA 06.05',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'ATESTADO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'ATESTADO',
        "reserva": 'ATESTADO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSINÉIA MARTINIANO',
        "motivo": 'POSTO VAGO',
        "obs": '90 DIAS'
    },
    {
        "data": "05/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA - BIBLIOTECA',
        "reserva": 'ELAINE POTIRA',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'SOLANGE ANDRADE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'LUANA BONIFÁCIO',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'ROSÂNGELA BIRAL',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'AMÉRICA SABINO',
        "reserva": 'DAIANE DOS SANTOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'SCHERER',
        "reserva": 'VAGA 44h EM ABERTO',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'MARINA SABÓIA',
        "reserva": 'JULIANA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'CLEMILDE MARTINS',
        "reserva": 'INGRID SANTOS',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'REGINA CONRADI',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNÊS CORSO',
        "reserva": 'FRANCIELE CARVALHO',
        "motivo": 'ATESTADO CIRURGICO',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'TERESA CANHADA',
        "reserva": 'JÉSSICA TRINDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'JANAÍNA RIBEIRO DE ASSIS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'MELVIN JONNES',
        "reserva": 'CAROLINA DANDARA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'MARISA ARRUDA',
        "reserva": 'PAULO AQUINO',
        "motivo": 'ATESTADO ATÉ DIA 06.05',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'JEFFERSON',
        "local": 'EM TRABALHO E SABER',
        "reserva": 'LIMPEZA PESADA',
        "motivo": 'LIMPEZA PESADA',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'JÚNIOR ALVES',
        "local": 'EM TRABALHO E SABER',
        "reserva": 'LIMPEZA PESADA',
        "motivo": 'LIMPEZA PESADA',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'SECRETARIA - MORINGÃO',
        "reserva": 'LIMPEZA PESADA',
        "motivo": 'LIMPEZA PESADA',
        "obs": None
    },
    {
        "data": "05/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'SECRETARIA - MORINGÃO',
        "reserva": 'LIMPEZA PESADA',
        "motivo": 'LIMPEZA PESADA',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'JOSÉ GASPARINI',
        "reserva": 'SUELI RODRIGUES',
        "motivo": 'ATESTADO ATÉ HOJE',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'CORVETA',
        "reserva": 'LILIAN FERNANDES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSINÉIA MARTINIANO',
        "motivo": 'AFASTAMENTO',
        "obs": '90 DIAS'
    },
    {
        "data": "06/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA - BIBLIOTECA',
        "reserva": 'ELAINE POTIRA',
        "motivo": 'ATESTADO MÉDICO 15 DIAS',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'BEATRIZ DA SILVA CAMPOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'LUANA BONIFÁCIO',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'ROSÂNGELA BIRAL',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'JULIANO STINGHEN',
        "reserva": 'ADRIANA SILVA DOS SANTOS',
        "motivo": 'ATESTADO',
        "obs": '2 DIAS'
    },
    {
        "data": "06/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'VILMA ELISA',
        "reserva": 'LARISSA NATALINA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'LUIZ MARQUES CASTELO',
        "reserva": 'LUCILENE DE SOUZA',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'CECÍLIA ERMÍNIA',
        "reserva": 'ROSELI REIS',
        "motivo": 'PERÍODO DA TARDE',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'ABIQUEILA PEREIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNES CORSO',
        "reserva": 'FRANCIELE C. DE OLIVEIRA',
        "motivo": 'ATESTADO MÉDICO',
        "obs": '30 DIAS'
    },
    {
        "data": "06/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'TERESA CANHADA',
        "reserva": 'JÉSSICA TRINDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'HIKOMA UDIHARA',
        "reserva": 'LUANA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'JANAÍNA RIBEIRO DE ASSIS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'MELVIN JONNES',
        "reserva": 'CAROLINA DANDARA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "06/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'MARISA ARRUDA',
        "reserva": 'JONATHAS',
        "motivo": 'ATESTADO MÉDICO',
        "obs": '3 DIAS'
    },
    {
        "data": "07/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'WATER OKANO',
        "reserva": 'ROSÂNGELA GUSMÃO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'VILMA ELIZA',
        "reserva": 'LARISSA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSINÉIA MARTINIANO',
        "motivo": 'AFASTAMENTO',
        "obs": '90 DIAS'
    },
    {
        "data": "07/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SCHERER',
        "reserva": 'VAGA 44h EM ABERTO',
        "motivo": 'POSTO VAGO',
        "obs": 'NÃO COBRIU'
    },
    {
        "data": "07/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'SOLÂNGE DE ANDRADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'LUANA BONIFÁCIO',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'ROSÃNGELA BIRAL',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'BEATRIZ DA SILVA CAMPOS',
        "motivo": 'DEMISSÃO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'AMÉRICA SABINO',
        "reserva": 'GILVANETE COSTA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'CRAS - SUL B',
        "reserva": 'MÁRCIA FRANCISCA SILVA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'MARIA TERESA',
        "reserva": 'ADRIANA CRISTINA SOUZA',
        "motivo": 'MEIO PERÍODO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'CRISTIANE DOS SANTOS',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNÊS CORSO',
        "reserva": 'FRANCIELE CARVALHO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'TERESA CANHADA',
        "reserva": 'JÉSSICA TRINDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'VALÉRIA VERONESI',
        "reserva": 'LUZIA CAZARIN',
        "motivo": 'ATESTADO MÉDICO',
        "obs": '2 DIAS'
    },
    {
        "data": "07/05",
        "ausente": 'JANAÍNA RIBEIRO DE ASSIS',
        "local": 'JUSTA CAUSA',
        "reserva": 'JUSTA CAUSA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'MELVIN JONNES',
        "reserva": 'CAROLINA DANDARA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "07/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'MARIA CÂNDIDO PEIXOTO',
        "reserva": 'JERRI ADRIANI',
        "motivo": 'ATESTADO 15 DIAS',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'WATER OKANO',
        "reserva": 'ROSÂNGELA GUSMÃO',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSINÉIA MARTINIANO',
        "motivo": 'POSTO VAGO',
        "obs": '90 DIAS'
    },
    {
        "data": "08/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'VALÉRIA VERONESI',
        "reserva": 'ROSÂNGELA A. ROCHA',
        "motivo": 'CONSULTA AS 10H',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO INDIRETA',
        "reserva": 'RESCISÃO INDIRETA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'TJ LONDRINA',
        "reserva": 'SOLANGE ANDRADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'LUANA BONIFÁCIO',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'TJ LONDRINA',
        "reserva": 'ROSÃNGELA BIRAL',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'TJ LONDRINA',
        "reserva": 'BEATRIZ DA SILVA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'AMÉRICA SABINO',
        "reserva": 'GILVANETE COSTA',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'CRAS-SUL B',
        "reserva": 'MÁRCIA FRANCISCA SILVA',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'MARIA TERESA',
        "reserva": 'MARIA TEREZA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'TJ LONDRINA',
        "reserva": 'CRISTIANE DOS SANTOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNÊS CORSO',
        "reserva": 'FRANCIELE CARVALHO',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'TERESA CANHADA',
        "reserva": 'JÉSSICA TRINDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'VALÉRIA VERONESI',
        "reserva": 'LUZIA CAZARIN',
        "motivo": 'ATESTADO MÉDICO',
        "obs": '2 DIAS'
    },
    {
        "data": "08/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'MELVIN JONNES',
        "reserva": 'CAROLINA DANDARA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EURIDES CUNHA',
        "reserva": 'EDER ROMERO',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'SECRETARIA - PLANETÁRIO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "08/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'SECRETARIA - PLANETÁRIO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'SCHERER',
        "reserva": 'POSTO VAGO',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'HÉLVIO ESTEVES',
        "reserva": 'CLAUDIMARY REJIANE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSINÉIA MARTINIANO',
        "motivo": 'AFASTAMENTO 90 DIAS',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'VILMA ELIZA',
        "reserva": 'LARISSA NATALINA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'TJ CRIMINAL DE LONDRINA',
        "reserva": 'ABIQUEILA PEREIRA DA SILVA',
        "motivo": 'ACOMPANHOU FILHA',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'LUANA BONIFÁCIO',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'BEATRIZ DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'JULIANO STINGHEN',
        "reserva": 'DAIANA CRISTINA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'IGNÊS CORSO',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'RUTH LEMOS',
        "reserva": 'CARINA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'NOEMI  MALANGA',
        "reserva": 'LAIS CAVALCANTE',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'TJ CRIMINAL DE LONDRINA',
        "reserva": 'DOMINIQUE MARIA',
        "motivo": 'FÉRIAS',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'TEREZA CANHADA',
        "reserva": 'JÉSSICA TRINDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'EM FRANCISCO PEREIRA',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'CMEI TELMA CAVALIEIRI',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "11/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM EURIDES CUNHA',
        "reserva": 'EBED ROMERO',
        "motivo": 'DEMISSÃO',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'NAIR AUZI CORDEIRO',
        "reserva": 'AMANDA DE SOUZA',
        "motivo": 'ACOMPANHAR FILHA',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE CASTRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'VILMA ELIZA',
        "reserva": 'LARISSA NATALINA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'SOLANGE ANDRADE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'LUANA BONIFÁCIO',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'ROSÂNGELA BIRAL',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'JULIANO STINGHEN',
        "reserva": 'ADRIANA SILVA',
        "motivo": 'ATESTADO',
        "obs": '10 DIAS'
    },
    {
        "data": "12/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'IGNÊS CORSO',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'ATESTADO',
        "obs": '4 DIAS'
    },
    {
        "data": "12/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'E.M TEREZA CANHADAS',
        "reserva": 'MARCILENE DAS DORES DOS SANTOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'CARLOS DITZ',
        "reserva": 'TAMIRA RIBEIRO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'TJ CRIMINAL DE LONDRINA',
        "reserva": 'DOMINIQUE MARIA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'AMÉRICA SABINO',
        "reserva": 'JANAÍNA DE ASSIS',
        "motivo": 'ATESTADO',
        "obs": '2 DIAS'
    },
    {
        "data": "12/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'E.M TEREZA CANHADAS',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'E.M MARIA CANDIDA',
        "reserva": 'Jerri Adriane',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'CMEI TELMA CAVALIEIRI',
        "reserva": 'APOIO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'E.M EURIDES CUNHA',
        "reserva": 'EBED ROMERO',
        "motivo": 'DEMISSÃO',
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'SECRETARIA - PLANETÁRIO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "12/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'SECRETARIA - PLANETÁRIO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'GASPAR VELLOSO',
        "reserva": 'MARCIA ORTIZ',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'EMILY NATALY',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'JOAQUIM VICENTE CASTRO',
        "reserva": 'FALTANDO SERVENTE',
        "motivo": None,
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'NATÁLIA MOREIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'LUANA BONIFÁCIO',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'ROSÂNGELA BIRAL',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'E.M JULIANO STINGHEN',
        "reserva": 'ADRIANA SILVA DOS SANTOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'E.M IGNEZ CORSO',
        "reserva": 'CARINA SUZI',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'E.M TEREZA CANHADAS',
        "reserva": 'VANESSA GONÇALVES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'E.M EURIDES CUNHA',
        "reserva": 'KEILA MARQUES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FORUM CRIMINAL',
        "reserva": 'JENIFER FERNANDA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'E.M JOAQUIM VICENTE DE CASTRO',
        "reserva": 'FALTA DE SERVENTE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'E.M TEREZA CANHADAS',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'E.M MARIA CANDIDO PEIXOTO',
        "reserva": 'Jerri Adriane',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'E.M HAYDEE COLLI',
        "reserva": 'VALDETE APARECIDA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'E.M EURIDES CUNHA',
        "reserva": 'EBED ROMERO',
        "motivo": 'DEMISSÃO',
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'SECRETARIA - PLANETÁRIO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "13/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'SECRETARIA - PLANETÁRIO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'HELVIO ESTEVES',
        "reserva": 'CLAUDIMARY REJIANE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'ATESTADO MÉDICO',
        "reserva": 'ATESTADO MÉDICO',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSILEIDE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'JOAQUIM VICENTE CASTRO',
        "reserva": 'FALTANDO SERVENTE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'RESCISÃO DIRETA',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'NATÁLIA MOREIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'LUANA BONIFÁCIO',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'SOLANGE ANDRADE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'AMÉRICA SABINO',
        "reserva": 'DAYANE DOS SANTOS',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'IGNÊS CORSO',
        "reserva": 'CARINA SUZI',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'MERCEDES MARTINS',
        "reserva": 'MARINA FERNANDES',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'GENI FERREIRA',
        "reserva": 'MONICA JENNIFER',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FORUM CRIMINAL',
        "reserva": 'JENIFER FERNANDA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'JULIANO STINGHEN',
        "reserva": 'ADRIANA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'E.M TEREZA CANHADAS',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'FRANCISCO PEREIRA JR',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'E.M TELMA CAVALIERI',
        "reserva": 'PATRICIA LIMA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EURIDES CUNHA',
        "reserva": 'EBED ROMERO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'SECRETARIA - PLANETÁRIO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "14/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'SECRETARIA - PLANETÁRIO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'HELVIO ESTEVES',
        "reserva": 'CLAUDIMARY REJIANE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE CASTRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'E.M JOAQUIM VICENTE',
        "reserva": 'FALTANDO SERVENTE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'NATÁLIA MOREIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'LUANA BONIFÁCIO',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'SOLANGE ANDRADE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'E.M IGNEZ CORSO',
        "reserva": 'CARINA SUZI',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'E.M NAIR AUZI',
        "reserva": 'AMANDA DE SOUZA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'E.M NOEMIA MALANGA',
        "reserva": 'JULIANA APARECIDA',
        "motivo": 'ATESTADO 2 DIAS',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FORUM CRIMINAL DE LONDRINA',
        "reserva": 'JENIFER FERNANDA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'E.M JULIANO STINGHEN',
        "reserva": 'ADRIANA DA SILVA DOS SANTOS',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'E.M TEREZA CANHADAS',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'E.M MARIA CANDIDO PEIXOTO',
        "reserva": 'JERRY ANDRIANE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'SANDRA LEME',
        "reserva": 'CINTIA VALIN',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'PADRE ANCHIETA',
        "reserva": 'DOUGLAS MARTINES',
        "motivo": 'ATESTADO',
        "obs": '5 DIAS'
    },
    {
        "data": "15/05",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'SECRETARIA - PLANETÁRIO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "15/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'SECRETARIA - PLANETÁRIO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'E.M. RUTH LEMOS',
        "reserva": 'CARINA SOARES DA SILVA',
        "motivo": 'AT. MÉDICO DE 11 A 24/05',
        "obs": '14 DIAS'
    },
    {
        "data": "18/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSINÉIA MARTINIANO',
        "motivo": 'POSTO VAGO',
        "obs": '90 DIAS'
    },
    {
        "data": "18/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA - ASSIST. SOC.',
        "reserva": 'ANGELINA OLIV. DA SILVA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'RESCISÃO DIRETA',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'MARIA LÚCIA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'LUANA BONIFÁCIO',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'TJ CÍVIL DE LONDRINA',
        "reserva": 'CLÁUDIA B.',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'CARLOS DITZ',
        "reserva": 'ROSELENE BOLETE',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM JULIANO STINGHEN',
        "reserva": 'ADRIANA SILVA DOS SANTOS',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'SECRETARIA DA SAÚDE',
        "reserva": 'VANILDA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'CECÍLIA ERMÍNIA',
        "reserva": 'PAULA CAROLINA',
        "motivo": 'ATESTADO',
        "obs": '7 DIAS'
    },
    {
        "data": "18/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'TJ CRIMINAL DE LONDRINA',
        "reserva": 'JENNIFER FERNANDA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNEZ CORSO',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'ATESTADO',
        "obs": '14 DIAS'
    },
    {
        "data": "18/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'IRENE APARECIDA DA SILVA',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'FRANCISCO PEREIRA JÚNIOR',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'SÔNIA PARREIRA',
        "reserva": 'ELCIMARIA BALBINO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'E.M. PADRE ANCHIETA',
        "reserva": 'DOUGLAS MARTINES',
        "motivo": 'AT. MÉDICO DE 15 A 19/05',
        "obs": '5 DIAS'
    },
    {
        "data": "18/05",
        "ausente": 'JEFFERSON',
        "local": 'EM MÁBIO G. PALHANO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'JÚNIOR ALVES',
        "local": 'EM MÁBIO G. PALHANO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'EM MARIA TERESA',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "18/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'EM MARIA TERESA',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'EM VILMA RODR. ROMERO',
        "reserva": 'LUZINÉIA FURQUIM',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'E.M. RUTH LEMOS',
        "reserva": 'CARINA SOARES DA SILVA',
        "motivo": 'AT. MÉD. 11 A 24/05',
        "obs": '14 DIAS'
    },
    {
        "data": "19/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE CASTRO',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "19/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'EM CARLOS DIETZ',
        "reserva": 'RENATA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM DE LONDRINA',
        "reserva": 'CRISTIANE DOS SANTOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM DE LONDRINA',
        "reserva": 'INDIANARA COLTRO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'RODRIGO CEZAR',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM JULIANO STINGHEN',
        "reserva": 'ADRIANA SILVA DOS SANTOS',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'SECRETARIA DE SAÚDE',
        "reserva": 'VANILDA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'CECÍLIA HERMÍNIA',
        "reserva": 'ROSELI REIS DA COSTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO',
        "motivo": 'INTERNADO',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM DE  LONDRINA',
        "reserva": 'JENIFER FERNANDA',
        "motivo": 'DEMISSÃO',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNÊS CORSO ANDREAZZA',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'ATESTADO DE 14 DIAS',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'HIKOMA UDIHARA',
        "reserva": 'LAUANE SILVA',
        "motivo": 'ATESTADO DIAS 18 E 19',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'BARTOLOMEU DE GUSMÃO',
        "reserva": 'KELLY DIAS',
        "motivo": 'ATESTADO DIAS 19,20,21,22',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'EM SÔNIA PARREIRA DEBEI',
        "reserva": 'ELCIMARIA ALBINO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'E.M. PADRE ANCHIETA',
        "reserva": 'DOUGLAS MARTINES',
        "motivo": 'ATESTADO DIAS 15 A 19',
        "obs": '5 DIAS'
    },
    {
        "data": "19/05",
        "ausente": 'JEFFERSON',
        "local": 'EM MÁBIO G. PALHANO',
        "reserva": 'EM. NÍSSIA ROCHA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'JÚNIOR ALVES',
        "local": 'EM MÁBIO G. PALHANO',
        "reserva": 'EM. NÍSSIA ROCHA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'CRAS SUL E EM',
        "reserva": 'LIMPEZA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "19/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'CRAS SUL E EM',
        "reserva": 'LIMPEZA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO  VAGO',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'ATESTADO MÉDICO 1 DIA',
        "reserva": 'ATESTADO MÉDICO 1 DIA',
        "motivo": 'ATESTADO MÉDICO 1 DIA',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'EM RUTH LEMOS',
        "reserva": 'CARINA SOARES DA SILVA',
        "motivo": 'AT. MÉD. 11 A 24/05',
        "obs": '14 DIAS'
    },
    {
        "data": "20/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'ALINE CRISTINA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE CASTRO',
        "motivo": 'POSTO  VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "20/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA ASSIST. SOCIAL',
        "reserva": 'ANGELINA OLIVEIRA SILVA',
        "motivo": 'ATESTADO 18, 19 E 20.',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO  VAGO',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'MARIA EDUARDA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO  VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "20/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'EM VANDERLAINE',
        "reserva": 'ROSÂNGELA AP. DA SILVA',
        "motivo": 'DECLARAÇÃO ACOMP.',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'RODRIGO CEZAR',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM JULIANO STINGHEN',
        "reserva": 'ADRIANA DA SILVA',
        "motivo": 'ATESTADO 10 DIAS',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'SECRETARIA MUN. SAÚDE',
        "reserva": 'VANILDA APARECIDA',
        "motivo": 'ATESTADO DE 7 DIAS',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM CORVETA CAMAQUÃ',
        "reserva": 'GLÁUCIA REGINA',
        "motivo": 'ATESTADO DE 2 DIAS',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO',
        "motivo": 'INTERNADO',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'JENNIFER FERNANDA',
        "motivo": 'DEMISSÃO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "20/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNÊS CORSO ANDREAZZA',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'POSTO  VAGO',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO  VAGO',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM IRENE AP. DA SILVA',
        "reserva": 'APOIO',
        "motivo": 'ENTROU 8H',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'EM BARTOLOMEU DE GUSM.',
        "reserva": 'KELLY DIAS',
        "motivo": 'ASSUNTOS PESSOAIS',
        "obs": '19,20,21,22'
    },
    {
        "data": "20/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'EM GENI FERREIRA',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM HIKOMA UDIHARA',
        "reserva": 'LAUANA SILVA',
        "motivo": 'CONSULTA MÉDICA',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'JEFFERSON',
        "local": 'EM NÍSSIA ROCHA',
        "reserva": 'LIMPEZA PESADA',
        "motivo": 'LIMPEZA PESADA',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'JÚNIOR ALVES',
        "local": 'EM NÍSSIA ROCHA',
        "reserva": 'LIMPEZA PESADA',
        "motivo": 'LIMPEZA PESADA',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'SECRETARIA DE CULTURA',
        "reserva": 'REGINA APARECIDA DA SILVA',
        "motivo": 'PAGAR INSALUBRIDADE.',
        "obs": None
    },
    {
        "data": "20/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'CMEI VALÉRIA VERONESI',
        "reserva": 'COBRINDO MARIA AUGUSTA',
        "motivo": 'TRANSFERIDA',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO  VAGO',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'EM VILMA RODR. ROMERO',
        "reserva": 'LUZINÉIA FURQUIM',
        "motivo": 'POSTO  VAGO',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'EM RUTH LEMOS',
        "reserva": 'CARINA SOARES DA SILVA',
        "motivo": 'AT. MÉD. 11 A 24/05',
        "obs": '14 DIAS'
    },
    {
        "data": "21/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'EM EUGÊNIO BRUGIN',
        "reserva": 'MARIA CASTORINO RIBEIRO',
        "motivo": 'ATESATADO 20,21,22',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE CASTRO',
        "motivo": 'POSTO  VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "21/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA DE CULTURA',
        "reserva": 'REGINA AP. DA SILVA',
        "motivo": 'PAGAR INSALUBRIDADE.',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'CRISTIANE DOS SANTOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM CARLOS C. BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'ATESTADO DE 180 DIAS',
        "obs": 'CONTRATAR'
    },
    {
        "data": "21/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'SECRETARIA ASSIST. SOCIAL',
        "reserva": 'CÍNTIA GONZAGA',
        "motivo": 'ATESTADO 18,19,20,21',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM MAESTRE DE HELD',
        "reserva": 'OLGA ANGÉLICA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM AMÉRICA SABINO',
        "reserva": 'DAYANE DOS SANTOS MACEDO',
        "motivo": 'ATESTADO 20,21',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'SECRETARIA DE SAÚDE',
        "reserva": 'VANILDA APARECIDA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM CORVETA CAMAQUÃ',
        "reserva": 'GLÁUCIA REGINA',
        "motivo": 'ATESTADO DE 2 DIAS',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO',
        "motivo": 'INTERNADO',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'JENIFER FERNANDA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNÊS CORSO ANDREAZZA',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'ATESTADO DE 14 DIAS',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'IRENE APARECIDA',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'EM BARTOLOMEU GUSMÃO',
        "reserva": 'KELLY DIAS',
        "motivo": 'ASSUNTOS PESSOAIS',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'EM LAURA VIRGÍNIA',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM HIKOMA UDIHARA',
        "reserva": 'LUANA SILVA',
        "motivo": 'ATESTADO 20,21,22',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'JEFFERSON',
        "local": 'EM NÍSSIA ROCHA',
        "reserva": 'LIMPEZA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'JÚNIOR ALVES',
        "local": 'EM NÍSSIA ROCHA',
        "reserva": 'LIMPEZA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'SECRETARIA DE CULTURA',
        "reserva": 'REGINA APARECIDA DA SILVA',
        "motivo": 'PAGAR INSALUBRIDADE.',
        "obs": None
    },
    {
        "data": "21/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'CMEI VALÉRIA VERONESI',
        "reserva": 'COBRINDO MARIA AUGUSTA',
        "motivo": 'TRANSFERIDA',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO  VAGO',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'CMEI VALÉRIA VERONESI',
        "reserva": 'MARIA AUGUSTA MECCHI',
        "motivo": 'TRANSFERIDA',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'SELMA  DE JESUS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE CASTRO',
        "motivo": 'POSTO  VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "22/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA ASSIST. SOCIAL',
        "reserva": 'CÍNTIA GONZAGA CARVALHO',
        "motivo": 'ATESTADO 18,19,20,21,22',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'ANDRÉ GUSTAVO SENA',
        "local": 'EM VILMA RODRIGUES ROMERO',
        "reserva": 'LUZINÉIA FURQUIM',
        "motivo": 'POSTO  VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "22/05",
        "ausente": 'JACQUELINE AP. DE PAULA',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'CRISTIANE DOS SANTOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM CARLOS C. BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO  VAGO',
        "obs": 'CONTRATAR ?'
    },
    {
        "data": "22/05",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO',
        "motivo": 'INTERNADO',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'ROSANGELA BIRAL',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'CMEI NÍSSIA ROCHA',
        "reserva": 'VALQUÍRIA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM AMÉRCIA SABINO',
        "reserva": 'JANAÍNA DE ASSIS PEREIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'CMEI HELLENA OMETO',
        "reserva": 'ESTEFANI MORAIS',
        "motivo": 'ATESTADO 21,22',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'PAULA CAROLINA FERNANDES DE MOURA',
        "local": 'EM CECÍLIA HERMÍNIA',
        "reserva": 'ROSELI REIS DA COSTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'JENIFER FERNANDA',
        "motivo": 'DEMISSÃO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "22/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNÊS CORSO ANDREAZZA',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'ATESTADO DE 14 DIAS',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO  VAGO',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM JOSÉ GASPARINI - ANEXO',
        "reserva": 'RENATA FERREIRA',
        "motivo": 'LEVOU FILHA AO MÉDICO',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'EM BARTOLOMEU GUSMÃO',
        "reserva": 'KELLY DIAS',
        "motivo": 'ASSUNTOS PESSOAIS',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'E.M MARIA CANDIDO PEIXOTO',
        "reserva": 'JERRY ANDRIANE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM HIKOMA UDIHARA',
        "reserva": 'LAUANE SILVA',
        "motivo": 'ATESTADO 20, 21 E 22.',
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "22/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO  VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "25/05",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTOU',
        "reserva": 'FALTOU',
        "motivo": 'FALTOU',
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'CMEI VALÉRIA VERONESI',
        "reserva": 'MARIA AUGUSTA MECCHI',
        "motivo": 'TRANSFERIDA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO  VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "25/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'ABIQUEILA PEREIRA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSILEIDE DE CASTRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA ASSIST. SOCIAL',
        "reserva": 'CYNTIA GONZAGA CARVALHO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'RESCISÃO DIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "25/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'ATESTADO',
        "reserva": 'ATESTADO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO  VAGO',
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'MARIA EDUARDA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM CECÍLIA ERMÍNIA',
        "reserva": 'ROSELI REIS DA COSTA',
        "motivo": 'PERÍODO DA TARDE',
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM AMÉRICA SABINO',
        "reserva": 'JANAÍNA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'EM LUIS MARQUES CASTELO',
        "reserva": 'LUCILENE DE SOUZA VIEIRA',
        "motivo": 'ATESTADO ÓBITO DO PAI',
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM GENI FERREIRA',
        "reserva": 'MONNICA JHENNIFER',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO',
        "motivo": 'INTERNADO',
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FALTOU',
        "reserva": 'FALTOU',
        "motivo": 'FALTOU',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNÊS CORSO ANDREAZZA',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'ATESTADO DE 14 DIAS',
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTOU',
        "reserva": 'FALTOU',
        "motivo": 'FALTOU',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'EDUCIANDRA',
        "local": 'EM SAN IZIDRO',
        "reserva": 'CLAUDINÉIA M. DOS SANTOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'EM JULIANO STINGHEN',
        "reserva": 'ADRIANA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'EM HIKOMA UDIHARA',
        "reserva": 'ZILDA POTIL MAGALHÃES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'E.M IRENE APARECIDA',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'EM JOSÉ GASPARINI',
        "reserva": 'RENATA FERREIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'EM TELMA CAVALHERI',
        "reserva": 'PATRÍCIA DE LIMA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM HIKOMA UDIHARA',
        "reserva": 'LAUANE ISABELE DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'JEFFERSON',
        "local": 'EM MARI CARRERA',
        "reserva": 'LIMPEZA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'JÚNIOR ALVES',
        "local": 'EM MARI CARRERA',
        "reserva": 'LIMPEZA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'EM JULIANO STINGHEN',
        "reserva": 'ADRIANA DA SILVA',
        "motivo": 'PAGAR INSALUBRIDADE',
        "obs": None
    },
    {
        "data": "25/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'EM HIKOMA UDIHARA',
        "reserva": 'ZILDA POTIL MAGALHÃES',
        "motivo": 'PERÍODO DA TARDE',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "26/05",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'CMEI VALÉRIA VERONESI',
        "reserva": 'MARIA AUGUSTA MECCHI',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "26/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'ALINE CRISTINA RIBEIRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA LONDRINA',
        "reserva": 'ROSELEIDE CASTRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATADA'
    },
    {
        "data": "26/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'LARISSA FARIAS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'MARIA EDUARDA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM SÔNIA PARREIRA',
        "reserva": 'SIMONE JANUÁRIO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM JULIANO STINGHEN',
        "reserva": 'ADRIANA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'SECRETARIA ASSIST. SOCIAL',
        "reserva": 'CYNTIA GONZAGA CARVALHO',
        "motivo": 'ATESTADO DE 02 DIAS',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM GENI FERREIRA',
        "reserva": 'MÔNICA JENNIFER',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO',
        "motivo": 'INTERNADO',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNÊS CORSO ANDREAZZA',
        "reserva": 'FRANCIELE',
        "motivo": 'ATESTADO DE 14 DIAS',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'EDUCIANDRA',
        "local": 'EM HAYDEE COLLI MONTEIRO',
        "reserva": 'GILCINÉIA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM JOSÉ GASPARINI',
        "reserva": 'FAUSTO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'EM JOSÉ GASPARINI - ANEXO',
        "reserva": 'RENATA FERREIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'EM TELMA CAVALHERI',
        "reserva": 'PATRÍCIA DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'ATESTADO',
        "reserva": 'ATESTADO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'JEFFERSON',
        "local": 'EM CARLOS COSTA BRANCO',
        "reserva": 'TOLDOS',
        "motivo": 'APONTAMENTO IMR ABRIL',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'JÚNIOR ALVES',
        "local": 'EM CARLOS COSTA BRANCO',
        "reserva": 'TOLDOS',
        "motivo": 'APONTAMENTO IMR ABRIL',
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'CRAS SUL - B',
        "reserva": 'TERMINAR TRABALHO',
        "motivo": None,
        "obs": None
    },
    {
        "data": "26/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'EM CORVET CAMAQUÃ',
        "reserva": 'TIRAR LIMO DO CHÃO',
        "motivo": 'URGÊNCIA IMR DE JUNHO',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "27/05",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'EM. MALVINA POPI',
        "reserva": 'LAÍS BATISTA FERREIRA',
        "motivo": 'ATESTADO 1 DIA',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'CMEI VALÉRIA VERONESI',
        "reserva": 'MARIA AUGUSTA MECCHI',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "27/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'EM. VILMA RODRIGUES',
        "reserva": 'LUZINÉIA FURQUIM',
        "motivo": 'POSTO VAGO',
        "obs": 'COBRIU A TARDE'
    },
    {
        "data": "27/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA LONDRINA',
        "reserva": 'ROSELEIDE CASTRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'CMEI DURVALINA P. ASSIS',
        "reserva": 'ELAINE FERMINO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'HELLEN S. DOS SANTOS DA SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATADA'
    },
    {
        "data": "27/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'ATESTADO',
        "reserva": 'ATESTADO',
        "motivo": 'ATESTADO',
        "obs": 'ATESTADO 27,28'
    },
    {
        "data": "27/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CÍVIL',
        "reserva": 'MARIA  EDUARDA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM CARLOS DIETZ',
        "reserva": 'RENATA GARCIA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM JULIANO STINGHEN',
        "reserva": 'ADRINA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'EM MARINA SABÓIA',
        "reserva": 'JULIANA DA SILVA DIAS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM GENI FERREIRA',
        "reserva": 'MÔNICA JENNIFER',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO',
        "motivo": 'INTERNADO',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNÊS CORSO ANDREAZZA',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'ATESTADO DE 14 DIAS',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'EDUCIANDRA',
        "local": 'EM HAYDEE COLLI',
        "reserva": 'GILCINÉIA LILIANE',
        "motivo": 'ATESTADO 26 E 27',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM JOSÉ GASPARINI - ANEXO',
        "reserva": 'RENATA FERREIRA',
        "motivo": 'ATESTADO 10 DIAS',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'CMEI IOLANDA SALGADO',
        "reserva": 'MOACIR MONSATO',
        "motivo": 'ATESTADO 4 DIAS',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'EM TELMA CAVALHERI',
        "reserva": 'PATRÍCIA DE LIMA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM MARIA TERESA',
        "reserva": 'VILMA BRAGA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'RUTH LEMOS / MARISA ARRUDA',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "27/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'RUTH LEMOS / MARISA ARRUDA',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'EM HIKOMA UDIHARA',
        "reserva": 'ROSEMEIRE PEREIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'CMEI VALERIA VERONESI',
        "reserva": 'MARIA AUGUSTA MECCHI',
        "motivo": 'TRANSFERIDA',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'EM VILMA RODRIGUES',
        "reserva": 'LUZINEIA FURQUIM',
        "motivo": 'POSTO VAGO',
        "obs": 'SEM INSALUBRIDADE'
    },
    {
        "data": "28/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA LONDRINA',
        "reserva": 'ROSELEIDE CASTRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'EM MARIA SHIRLEY B. LIRA',
        "reserva": 'VANILCE CÍCERA',
        "motivo": 'COMPENSAR HR EXTRA',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'ATESTADO',
        "reserva": 'ATESTADO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'MARIA EDUARDA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'E.M MERCEDES MARTINS',
        "reserva": 'MARIA FERNANDES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM AMÉRICA SABINO',
        "reserva": 'DAIANE DOS SANTOS',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'EM MARINA SABÓIA',
        "reserva": 'LUCIANA LOURENÇA RIBEIRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM GENI FERREIRA',
        "reserva": 'MONICA JENNIFER',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO',
        "motivo": 'INTERNADO',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'EM IGNÊS CORSO ANDREAZZA',
        "reserva": 'FRANCIELE',
        "motivo": 'ATESTADO DE 14 DIAS',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM JOSÉ GASPARINI - ANEXO',
        "reserva": 'RENATA FERREIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'CMEI YOLANDA SALGADO',
        "reserva": 'MOACIR MOSATO',
        "motivo": 'ATESTADO 4 DIAS',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'EM TELMA CAVALHERI',
        "reserva": 'PATRÍCIA DE OLIVEIRA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM AMÉRICA SABINO',
        "reserva": 'WESLEY GONÇALVES',
        "motivo": 'ATESTADO 7 DIAS',
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'JEFFERSON',
        "local": 'EM MÁBIO G. PALHANO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'JÚNIOR ALVES',
        "local": 'EM MÁBIO G. PALHANO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'EM MARIA CANDIDO',
        "reserva": 'JENIFER SOUZA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "28/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'EM HIKOMA UDIHARA',
        "reserva": 'ZILDA MAGALHÃES',
        "motivo": None,
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "29/05",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'EM JULIANO STINGHEN',
        "reserva": 'ADRIANA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'EM MARINA SABÓIA',
        "reserva": 'LUCIANA LOURENÇO RIBEIRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'INSS',
        "obs": 'CONTRATAR'
    },
    {
        "data": "29/05",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE CASTRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'EM MARIA SHIRLEY B. LIRA',
        "reserva": 'VANÍLCE CÍCERA',
        "motivo": 'COMPENSAR HORAS EXTRAS',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCISÃO DIRETA',
        "reserva": 'RESCISÃO DIRETA',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATADA'
    },
    {
        "data": "29/05",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'SILVIA REGINA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'POSTO  VAGO',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'MARIA EDUARDA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM MERCEDES MARTINS',
        "reserva": 'MARINA FERNANDA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'E.M AMERICA SABINO',
        "reserva": 'DANIELLE PRUDENCIO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINEIA REGINA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM GENI FERREIRA',
        "reserva": 'MONICA JENNIFER',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO DA SILVA',
        "motivo": 'INTERNADO',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'IGNÊS CORSO ANDREAZZA',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'ATESTADO DE 14 DIAS',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'E.M GASPARINI',
        "reserva": 'RENATA FERREIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'CMEI YOLANDA SALGADO',
        "reserva": 'MOACIR MOSATO',
        "motivo": 'ATESTADO 4 DIAS',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'E.M TELMA CAVALIERI',
        "reserva": 'PATRICIA DE LIMA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'E.M AMERICA SABINO',
        "reserva": 'WESLEY GONÇALVES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'MARIA TERESA MELEIRO',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "29/05",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'MARCENARIA PML',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "01/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'GUARDA MUNICIPAL',
        "reserva": 'APARECIDA BORSUK DE ALENCAR',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'FRANCISCO SEIXAS',
        "reserva": 'EDNA AP. FERNANDES',
        "motivo": 'DECLARAÇÃO ACOMPANHANTE',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "01/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'ATESTADO MEDICO',
        "reserva": 'ATESTADO MEDICO',
        "motivo": 'ATESTADO MÉDICO OK.',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE DE CASTRO',
        "motivo": 'ATESTADO MEDICO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'MÁBIO GONÇALVES PALHANO',
        "reserva": 'RAQUEL DE FÁTIMA RODRIGUES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCISÃO INDIRETA',
        "reserva": 'RESCISÃO INDIRETA',
        "motivo": 'RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "01/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'ALINE DOS SANTOS HONORATO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'KARINA NUNES DA ROCHA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'MERCEDES MARTINS',
        "reserva": 'MARINA FERNANDES',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'IGNÊS CORSO',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINÉIA REGINA',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'CARLOS DIETZ',
        "reserva": 'ROSELENE GOMES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO',
        "motivo": 'INTERNADO SEM PREVISÃO DE ALTA',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'MARIA EDUARDA VENANCIO',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'JULIANO STINGHEN',
        "reserva": 'ADRIANA DA SILVA',
        "motivo": 'DECLARAÇÃO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'EDUCIANDRA DONAIRE',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'GIOVANA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LINENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM JOSE GASPARINI',
        "reserva": 'RENATA FERREIRA DA COSTA',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'FÁTIMA APARECIDA JARDIM',
        "local": 'FRANCISCO PEREIRA DE A. J.',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'TELMA CAVALHERI',
        "reserva": 'PATRÍCIA DE LIMA',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'AMÉRICA SABINO  COIMBRA',
        "reserva": 'WESLEY GONÇALVES',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'JEFFERSON',
        "local": 'CORVETA CAMAQUÃ',
        "reserva": 'LIMPESA PESADA',
        "motivo": 'SUPERVISOR VANDERSON',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'JÚNIOR ALVES',
        "local": 'CORVETA CAMAQUÃ',
        "reserva": 'LIMPESA PESADA',
        "motivo": 'SUPERVISOR VANDERSON',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'PADRE ANCHIETA',
        "reserva": 'LIMPESA PESADA',
        "motivo": 'SUPERVISOR LUIZ OTÁVIO',
        "obs": None
    },
    {
        "data": "01/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'PADRE ANCHIETA',
        "reserva": 'LIMPESA PESADA',
        "motivo": 'SUPERVISOR LUIZ OTÁVIO',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "02/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'AUTÓDROMO INT. LONDRINA',
        "reserva": 'LUCAS PEREIRA DE SOUZA',
        "motivo": 'TRANSFERÊNCIA PARA SECRETARIA DE OBRAS',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'CMEI VALÉRIA VERONESI',
        "reserva": 'ANA CAROLINA S. FELIPE',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATAR'
    },
    {
        "data": "02/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'ATESTADO MEDICO',
        "reserva": 'ATESTADO MEDICO',
        "motivo": 'ATESTADO MÉDICO 3 DIAS OK.',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE CASTRO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'GUARDA MUNICIPAL LDA',
        "reserva": 'APARECIDA BORSUK DE ALENCAR',
        "motivo": 'ATESTADO MÉDICO 4 DIAS',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "02/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'KARINA NUNES DA ROCHA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'MARIA EDUARDA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'FÓRUM CÍVIL',
        "reserva": 'RODRIGO CESAR',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'IGNÊS CORSO ANDREZZA',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINÉIA REGINA',
        "motivo": 'PAGAR GAF',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'CARLOS DIETZ',
        "reserva": 'ROSELENE GOMES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO',
        "motivo": 'INTERNADO SEM PREVISÃO DE ALTA',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CÍVIL',
        "reserva": 'DAIANE CAETANO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'JULIANO STINGHEN',
        "reserva": 'ADRIANA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'JOSÉ GASPARINI',
        "reserva": 'RENATA FERREIRA DA COSTA',
        "motivo": 'ATESTADO MÉDICO DE 05 DIAS',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'FRANCISCO PEREIRA DE A. J.',
        "reserva": 'APOIO',
        "motivo": 'TEVE CONSULTA AS 13H',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'TELMA CAVALHERI',
        "reserva": 'PATRÍCIA LIMA',
        "motivo": 'ATESTADO MÉDICO 30DIAS',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'IRMÃ MARIA NÍVEA',
        "reserva": 'POSTO VAGO',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'JEFFERSON',
        "local": 'APOIO NA BASE',
        "reserva": 'LIMPESA PESADA',
        "motivo": 'LAVAÇÃO DO ESTACIONAMENTO DE CAMINHÕES',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'JÚNIOR ALVES',
        "local": 'ATESTADO MEDICO',
        "reserva": 'ATESTADO MEDICO',
        "motivo": 'ATESTADO MÉDICO 01 DIA OK.',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'PADRE ANCHIETA',
        "reserva": 'LIMPESA PESADA',
        "motivo": 'LIMPEZA DE VENTILADORES',
        "obs": None
    },
    {
        "data": "02/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'PADRE ANCHIETA',
        "reserva": 'LIMPESA PESADA',
        "motivo": 'LIMPEZA DE VENTILADORES',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'INSS',
        "obs": 'CONTRATAR'
    },
    {
        "data": "03/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SEM INFORMAÇÃO DE ONDE ATUOU',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'CMEI VALÉRIA VERONESI',
        "reserva": 'ANA CAROLINA S. FELIPE',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'INSS',
        "obs": 'CONTRATAR'
    },
    {
        "data": "03/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE CASTRO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'GUARDA MUNICIPAL LDA',
        "reserva": 'APARECIDA BORSUK DE ALENCAR',
        "motivo": 'ATESTADO MÉDICO 4 DIAS',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "03/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'MARIA EDUARDA',
        "motivo": 'DEMISSÃO',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'ALINE DOS SANTOS HONORATO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'FÓRUM CÍVIL',
        "reserva": 'DAIANE CAETANO',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'IGNÊS CORSO ANDREAZZA',
        "reserva": 'CARINA SUZI FIDELIS',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINÉIA REGINA',
        "motivo": 'PAGAR GAF',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'LAURA VIRGÍNIA',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'VILMA ELIZA',
        "reserva": 'SELMA CRISTINA SALES',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CÍVIL',
        "reserva": 'RODRIGO CÉSAR',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'JULIANO STINGHEN',
        "reserva": 'ADRIANA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'IRENE APARECIDA DA SILVA',
        "reserva": 'APOIO',
        "motivo": 'CONSULTA MÉDICA A TARDE.',
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'FRANCISCO PEREIRA DE A. J.',
        "reserva": 'APOIO',
        "motivo": None,
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'TELMA CAVALHERI',
        "reserva": 'PATRÍCIA DE LIMA',
        "motivo": 'ATESTADO MÉDICO 30 DIAS. CONTRATAR',
        "obs": '30 DIAS'
    },
    {
        "data": "03/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'IRMÃ MARIA NÍVEA',
        "reserva": None,
        "motivo": 'POSTO VAGO',
        "obs": 'DESLIGADA'
    },
    {
        "data": "03/06",
        "ausente": 'JEFFERSON',
        "local": 'APOIO NA BASE',
        "reserva": 'SEM VEÍCULO',
        "motivo": None,
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'JÚNIOR ALVES',
        "local": 'APOIO NA BASE',
        "reserva": 'SEM VEÍCULO',
        "motivo": None,
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'CORVETA CAMAQUÃ',
        "reserva": 'VANDERSON',
        "motivo": None,
        "obs": None
    },
    {
        "data": "03/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'CORVETA CAMAQUÃ',
        "reserva": 'VANDERSON',
        "motivo": None,
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "08/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'MOACYR TEIXEIRA',
        "reserva": 'DORICA MARIA DA CONCEIÇÃO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "08/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'MARIA LÚCIA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE DE CASTRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA DE ASSIST. SOCIAL',
        "reserva": 'CYNTIA GONZAGA CARVALHO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "08/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL DE LONDRINA',
        "reserva": 'ABIQUEILA PEREIRA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMINAL DE LONDRINA',
        "reserva": 'ALINE CRISTINA RIBEIRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'SANDRA LEME',
        "reserva": 'SANDRA ANTUNES',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'MÁBIO GONÇALVES PALHANO',
        "reserva": 'ANDREA FERNANDES VELOSO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINÉIA REGINA DA SILVA',
        "motivo": 'ATESTADO 05 DIAS',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'CECÍLIA HERMÍNIA',
        "reserva": 'ROSELI REIS DA COSTA',
        "motivo": 'DECLARAÇÃO',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO',
        "motivo": 'INTERNADO SEM PREVISÃO DE ALTA',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'NOELLY FRANCINNE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'JULIANO STINGHEN',
        "reserva": 'ADRIANA SILVA DOS SANTOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'VALÉRIA VERONESI',
        "reserva": 'ANA CAROLINA FELIPE',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'IRENE APARECIDA DA SILVA',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'MARIA SHIRLEY BARNABÉ LIRA',
        "reserva": 'JANE FABRÍCIO',
        "motivo": 'COMPENSAÇÃO DE HORAS EXTRAS INDEVIDAS',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'TELMA CAVALHERI MOTTA',
        "reserva": 'PATRÍCIA LIMA DOS SANTOS',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'IRMÃ MARIA NÍVEA',
        "reserva": None,
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'JEFFERSON',
        "local": 'JOÃO XXIII',
        "reserva": 'LIMPEZA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'JÚNIOR ALVES',
        "local": 'JOÃO XXIII',
        "reserva": 'LIMPEZA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'CRAS SUL B',
        "reserva": 'LIMPEZA PESADA',
        "motivo": 'FALTOU',
        "obs": None
    },
    {
        "data": "08/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'EM WATER OKANO',
        "reserva": 'ALINE DAYANE DA SILVA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "09/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'ANTONIETA TRINDADE',
        "reserva": 'ZELIA MARIA SANTANA',
        "motivo": 'ATESTADO DE 03 DIAS',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "09/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'KÁTIA CRISTINA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE DE CASTRO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA DE ASSIST.SOCIAL',
        "reserva": 'CYNTIA GONZAGA CARVALHO',
        "motivo": 'ATESTADO DE 03 DIAS',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "09/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMNAL DE LONDRINA',
        "reserva": 'ABIQUEILA PEREIRA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMNAL DE LONDRINA',
        "reserva": 'SILVIA REGINA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'CLEMILDE MARTINS',
        "reserva": 'TAMIRES AZEVEDO',
        "motivo": 'ATESTADO DE 02 DIAS',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'JOAQUIM VICENTE DE CASTRO',
        "reserva": 'APARECIDA KETTI DE ALMEIDA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINÉIA REGINA DA SILVA',
        "motivo": 'ATESTADO 05 DIAS',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'CECÍLIA HERMÍNIA',
        "reserva": 'ROSELI COSTA',
        "motivo": 'ATESTADO DE 02 DIAS',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'ZUMBI DOS PALMARES',
        "reserva": 'GERALDO SEVERINO',
        "motivo": 'INTERNADO SEM PREVISÃO DE ALTA MÉDICA',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'IDALICE GONÇALVES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'JULIANO STINGHEN',
        "reserva": 'ADRIANA SILVA DOS SANTOS',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'VALÉRIA VERONESI',
        "reserva": 'ANA CAROLNA FELIPE',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'MARIA IRENE AP. TEODORO',
        "reserva": 'DEMISSÃO',
        "motivo": 'EJA DAS 9 AS 18:00 COBERTURA PARCIAL',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'FÁTIMA APARECIDA JARDIM',
        "local": 'ATESTADO',
        "reserva": 'ATESTADO',
        "motivo": 'ATESTADO MÉDICO 09,10 E 11.',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'TELMA CAVALHERI MOTTA',
        "reserva": 'PATRÍCIA LIMA',
        "motivo": 'ATESTADO MÉDICO DE 30 DIAS',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'IRMÃ MARIA NÍVEA',
        "reserva": None,
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": 'LIMPESA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": 'LIMPESA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'NORMAN PROCHET',
        "reserva": 'LIMPESA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "09/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'NORMAN PROCHET',
        "reserva": 'LIMPESA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "10/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'ANTONIETA TRINDADE',
        "reserva": 'ZELIA MARIA SANTANA',
        "motivo": 'ATESTADO DE 03 DIAS',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "10/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEIRUTA DE LONDRINA',
        "reserva": 'ROSELEIDE DE CASTRO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA DE ASSIST.SOCIAL',
        "reserva": 'CYNTIA GONZAGA CARVALHO',
        "motivo": 'ATESTADO DE 03 DIAS',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "10/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL DE LONDRINA',
        "reserva": 'ALICE CASTORINO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMINAL DE LONDRINA',
        "reserva": 'ABIQUEILA PEREIRA DA SILVA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'CARLOS DIETZ',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'VADERLAINE',
        "reserva": 'MAYARA ALVES DE PAULA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEIRUTA DE LONDRINA',
        "reserva": 'VALDINÉIA REGINA',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'CECÍLIA HERMÍNIA',
        "reserva": 'ROSELI REIS',
        "motivo": 'DECLARAÇÃO',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'VILMA ELISA',
        "reserva": 'SELMA CRISTINA SALES',
        "motivo": 'ATESTADO MÉDICO',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'MARIA EDUARDA VENÂNCIO',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'JULIANO STINGHEN',
        "reserva": 'ADRIANA SILVA DOS SANTOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'EDUCIANDRA DONAIRE',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'KAREN CABEÇA',
        "motivo": 'ATESTADO MÉDICO DE 02 DIAS',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'VALÉRIA VERONESI',
        "reserva": 'ANA CAROLNA FELIPE',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'MARIA IRENE AP. TEODORO',
        "reserva": 'DEMISSÃO',
        "motivo": 'EJA DAS 9 AS 18:00 COBERTURA PARCIAL',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'ATESTADO',
        "reserva": 'SEM COBERTURA',
        "motivo": 'ATESTADO MÉDICO DE 03 DIAS',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'TELMA CAVALHERI MOTTA',
        "reserva": 'PATRÍCIA SANTOS',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'IRMÃ MARIA NÍVEA',
        "reserva": 'DEMISSÃO',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": 'LIMPESA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": 'LIMPESA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'NORMAN PROCHET',
        "reserva": 'LIMPESA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "10/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'NORMAN PROCHET',
        "reserva": 'LIMPESA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "11/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'HORAS FALTAS',
        "reserva": 'HORAS FALTAS',
        "motivo": 'HORAS FALTAS',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'EM NAIR AUZI CORDEIRO',
        "reserva": 'AMANDA DE SOUZA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "11/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'DAIANE REGINA CAETANO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'LETÍCIA RODRIGUES FERREIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'VILMA ELIZA',
        "reserva": 'SELMA CRISTINA SALES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "11/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL DE LONDRINA',
        "reserva": 'ABIQUEILA PEREIR DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMINAL DE LONDRINA',
        "reserva": 'TAINARA JULIANA LEITE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'CECÍLIA HERMÍNIA',
        "reserva": 'ROSELI REIS DA COSTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'IGNÊS CORSO ANDREAZZA',
        "reserva": 'SANDRA SELMA CÂNDIDO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINEIA REGINA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'GENI FERREIRA',
        "reserva": 'MÔNICA DYENIFFER OLIVEIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'HELENA OMETTO TORRES',
        "reserva": 'ESTEFANI MORAES',
        "motivo": 'ATESTADO MÉDICO DE 03 DIAS',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CRIMINAL DE LONDRINA',
        "reserva": 'CRISTIANE DOS SANTOS PEREZ',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'JULIANO ESTINGHEN',
        "reserva": 'ADRIANA SILVA DOS SANTOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'VALÉRIA VERONESI',
        "reserva": 'ANA CAROLINA FELIPE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'MARIA IRENE AP. TEODORO',
        "reserva": None,
        "motivo": 'POSTO VAGO EJA DAS 9 AS 18:00 COBERTURA PARCIAL',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'FÁTIMA APARECIDA JARDIM',
        "local": 'ATESTADO',
        "reserva": 'SEM COBERTURA',
        "motivo": 'ATESTADO MÉDICO DE 03 DIAS',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'TELMA CAVALHERI DA MOTTA',
        "reserva": 'PATRICIA LIMA DOS SANTOS',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'IRMÃ MARIA NÍVEA',
        "reserva": None,
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'MARIA EDUARDA VENÂNCIO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "11/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "15/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'NAIR AUZI CORDEIRO',
        "reserva": 'AMANDA DE SOUZA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'INSS',
        "obs": 'CONTRATAR'
    },
    {
        "data": "15/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'ROSELEIDE DE CASTRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'JOSE GARCIA VILLAR',
        "reserva": 'TEREZA CRISTINA',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "15/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'KARINA NUNES',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'TAINARA JULIANA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'CLEMILDE MARTINS',
        "reserva": 'IVONE LÚCIO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'IGNÊZ CORSO',
        "reserva": 'FRANCIELE CARVALHO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'EM ZUMBI DOS PALMARES',
        "reserva": 'EDNA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM CECÍLIA HERMÍNIA',
        "reserva": 'JÚNIA RIBEIRO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM VILMA ELISA',
        "reserva": 'SELMA CRISTINA SALES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'CAROLINA IBIPIANO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'EM JULIANO STINGHEN',
        "reserva": 'ADRIANA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'CMEI VALÉRIA VERONESI',
        "reserva": 'ANA CAROLINA DIAS FELIPE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'JÉSSICA DE FREITAS',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'IDALINA APARECIDA BRAGATO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM MÁBIO G. PALHANO',
        "reserva": 'KELI ADELAIDE MODESTO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'EM VILMA RODRIGUES',
        "reserva": 'CRISTIANE ALVES',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'EM TELMA CAVALHERI',
        "reserva": 'PATRICIA LIMA DOS SANTOS',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM HAYDEE COLLI',
        "reserva": 'MICHELE MARCUCCI BALDI',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'EM NORMAN PROCHET',
        "reserva": 'ANEXO PÓS OBRA',
        "motivo": 'FORAM AO CENTRO DE FORM. GUARDA MUNUCIPAL A TARDE',
        "obs": None
    },
    {
        "data": "15/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'EM NORMAN PROCHET',
        "reserva": 'ANEXO PÓS OBRA',
        "motivo": 'FORAM AO CENTRO DE FORM. GUARDA MUNUCIPAL A TARDE',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "16/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'EM WATER OKANO',
        "reserva": 'LARISSA LAWANA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "16/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'MARIA LUCIA DE LIMA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'CRISTIANE DOS SANTOS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'EM JOSÉ GARCIA VILLAR',
        "reserva": 'TEREZA CRISTINA',
        "motivo": 'INSS',
        "obs": 'MATERNIDADE'
    },
    {
        "data": "16/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCISÃO INDIRETA',
        "reserva": 'RESCISÃO INDIRETA',
        "motivo": 'POSTO VAGO',
        "obs": 'CONTRATADA'
    },
    {
        "data": "16/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'TAINARA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'KARINA NUNES DA ROCHA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM CORVETA CAMAQUÃ',
        "reserva": 'LILIAN FERNANDA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM AMERICA SABINO',
        "reserva": 'NATHALIA BIANCA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'CRAS SUL-A',
        "reserva": 'NEUSA MARIA COSTA SALES',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM CAROLINA BENEDITA',
        "reserva": 'ELISE DE SOUZA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'VILMA ELIZA',
        "reserva": 'SELMA CRISTINA SALES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'CAROLINA IBIPIANO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'EM JULIANO STINGHEN',
        "reserva": 'ADRIANA SILVA DOS SANTOS',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'EM SAN IZIDRO',
        "reserva": 'ELAINE FRANCIELE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'JÉSSICA DE FREITAS',
        "local": 'CFGM - GUARDA MUNICIPAL',
        "reserva": 'ERICA ALVES BARBOSA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM MABIO GONCALVES',
        "reserva": 'KELI ADELAIDE MODESTO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'EM VILMA RODRIGUES',
        "reserva": 'CRISTIANE ALVES',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'CMEI IRMA MARIA NIVEA',
        "reserva": None,
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM HAYDEE COLLI',
        "reserva": 'MICHELE MARCUCCI',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "16/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "17/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'EM JOVITA KAISER',
        "reserva": 'JULIETA MARIA DE OLIVEIRA',
        "motivo": 'FALTA',
        "obs": 'OBITO DO PAI'
    },
    {
        "data": "17/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "17/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'TAINARA JULIANA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'EM JOSE GARCIA VILLAR',
        "reserva": 'TEREZA CRISTINA',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "17/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'CRISTIANE DOS SANTOS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM EURIDES CUNHA',
        "reserva": 'KEILA ADRIANE MARQUES',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM DR JOAQUIM VICENTE',
        "reserva": 'CLEONICE ROSALVO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINEIA REGINA DA SILVA',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM CORVETA CAMAQUÃ',
        "reserva": 'LILIAN FERNANDA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'VILMA ELISA COLOMBO',
        "reserva": 'SELMA CRISTINA LOPES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'NOELLY FRANCINNE',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'EM JULIANO STINGHEN',
        "reserva": 'ADRIANA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'CEMITERIO JARDIM DA SAUDADE',
        "reserva": 'ELIANA GONCALVES COIMBRA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM MABIO GONCALVES',
        "reserva": 'KELI ADELAIDE MODESTO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'EM VILMA RODRIGUES',
        "reserva": 'CRISTIANE ALVES',
        "motivo": 'INSS / A TARDE FOI AO IRMA MARIA NIVEA COBRIR POSTO VAGO',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'EM CARLOS DIETZ',
        "reserva": 'JESSICA RODRIGUES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM HAYDEE COLLI',
        "reserva": 'MICHELE MARCUCCI BALDI',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "17/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "18/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'EM PROF. JOVITA KAISER',
        "reserva": 'JULIETA MARIA DE OLIVEIRA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "18/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'TAINARA JULIANA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'EM JOSE GARCIA VILLAR',
        "reserva": 'TEREZA CRISTINA',
        "motivo": 'INSS',
        "obs": 'LIC.MATERN.'
    },
    {
        "data": "18/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "18/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'CRISTIANE DOS SANTOS',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'CFGM - GUARDA MUNICIPAL',
        "reserva": 'ERICA ALVES BARBOSA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM EURIDES CUNHA',
        "reserva": 'KEILA ADRIANE',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM AMERICA SABINO',
        "reserva": 'NATHALIA BIANCA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINEIA REGINA DA SILVA',
        "motivo": 'INSS',
        "obs": 'perguntar para ela'
    },
    {
        "data": "18/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'CEMITERIO JARDIM SAUDADE',
        "reserva": 'ELIANA GONCALVES',
        "motivo": 'FALTA',
        "obs": 'ver com jaquelina'
    },
    {
        "data": "18/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM CORVETA CAMAQUÃ',
        "reserva": 'LILIAN FERNANDA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'VILMA ELIZA',
        "reserva": 'SELMA CRISTINA SALES',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'CAROLINA IBIPIANO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'EM DIRCE DE ALMEIDA',
        "reserva": 'BRUNA THOMY',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'JESSICA DE FREITAS',
        "local": 'FÓRUM CÍVIL DE LONDRINA',
        "reserva": 'EDERSON LUIZ DA SILVA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM MABIO GONCALVES',
        "reserva": 'KELI ADELAIDE MODESTO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'EM CECILIA HERMINIA',
        "reserva": 'ROSELI REIS DA COSTA',
        "motivo": 'INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'CMEI IRMA MARIA NIVEA',
        "reserva": None,
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM HAYDEE COLLI',
        "reserva": 'MICHELE MARCUCCI BALDI',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "18/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "19/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'CMEI VALERIA VERONESI',
        "reserva": 'ROZANA REGINA',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "19/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'KAREN CABECA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'TAINARA JULIANA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'EM JOSE GARCIA VILLAR',
        "reserva": 'TEREZA CRISTINA',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "19/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'MARIA EDUARDA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'KELLEN CRISTINE DE OLIVEIRA',
        "motivo": 'REMANEJADA DE POSTO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM CECÍLIA HERMÍNIA',
        "reserva": 'ROSELI REIS',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM CLAUDIA RIZZI',
        "reserva": 'ROSANGELA JUSTINA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINEIA REGINA DA SILVA',
        "motivo": 'INSS',
        "obs": 'VER FERNANDO'
    },
    {
        "data": "19/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM CECÍLIA HERMÍNIA',
        "reserva": 'TAIS APARECIDA SANTANA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'VILMA ELIZA',
        "reserva": 'SELMA CRISTINA SALES',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'KAREN JHENIFER CABECA',
        "motivo": 'REMANEJADA DE POSTO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'EM ATANAZIO LEONEL',
        "reserva": 'JOSIANE RIBEIRO FROIS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'EM SAN IZIDRO',
        "reserva": 'ELAINE FRANCIELE',
        "motivo": 'ATESTADO',
        "obs": 'CATETERISMO'
    },
    {
        "data": "19/06",
        "ausente": 'GIOVANA DOS SANTOS',
        "local": 'FILIAL LONDRINA',
        "reserva": 'EDUCIANDRA DONAIRE',
        "motivo": 'REMANEJADA DE POSTO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'KELLEN CRISTINE DE OLIVEIRA',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'MARILDA TASSONI PEREIRA DE LIMA',
        "motivo": 'ATESTADO',
        "obs": 'VER FERNANDO'
    },
    {
        "data": "19/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'JÉSSICA DE FREITAS',
        "local": 'CTGM - GUARDA MUNICIPAL',
        "reserva": 'ERICA ALVES BARBOSA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM MABIO GONCALVES',
        "reserva": 'KELI ADELAIDE MODESTO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'FRANCISCO PEREIRA JUNIOR',
        "reserva": 'APOIO',
        "motivo": None,
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'CMEI IRMA MARIA NIVEA',
        "reserva": None,
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM HAYDEE COLLI MONTEIRO',
        "reserva": 'MICHELE MARCUCCI BALDI',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'JÚNIOR ALVES',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "19/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "22/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'CMEI VALERIA VERONESI',
        "reserva": 'ROZANA REGINA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "22/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'DECLARAÇÃO',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'FORUM CÍVIL LONDRINA',
        "reserva": 'LARISSA SILVA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA ASSIST. SOCIAL',
        "reserva": 'EMILY NATALY BARBOSA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FORUM CÍVIL LONDRINA',
        "reserva": 'ALINE DOS SANTOS HONORIO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'KELLEN CRISTINE DE OLIVEIRA',
        "motivo": 'REMANEJADA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM MARIA TEREZA',
        "reserva": 'CIBELE DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM ANDREA NUZZI',
        "reserva": 'MARIA DE LOURDES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINEIA REGINA DA SILVA',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM GENI FERREIRA',
        "reserva": 'CAMILA STEFANI',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM VILMA ELIZA',
        "reserva": 'SELMA CRISTINA SALES',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'KAREN JHENIFER DA SILVA',
        "motivo": 'REMANEJADA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'JESSICA DE FREITAS',
        "local": 'CTGM - GUARDA MUNICIPAL',
        "reserva": 'ERICA ALVES BARBOSA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'EM JULIANO STINGHEN',
        "reserva": 'CLAUDINEIA SOARES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'GIOVANA DA SILVA',
        "local": 'EM CECÍLIA HERMÍNIA',
        "reserva": 'JUNIA RIBEIRO DE NOVAES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'KELLEN CRISTINE DE OLIVEIRA',
        "local": 'EM TEREZA CANHADAS',
        "reserva": 'MARCILENE DAS DORES',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'EDUCIANDRA DA SILVA DONAIRE',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'GIOVANA DA SILVA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM MABIO GONCALVES',
        "reserva": 'KELI ADELAIDE MODESTO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'EM RUTH LEMOS',
        "reserva": 'RICARDO DOS SANTOS',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'EM GENI FERREIRA',
        "reserva": 'APOIO',
        "motivo": 'MEIO PERÍODO NO HIKOMA UDIHARA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM HAYDEE COLLI',
        "reserva": 'MICHELE MARCUCCI',
        "motivo": 'REMANEJADA',
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'JEFFERSON',
        "local": 'EM CARLOS KRAEMER',
        "reserva": 'LIMPEZA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'JÚNIOR ALVES',
        "local": 'EM CARLOS KRAEMER',
        "reserva": 'LIMPEZA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "22/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "23/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'EM NAIR AUZI',
        "reserva": 'AMANDA DE SOUZA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "23/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'EM HAYDEE COLLI MONTEIRO',
        "reserva": 'CRISTINA KEITTI DE OLIVEIRA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'GERALDA ALICREIA',
        "motivo": 'POSTO VAGO',
        "obs": 'VER FERNANDO'
    },
    {
        "data": "23/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'EM JOSE GARCIA VILLAR',
        "reserva": 'TEREZA CRISTINA',
        "motivo": 'LICENÇA INSS',
        "obs": 'VER JOAO'
    },
    {
        "data": "23/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "23/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FORUM CIVIL DE LONDRINA',
        "reserva": 'MARIA EDUARDA',
        "motivo": 'POSTO VAGO',
        "obs": 'VER FERNANDO'
    },
    {
        "data": "23/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'GIOVANA DA SILVA',
        "motivo": 'REMANEJADA',
        "obs": 'GAF'
    },
    {
        "data": "23/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM CECÍLIA HERMÍNIA',
        "reserva": 'ROSELI REIS DA COSTA',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM ANDREA NUZZI',
        "reserva": 'MARIA DE LOURDES',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINEIA REGINA DA SILVA',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM CARLOS DIETZ',
        "reserva": 'RENATA GARCIA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM VILMA ELIZA',
        "reserva": 'SELMA CRISTINA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'SECRETARIA ASSIST. SOCIAL',
        "reserva": 'EMILY NATALY BARBOSA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'KAREN JHENIFER DA SILVA',
        "motivo": 'REMANEJADA',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'GIOVANA DA SILVA',
        "local": 'EM CECÍLIA HERMÍNIA',
        "reserva": 'JUNIA RIBEIRO DE NOVAES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'KELLEN CRISTINE DE OLIVEIRA',
        "local": 'EM TEREZA CANHADAS',
        "reserva": 'MARCILENE DAS DORES',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'JÉSSICA DE FREITAS',
        "local": 'CTGM - GUARDA MUNICIPAL',
        "reserva": 'ERICA ALVES BARBOSA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'EDUCIANDRA DA SILVA DONAIRE',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'KELLEN CRISTINE DE OLIVEIRA',
        "motivo": 'REMANEJADA',
        "obs": 'GAF'
    },
    {
        "data": "23/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'EM VANDERLAINE',
        "reserva": 'MAYARA ALVES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM MABIO GONCALVES',
        "reserva": 'KELI ADELAIDE MODESTO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'CMEI VALERIA VERONESI',
        "reserva": 'LUZIA CAZARIN',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'EM SANDRA REGINA LEME',
        "reserva": 'CINTIA VALIM',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'EM HAYDEE COLLI MONTEIRO',
        "reserva": 'MICHELE MARCUCCI BALDI',
        "motivo": 'REMANEJADA',
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'JEFFERSON',
        "local": 'EM CARLOS KRAEMER',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'JÚNIOR ALVES',
        "local": 'EM CARLOS KRAEMER',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'CEMITERIO PADRE ANCHIETA',
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "23/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "24/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'EM NAIR AUZI',
        "reserva": 'AMANDA DE SOUZA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "24/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'VALERIA VERONESI',
        "reserva": 'CELIA REGINA MARQUES',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'GERALDA ALICREIA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'EM JOSE GARCIA VILLAR',
        "reserva": 'TEREZA CRISTINA',
        "motivo": 'LICENÇA INSS',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "24/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM DE LONDRINA',
        "reserva": 'POSTO VAGO',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'SCHERER AUTO PECAS',
        "reserva": 'KELLEN CRISTINE DE OLIVEIRA',
        "motivo": 'REMANEJADA',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'CLEMILDE DE MARTINI',
        "reserva": 'ROSELE GOMES DE LIMA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM AMERICA SABINO',
        "reserva": 'GILVANETE',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'CMEI VALERIA VERONESI',
        "reserva": 'ROZANA REGINA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINEIA REGINA DA SILVA',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM RUTH FERREIRA',
        "reserva": 'TERESINHA FATIMA DA SILVA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM VILMA ELIZA',
        "reserva": 'SELMA CRISTINA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'SECRETARIA ASSIST. SOCIAL',
        "reserva": 'EMILY NATALY BARBOSA',
        "motivo": 'FALTA',
        "obs": 'LUIZ'
    },
    {
        "data": "24/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'SCHERER AUTO PECAS',
        "reserva": 'KAREN JHENIFER DA SILVA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'GIOVADA DOS SANTOS',
        "local": 'EM CECÍLIA HERMÍNIA',
        "reserva": 'JUNIA RIBEIRO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'KELLEN CRISTINE DE OLIVEIRA',
        "local": 'EM TEREZA CANHADAS',
        "reserva": 'MARCILENE DAS DORES',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'JESSICA DE FREITAS',
        "local": 'EM MALVINA POPPI',
        "reserva": 'LAIS BATISTA FERREIRA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'EDUCIANDRA DA SILVA DONAIRE',
        "local": 'SCHERER AUTO PECAS',
        "reserva": 'GIOVANA DOS SANTOS',
        "motivo": 'REMANEJADA',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM MABIO GONCALVES',
        "reserva": 'KELI ADELAIDE MODESTO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'EM SAN IZIDRO',
        "reserva": None,
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'CMEI VALERIA VERONESI',
        "reserva": 'LUZIA CAZARIN',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": 'EQUIPE LIMPESA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": 'EQUIPE LIMPESA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'FALTA',
        "reserva": 'EQUIPE LIMPESA PESADA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "24/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'CEMITERIO PADRE ANCHIETA',
        "reserva": 'EQUIPE LIMPESA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "25/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'EM NAIR AUZI',
        "reserva": 'AMANDA DE SOUZA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "25/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'CEMITERIO JARDIM DA SAUDADE',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'FÓRUM CRIMINAL',
        "reserva": 'GERALDA ALICREIA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'SECRETARIA ASSIST. SOCIAL',
        "reserva": 'EMILY NATALY BARBOSA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "25/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FORUM CIVIL DE LONDRINA',
        "reserva": 'MARIA EDUARDA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'JÉSSICA DE FREITAS',
        "local": 'EM MALVINA POPPI',
        "reserva": 'LAIS BATISTA FERREIRA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'KELLEN CRISTINE DE OLIVEIRA',
        "motivo": 'REMANEJADA',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM SONIA PARREIRA',
        "reserva": 'APOIO',
        "motivo": 'APOIO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM AMERICA SABINO',
        "reserva": 'GILVANETE SIQUEIRA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'MARIA VANDA DA LUZ',
        "local": 'CMEI VALERIA VERONESI',
        "reserva": 'ROZANA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINEIA REGINA DA SILVA',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM CECÍLIA HERMÍNIA',
        "reserva": 'JUNIA RIBEIRO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM VILMA ELIZA',
        "reserva": 'SELMA CRISTINA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'KAREN JHENIFER DA SILVA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'EDUCIANDRA DA SILVA DONAIRE',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'GIOVANA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'GIOVANA DOS SANTOS',
        "local": 'EM ANDREA NUZZI',
        "reserva": 'MARIA DE LOURDES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'KELLEN CRISTINE DE OLIVEIRA',
        "local": 'EM VILMA ELIZA',
        "reserva": 'PRISCILA GOTCHALK',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM MABIO GONCALVES',
        "reserva": 'KELI ADELAIDE MODESTO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'SAN IZIDRO',
        "reserva": None,
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'EM MARIA TEREZA',
        "reserva": 'VILMA BRAGA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'JEFFERSON',
        "local": 'CAPSML',
        "reserva": 'EQUIPE DE LIMPEZA PESADA',
        "motivo": 'LIMPEZA DE TOLDO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'JÚNIOR ALVES',
        "local": 'CAPSML',
        "reserva": 'EQUIPE DE LIMPEZA PESADA',
        "motivo": 'LIMPEZA DE TOLDO',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "25/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": None,
        "reserva": None,
        "motivo": None,
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'ALESSANDRA DA SILVA CRUZ',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'AFASTADA',
        "obs": 'CONTRATAR'
    },
    {
        "data": "26/06",
        "ausente": 'ANDRÉ GUSTAVO SENNA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'ÂNGELA MARIA LOPES',
        "local": 'EM NAIR AUZI',
        "reserva": 'AMANDA DE SOUZA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'ANNA RITA DA SILVA',
        "local": 'INSS',
        "reserva": 'INSS',
        "motivo": 'LICENÇA MATERNIDADE ATÉ 20/07',
        "obs": 'CONTRATAR'
    },
    {
        "data": "26/06",
        "ausente": 'DAIANE APARECIDA R. DA SILVA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'ATESTADO MEDICO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'ELAINE R. MALACHINI HENRIQUES',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'GERALDA ALICREIA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'FLÁVIA PERES KERCHE DE MENEZES',
        "local": 'CEMITERIO PADRE ANCHIETA',
        "reserva": 'CLAUDENICE FERREIRA',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'HELLEN SAMARA DOS SANTOS SILVA',
        "local": 'RESCIÇÃO INDIRETA',
        "reserva": 'RESCIÇÃO INDIRETA',
        "motivo": 'PRISCILA FOI CONTRATADA NO LUGAR / RESCISÃO INDIRETA',
        "obs": 'CONTRATADA'
    },
    {
        "data": "26/06",
        "ausente": 'JACQUELINE APARECIDA DE PAULA',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'ALINE DOS SANTOS',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'LAÍS MIRANDA DA SILVEIRA',
        "local": 'EM. CARLOS COSTA BRANCO',
        "reserva": 'ELIZETE DE OLIVEIRA',
        "motivo": 'LICENÇA INSS 180 DIAS',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'LUCI FERNANDES DE SÁ ESTÉRCIO',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'KELLEN CRISTINE',
        "motivo": 'REMANEJADA',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'LUCIENE VIEIRA BOLETTI',
        "local": 'EM CLEMILDE MARTINI',
        "reserva": 'APOIO',
        "motivo": 'COBRIR HORAS FALTA',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'MARIA DE FÁTIMA S. P. DA SILVA',
        "local": 'EM AMERICA SABINO',
        "reserva": 'NATHALIA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'MARÍLIA DE OLIVEIRA BISPO',
        "local": 'PREFEITURA DE LONDRINA',
        "reserva": 'VALDINEIA REGINA',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'PAULA C. FERNANDES DE MOURA',
        "local": 'EM CECÍLIA HERMINIA',
        "reserva": 'JUNIA RIBEIRO',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'PRISCILA SILVA DE MENEZES',
        "local": 'EM VILMA ELIZA',
        "reserva": 'SELMA CRISTINA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'SAMONITA DA SILVA SANTOS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'SILVANA CRISTINA DOS SANTOS',
        "local": 'SCHERER AUTO PEÇAS',
        "reserva": 'KAREN JHENIFER DA SILVA',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'STHEFANE MAYARA MARTINS',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'SENTE DORES NAS COSTAS, MAS SEM ATESTADO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'JESSICA DE FREITAS',
        "local": 'FÓRUM CRIMINAL LONDRINA',
        "reserva": 'NOELLY FRANCINNE',
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'KELLEN CRISTINE DE OLIVEIRA',
        "local": 'EM VILMA ELIZA',
        "reserva": 'PRISCILA GOTCHALK',
        "motivo": 'ATESTADO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'GIOVANA DOS SANTOS',
        "local": 'EM ANDREA NUZZI',
        "reserva": 'MARIA DE LOURDES',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'BRUNA DANIELLY DA SILVA SANTOS',
        "local": 'LICENÇA MATERNIDADE',
        "reserva": 'LICENÇA MATERNIDADE',
        "motivo": 'LICENÇA MATERNIDADE',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'ELISÂNGELA APARECIDA DA SILVA',
        "local": 'EM MABIO GONCALVES',
        "reserva": 'KELI ADELAIDE MODESTO',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'FÁTIMA APARECIDA',
        "local": 'SAN IZIDRO',
        "reserva": None,
        "motivo": 'POSTO VAGO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'LUZIA DE OLIVEIRA',
        "local": 'CMEI VALERIA VERONESI',
        "reserva": 'LUZIA CAZARIN',
        "motivo": 'INSS',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'PAULO AQUINO DE ALMEIDA JÚNIOR',
        "local": 'HAYDEE COLLI',
        "reserva": 'MICHELE MARCUCCI',
        "motivo": 'REMANEJAMENTO',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'JEFFERSON',
        "local": None,
        "reserva": 'EQUIPE DE LIMPEZA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'JÚNIOR ALVES',
        "local": None,
        "reserva": 'EQUIPE DE LIMPEZA PESADA',
        "motivo": None,
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'CARLOS HENRIQUE SANTOS OLIVEIRA',
        "local": 'FALTA',
        "reserva": 'FALTA',
        "motivo": 'FALTA',
        "obs": None
    },
    {
        "data": "26/06",
        "ausente": 'LINCOLN GUSTAVO MENDES',
        "local": 'EM CARLOS DIETZ',
        "reserva": 'EQUIPE DE LIMPEZA PESADA',
        "motivo": 'LAVAÇÃO DE TOLDO',
        "obs": None
    },
]

with engine.connect() as conn:
    # Colaboradores
    colaboradores = conn.execute(text("SELECT id, nome FROM colaboradores")).fetchall()
    nomes_colab = {row[1]: row[0] for row in colaboradores}

    # Colaboradores
    locais = conn.execute(text("SELECT id, local FROM centro_de_custo")).fetchall()
    nomes_locais = {row[1]: row[0] for row in locais}

    def match_colaborador(nome_sujo, threshold=95):
        nome_sujo = nome_sujo.upper().strip()
        resultado = process.extractOne(nome_sujo, nomes_colab.keys(), scorer=fuzz.token_sort_ratio)
        if resultado and resultado[1] >= threshold:
            nome_match, score, _ = resultado
            return nomes_colab[nome_match], nome_match, score
        return 0, None, 0

    def match_local(local_sujo, threshold=95):
        local_sujo = local_sujo.upper().strip()
        resultado = process.extractOne(local_sujo, nomes_locais.keys(), scorer=fuzz.token_sort_ratio)
        if resultado and resultado[1] >= threshold:
            nome_match, score, _ = resultado
            return nomes_colab[nome_match], nome_match, score
        return 0, None, 0

    for item in historico:
        dia, mes = item.get("data").split("/")
        data = dt.now().replace(day=int(dia), month=int(mes))

        local = item.get("local")
        ausente = item.get("ausente")
        reserva = item.get("reserva")
        motivo = item.get("motivo")
        obs = item.get("obs")
        status = "approve"
        requisicao_id = 0

        ausente_id, ausente_nome, score_ausente = match_colaborador(str(ausente))
        reserva_id, nome_reserva, score_reserva = match_colaborador(str(reserva))
        local_id, nome_local, score_local = match_local(str(local))

        print(f"Cadastrando Historico - {ausente}")
        conn.execute(
            text(
                f"""INSERT INTO rp_historico(requisicao_id, reserva_id, ausente_id, cc, created_at, ended_at, status, obs, motivo)
                VALUES({requisicao_id}, {reserva_id}, {ausente_id}, {local_id}, '{data}', '{data}', '{status}', '{obs}', '{motivo}')"""
            )
        );
    conn.commit()