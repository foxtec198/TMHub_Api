# Regras de negócio de planilhas.
# Dependências externas.
from openpyxl import load_workbook
# Biblioteca padrão.
from string import ascii_uppercase
from os import path
# Dependências externas.
from flask import jsonify, request
# Módulos internos da aplicação.
from utils.safe_route import safe_route
# Dependências externas.
from pandas import read_excel

# Módulos internos da aplicação.
from models.colaboradores import Employees, db
from models.supervisores import Supervisors
from models.centros_de_custo import CostCenters
from utils.filial_scope import is_admin

class WorkSheet:
    @safe_route
    def __updateEmployees__(self, token_data):
        """
        Só altere o end caso precise ler mais linhas!

        :return: Response: any, StatusCode: int
        """

        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar colaboradores."), 403

        # Body JSON and Vars
        body = request.get_json()
        filename = body.get("file")
        end = body.get("end", 5000)

        # Local do arquivo
        file = path.join(filename)

        # Confirma a existencia
        if not path.exists(file):
            return jsonify("Arquivo não encontrado"), 404

        # Variaveis
        sheet = load_workbook(file).active
        init = body.get("init", 4)
        columns = {}
        employees = []

        # Itera sobre as letras do alfabeto para criar as colunas existentes
        for letter in ascii_uppercase:
            value = sheet[f"{letter}{init}"].value
            if value != None:
                if value == "focargos_nome":
                    columns[letter] = "cargo"
                elif value.lower() == "rg":
                    pass
                else:
                    columns[letter] = value.lower()  # Confirma se o valor nao é Nulo

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

        # Itera sobre os Objetos e cadastra caso nao exista no banco!
        for employee in employees:
            # Dados do funcionario
            codigo = int(employee["codigo"])
            nome = employee["nome"]
            centro_id = employee["centro"]
            data_admissao = employee["admissao"]
            cargo = employee["cargo"]
            situacao = employee["situacao"]
            
            # Funcionario do banco
            query_employee = Employees.query.filter_by(id=codigo).first()
            if query_employee:
                # Nunca deixa uma carga antiga sobrescrever o vinculo mais
                # recente quando a mesma matricula aparece mais de uma vez.
                incoming_admission = (
                    data_admissao.date()
                    if hasattr(data_admissao, "date")
                    else data_admissao
                )
                current_admission = (
                    query_employee.data_admissao.date()
                    if hasattr(query_employee.data_admissao, "date")
                    else query_employee.data_admissao
                )
                if (
                    current_admission
                    and incoming_admission
                    and incoming_admission < current_admission
                ):
                    continue

                # Updates caso seja diferenciado
                if nome != query_employee.nome: query_employee.nome = nome
                if centro_id != query_employee.centro_id: query_employee.centro_id = centro_id
                if data_admissao != query_employee.data_admissao: query_employee.data_admissao = data_admissao
                if cargo != query_employee.cargo: query_employee.cargo = cargo
                if situacao != query_employee.situacao: query_employee.situacao = situacao
                continue
            
            new_employee = Employees(
                id=codigo,
                matricula=codigo,
                nome=nome,
                centro_id=centro_id,
                data_admissao=data_admissao,
                cargo=cargo,
                situacao=situacao,
            )
            db.session.add(new_employee)
        db.session.commit()
        
        return (
            jsonify(
                {
                    "msg": "Funcionarios atualizados com sucesso",
                    "funcionarios_obtidos": employees,
                }
            ),
            200,
        )

    @safe_route
    def __updateCosts__(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar centros de custo."), 403
        # Dados vindos do JSON
        body = request.get_json()
        filename = body.get("file")
        centro_id_column = body.get("centro_id_column", 1)
        dpto_column = body.get("dpto_column", 2)
        local_column = body.get("local_column", 3)
        supervisor_column = body.get("supervisor_column", 4)
        is_supervisor_text = body.get("is_supervisor_str", True)

        # Variaves
        file = path.join(filename)
        costs = []

        # Confirma a existencia
        if not path.exists(file):
            return jsonify("Arquivo não encontrado"), 404
        df = read_excel(file)

        # Itera sobre os valores da planilha
        for item in df.values:
            if is_supervisor_text: # Confirma se na planilha é o nome do Supervisor ou o ID
                query = (
                    Supervisors().query.filter_by(nome=item[supervisor_column]).first()
                )
                if not query:
                    return (
                        jsonify(
                            f"Supervisor não cadastrado - {item[supervisor_column]}, favor cadastrar e refazer a importação"
                        ),
                        404,
                    )

            supervisor = query.id if query else item[supervisor_column]

            cost = {
                "id": item[centro_id_column],
                "dpto": item[dpto_column],
                "local": item[local_column],
                "supervisor_id": int(supervisor),
            }
            costs.append(cost)

        cad = 0
        for cost in costs:
            new_cost = CostCenters(
                id=cost["id"],
                local=cost["local"],
                departamento=cost["dpto"],
                supervisor_id=cost["supervisor_id"],
            )
            db.session.add(new_cost)
            cad += 1

        db.session.commit()
        return jsonify(f"Total de {cad} importados com sucesso"), 201

    @safe_route
    def __updateSupervisors__(self, token_data):
        if not is_admin(token_data):
            return jsonify("Apenas administradores podem importar supervisores."), 403
        # Dados originados do JSON
        body = request.get_json()
        filename = body.get("file")
        column = body.get("column", 4)

        # Variaveis
        file = path.join(filename)
        supervisors = set()

        # Verificações
        if not path.exists(file):
            return jsonify("Arquivo não encontrado"), 404

        # Dataframe do excel
        df = read_excel(file)

        if df.empty:
            return jsonify("Nenhum dado de supervisor encontrado"), 404
        for item in df.values:
            supervisors.add(item[column])  # Adiciona os supervisores ao Set

        # Itera sobre o set de Sups e cria caso nao haja correspondencia
        criados = 0
        for sup in supervisors:
            print(sup)
            new_supervisor = Supervisors()
            if not new_supervisor.query.filter_by(nome=sup).first():
                new_supervisor.nome = sup
                db.session.add(new_supervisor)
                criados += 1

        db.session.commit()
        return (
            jsonify(
                f"Sucesso na importação, total de {criados} supervisores atualizados"
            ),
            201,
        )
