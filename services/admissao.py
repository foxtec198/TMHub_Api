from flask import jsonify, request as rq
from utils.safe_route import safe_route
from utils.check_field import check_field
from datetime import datetime as dt

from models.colaboradores import Employees
from models.cargos import Cargos
from models.centros_de_custo import CostCenters
from models.admissao import Vacancy, db

STATUS_VALIDOS = ("aberta", "entrevista", "certidoes_tj", "aguardando_aso", "unico", "concluido")

class VacancyService:
    def _lookup_employee(self, matricula):
        return (
            db.session.query(
                Employees.matricula,
                Employees.nome,
                Employees.carga_horaria,
                Cargos.nome.label("funcao"),
                CostCenters.id.label("centro_id"),
                CostCenters.departamento,
                CostCenters.local.label("centro_custo"),
            )
            .select_from(Employees)
            .join(Cargos, Cargos.id == Employees.cargo)
            .join(CostCenters, CostCenters.id == Employees.centro_id)
            .filter(Employees.matricula == str(matricula))
            .first()
        )

    def search(self):
        query = (rq.args.get("q") or "").strip()
        if len(query) < 2: return jsonify([]), 200

        termo = f"%{query}%"
        matches = (
            db.session.query(
                Employees.matricula,
                Employees.nome,
                Employees.carga_horaria,
                Cargos.nome.label("funcao"),
                CostCenters.id.label("centro_id"),
                CostCenters.departamento,
                CostCenters.local.label("centro_custo"),
            )
            .select_from(Employees)
            .join(Cargos, Cargos.id == Employees.cargo)
            .join(CostCenters, CostCenters.id == Employees.centro_id)
            .filter(db.or_(Employees.matricula.ilike(termo), Employees.nome.ilike(termo)))
            .order_by(Employees.nome)
            .limit(6)
            .all()
        )
        return jsonify([m._asdict() for m in matches]), 200

    def read(self):
        status = rq.args.get("status")
        departamento = rq.args.get("departamento")
        order = rq.args.get("order", "desc")

        query = Vacancy.query
        if status: query = query.filter(Vacancy.status == status)
        if departamento: query = query.filter(Vacancy.departamento == departamento)

        query = query.order_by(Vacancy.created_at.asc() if order == "asc" else Vacancy.created_at.desc())
        vagas = query.all()
        return jsonify([v.to_dict() for v in vagas]), 200

    @safe_route
    def create(self):
        body = rq.get_json()
        matricula = body.get("matricula")
        horario_trabalho = body.get("horario_trabalho")
        motivo_saida = body.get("motivo_saida")

        ok, error = check_field(matricula=matricula, horario_trabalho=horario_trabalho, motivo_saida=motivo_saida)
        if not ok: return jsonify(error), 400

        emp = self._lookup_employee(matricula)
        if not emp: return jsonify("Colaborador não encontrado na base"), 404

        nova_vaga = Vacancy(
            matricula=emp.matricula,
            colaborador=emp.nome,
            departamento=emp.departamento,
            centro_custo=emp.centro_custo,
            centro_id=emp.centro_id,
            funcao=emp.funcao,
            carga_horaria=emp.carga_horaria,
            horario_trabalho=horario_trabalho,
            motivo_saida=motivo_saida,
        )
        db.session.add(nova_vaga)
        db.session.commit()
        return jsonify("Vaga cadastrada com sucesso"), 201

    @safe_route
    def update(self):
        body = rq.get_json()
        id = body.get("id")

        ok, error = check_field(id=id)
        if not ok: return jsonify(error), 400

        vaga = Vacancy.query.filter_by(id=id).first()
        if not vaga: return jsonify("Vaga não encontrada"), 404

        novo_status = body.get("status")
        if novo_status and novo_status != vaga.status:
            if novo_status not in STATUS_VALIDOS: return jsonify("Status inválido"), 400

            if novo_status == "entrevista":
                entrevistador = body.get("entrevistador", vaga.entrevistador)
                entrevista_data = body.get("entrevista_data", vaga.entrevista_data)

                ok, error = check_field(entrevistador=entrevistador, entrevista_data=entrevista_data)
                if not ok: return jsonify("Informe a colaboradora responsável e a data/horário da entrevista"), 400

                vaga.entrevistador = entrevistador
                vaga.entrevista_data = entrevista_data

            vaga.status = novo_status

        campos = ("horario_trabalho", "motivo_saida", "entrevistador", "entrevista_data")
        for campo in campos:
            if campo in body: setattr(vaga, campo, body[campo])

        vaga.updated_at = dt.now()
        db.session.commit()
        return jsonify("Vaga atualizada com sucesso"), 200

    @safe_route
    def delete(self):
        id = rq.args.get("id")

        ok, error = check_field(id=id)
        if not ok: return jsonify(error), 400

        vaga = Vacancy.query.filter_by(id=id).first()
        if not vaga: return jsonify("Vaga não encontrada"), 404

        db.session.delete(vaga)
        db.session.commit()
        return jsonify("Vaga removida com sucesso"), 200
