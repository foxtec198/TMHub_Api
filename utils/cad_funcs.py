from os import getenv, path
from string import ascii_uppercase
from dotenv import load_dotenv
from openpyxl import load_workbook
from sqlalchemy import create_engine, text

from models.colaboradores import Employees

load_dotenv()
filename = "./static/assets/sheets/all_clbs.xlsx"
end = 5000
engine = create_engine(getenv("DB_URI"))

# Local do arquivo
file = path.join(filename)

# Confirma a existencia
if not path.exists(file): print("Não encontrada")

# Variaveis
sheet = load_workbook(file).active
init = 1
columns = {}
employees = []

# Itera sobre as letras do alfabeto para criar as colunas existentes
for letter in ascii_uppercase:
    value = sheet[f"{letter}{init}"].value
    if value != None:
        if value == "focargos_nome": columns[letter] = "cargo"
        elif value.lower() == "rg": pass
        else: columns[letter] = value.lower()  # Confirma se o valor nao é Nulo

# Itera sobre um numero especifico para criar o Obejto de funcionarios!
for i in range((init + 1), (end + init + 1)):
    person = {}
    for key in columns:
        value = sheet[f"{key}{i}"].value
        if value != None:
            if not "Total" in str(value):
                person[columns[key]] = value
    if person:
        employees.append(person)

def set_cargos():
    cargos = set()
    [cargos.add(c["cargo"]) for c in employees ]

    with engine.connect() as conn:
        for cargo in cargos: 
            cargoExists = conn.execute(text(f"SELECT id from cargos where nome = '{cargo}'")).first()
            if not cargoExists: conn.execute(text(f"INSERT INTO Cargos(nome, multa, active) VALUES ('{cargo}', 0, {True})"))
        conn.commit()
    print("Cadastrados")
    

# Itera sobre os Objetos e cadastra caso nao exista no banco!
for employee in employees:
    # Dados do funcionario
    codigo = employee["codigo"]
    nome = employee["nome"]
    centro_id = employee["centro"]
    data_admissao = employee["admissao"]
    situacao = employee["situacao"]
    cargo = employee["cargo"]
    
    with engine.connect() as conn:
        print(f"Iniciando Cadastro | {codigo} - {nome}")
        cargo_id = conn.execute(text(f"select id from cargos where nome = '{cargo}'")).first()[0]
        if not cargo_id: print("Cargo não cadastrado"); cargo_id = 0

        query_employee = conn.execute(text(f"SELECT id FROM colaboradores WHERE matricula = '{codigo}'")).first()

        if query_employee:
            conn.execute(text(f"""
                UPDATE Colaboradores 
                SET nome = '{nome}', centro_id = {centro_id},
                data_admissao = '{data_admissao}', cargo = {cargo_id}, situacao = {situacao}
                WHERE id = {query_employee[0]}
            """))
            continue
        
        conn.execute(
            text(
                f"""
                    INSERT INTO Colaboradores(matricula, nome, centro_id, data_admissao, cargo_id, situacao)
                    VALUES({codigo}, '{nome}', {centro_id}, '{data_admissao}', {cargo_id}, {situacao} )
                """
            )
        )
    conn.commit()