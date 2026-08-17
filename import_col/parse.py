# Rotinas de importação de colaboradores: análise de dados.
# Biblioteca padrão.
import re, json
# Dependências externas.
from bs4 import BeautifulSoup

with open('/mnt/user-data/uploads/cc.html', 'r', encoding='latin-1') as f:
    content = f.read()

soup = BeautifulSoup(content, 'html.parser')
rows = soup.find_all('tr')
print(len(rows))

current_cc = None
employees = []

for tr in rows:
    cells = tr.find_all(['td', 'th'])
    texts = [c.get_text(strip=True) for c in cells]
    joined = " ".join(t for t in texts if t)
    if not joined:
        continue
    if 'Centro de Custo:' in joined:
        vals = [t for t in texts if t and t != 'Centro de Custo:']
        if vals:
            current_cc = vals[-1]
        continue
    first_td = cells[0] if cells else None
    if first_td and first_td.name == 'td' and first_td.get('align', '').lower() == 'right' and first_td.get('colspan') == '2':
        vals = [c.get_text(strip=True) for c in cells]
        if len(vals) >= 9 and vals[0].isdigit():
            employees.append({
                'centro_custo': current_cc,
                'codigo': vals[0],
                'nome': vals[1],
                'cargo': vals[2],
                'cc_num': vals[3],
                'horas': vals[4],
                'admissao': vals[5],
                'situacao': vals[6],
                'cpf': vals[7],
                'salario': vals[8],
            })

situacoes = {
    "1": "Trabalhando",
    "2": "Afastado Direitos Integrais",
    "3": "Acid. Trabalho periodo superior a 15 dias",
    "4": "Servico Militar",
    "5": "Licenca maternidade",
    "6": "Doenca periodo superior a 15 dias",
    "7": "Licenca sem Vencimento",
    "8": "Demitido",
    "9": "Ferias",
    "10": "Novo afast. mesmo acid. trabalho",
    "11": "Antecipacao e/ou prorrogacao Licenca Maternidade",
    "12": "Novo afast. mesma doenca",
    "13": "Exercicio de mandato sindical",
    "14": "Aposent. por invalid. acidente de trabalho",
    "15": "Aposent. por invalid. doenca profissional",
    "16": "Aposent. por invalid. exceto acid. trab. e doenca profissional",
    "17": "Acid. Trabalho periodo igual ou inferior a 15 dias",
    "18": "Doenca periodo igual ou inferior a 15 dias",
    "19": "Aborto nao criminoso",
    "20": "Licenca maternidade adocao 1 ano",
    "21": "Licenca maternidade adocao 1 a 4 anos",
    "22": "Licenca maternidade adocao 4 a 8 anos",
    "24": "Outros motivos de afastamento",
    "90": "Suspensao contratual decorrente acao trabalhista por rescisao indireta",
    "91": "Suspensao contratual para inquerito de apuracao de falta grave",
}

records = []
for e in employees:
    records.append({
        "codigo": e["codigo"],
        "nome": e["nome"],
        "cargo": e["cargo"],
        "centro_custo": e["centro_custo"],
        "centro_custo_num": e["cc_num"],
        "horas_mensais": e["horas"],
        "data_admissao": e["admissao"],
        "situacao_codigo": e["situacao"],
        "situacao_descricao": situacoes.get(e["situacao"], None),
        "cpf": e["cpf"],
        "salario": e["salario"],
    })

output = {
    "empresa": "COSTA OESTE SERVICOS LTDA",
    "relatorio": "RELACAO DE EMPREGADOS II",
    "emissao": "01/07/2026",
    "total_empregados": len(records),
    "empregados": records,
}

print(len(records))
print(records[:3])

with open('/home/claude/employees.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
