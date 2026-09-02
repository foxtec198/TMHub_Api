# Regras de negócio de estrutura.
# Dependências externas.
from flask import current_app, jsonify, request

# Módulos internos da aplicação.
from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.empresas import Company
from models.estrutura import StructureAsset, StructureLocation
from models.schedular_rotinas import SchedularRoutine, SchedularRoutineStructure
from models.schedular_tarefas import SchedularTask
from models.usuarios import Users
from services.tm_ops import TMOpsService
from utils.db import db
from utils.filial_scope import (
    apply_cost_center_scope,
    can_access_cost_center,
    can_access_supervisor_user,
    is_admin,
    supervisor_users_query,
)
from utils.safe_route import safe_route


def _text(value):
    return str(value or "").strip()


class StructureService:
    @safe_route
    def read(self, token_data):
        centers = (
            apply_cost_center_scope(CostCenters.query, CostCenters.id, token_data)
            .order_by(CostCenters.departamento, CostCenters.local)
            .all()
        )
        center_ids = [center.id for center in centers]
        locations = (
            StructureLocation.query
            .filter(StructureLocation.centro_custo_id.in_(center_ids))
            .order_by(StructureLocation.ordem, StructureLocation.nome)
            .all()
            if center_ids else []
        )
        assets = (
            StructureAsset.query
            .filter(StructureAsset.centro_custo_id.in_(center_ids))
            .order_by(StructureAsset.nome)
            .all()
            if center_ids else []
        )
        locations_by_center = {}
        assets_by_center = {}
        for item in locations:
            locations_by_center.setdefault(item.centro_custo_id, []).append(item.to_dict())
        for item in assets:
            assets_by_center.setdefault(item.centro_custo_id, []).append(item.to_dict())

        departments = {}
        for center in centers:
            department = str(center.departamento or "SEM DEPARTAMENTO")
            departments.setdefault(department, []).append({
                "id": center.id,
                "numero": center.centro_id,
                "contrato": center.local,
                "empresa_id": center.empresa_id,
                "empresa_nome": center.empresa.nome if center.empresa else "SEM EMPRESA",
                # O cadastro legado não define mais o responsável atual. Se o
                # backfill não encontrou usuario_id, o contrato fica sem
                # supervisor deliberadamente.
                "supervisor_usuario_id": center.supervisor_usuario_id,
                "supervisor_usuario_ids": [item.id for item in center.supervisores_usuarios],
                "supervisores": [{"id": item.id, "nome": item.nome} for item in center.supervisores_usuarios],
                "supervisor": ", ".join(item.nome for item in center.supervisores_usuarios) or "SEM SUPERVISOR",
                "locais": locations_by_center.get(center.id, []),
                "estrutura": self._location_tree(locations_by_center.get(center.id, [])),
                "ativos": assets_by_center.get(center.id, []),
            })
        return jsonify([
            {"departamento": department, "contratos": contracts}
            for department, contracts in departments.items()
        ])

    @staticmethod
    def _location_tree(items):
        by_parent = {}
        for item in items:
            by_parent.setdefault(item.get("parent_id"), []).append({**item, "filhos": []})
        for children in by_parent.values():
            children.sort(key=lambda row: (row.get("ordem", 0), row.get("nome", "")))
        def attach(nodes):
            for node in nodes:
                node["filhos"] = attach(by_parent.get(node["id"], []))
            return nodes
        return attach(by_parent.get(None, []))

    @safe_route
    def read_supervisors(self, token_data):
        center_id = request.args.get("centro_id", type=int)
        supervisors = supervisor_users_query(token_data, center_id).order_by(Users.nome).all()
        return jsonify([
            {"id": supervisor.id, "nome": supervisor.nome}
            for supervisor in supervisors
        ])

    @safe_route
    def update_contract_supervisor(self, center_id, token_data):
        center = db.session.get(CostCenters, center_id)
        if not center:
            return jsonify("Contrato não encontrado."), 404
        if not can_access_cost_center(token_data, center.id):
            return jsonify("Você não possui acesso à filial deste contrato."), 403

        body = request.get_json(silent=True) or {}
        values = body.get("supervisor_usuario_ids")
        if values is None and body.get("supervisor_usuario_id") not in (None, ""):
            # Compatibilidade temporária com clientes anteriores ao multivínculo.
            values = [body.get("supervisor_usuario_id")]
        if not isinstance(values, list) or not values:
            return jsonify("Informe ao menos um supervisor."), 400
        try:
            supervisor_user_ids = list(dict.fromkeys(int(value) for value in values))
        except (TypeError, ValueError):
            return jsonify("Informe supervisores válidos."), 400
        supervisors = Users.query.filter(
            Users.id.in_(supervisor_user_ids),
            db.func.upper(db.func.trim(Users.role)) == "SUPERVISOR",
        ).order_by(Users.nome).all()
        if len(supervisors) != len(supervisor_user_ids):
            return jsonify("Um ou mais supervisores não foram encontrados."), 404
        if any(not can_access_supervisor_user(token_data, item.id, center.id) for item in supervisors):
            return jsonify("Um ou mais supervisores não pertencem à filial deste contrato."), 403

        previous_supervisor_user_ids = [item.id for item in center.supervisores_usuarios]
        center.supervisores_usuarios = supervisors
        center.supervisor_usuario_id = supervisors[0].id
        db.session.commit()
        current_app.logger.info(
            "Supervisor do contrato alterado",
            extra={
                "centro_custo_id": center.id,
                "supervisores_usuarios_anteriores_ids": previous_supervisor_user_ids,
                "supervisores_usuarios_novos_ids": supervisor_user_ids,
                "alterado_por_usuario_id": token_data.get("id"),
            },
        )
        return jsonify({
            "message": "Supervisores alterados com sucesso.",
            "contrato": {
                "id": center.id,
                "supervisor_usuario_id": supervisors[0].id,
                "supervisor_usuario_ids": [item.id for item in supervisors],
                "supervisores": [{"id": item.id, "nome": item.nome} for item in supervisors],
                "supervisor": ", ".join(item.nome for item in supervisors),
            },
        })

    @safe_route
    def update_contract_company(self, center_id, token_data):
        if not is_admin(token_data):
            return jsonify("Somente administradores podem alterar a empresa de um contrato."), 403
        center = db.session.get(CostCenters, center_id)
        if not center:
            return jsonify("Contrato não encontrado."), 404

        body = request.get_json(silent=True) or {}
        try:
            company_id = int(body.get("empresa_id"))
        except (TypeError, ValueError):
            return jsonify("Informe uma empresa válida."), 400
        company = db.session.get(Company, company_id)
        if not company:
            return jsonify("Empresa não encontrada."), 404
        if not company.ativa:
            return jsonify("A empresa selecionada está inativa."), 409
        if company.id == center.empresa_id:
            return jsonify({"message": "O contrato já pertence a esta empresa."})

        duplicate_center = CostCenters.query.filter(
            CostCenters.empresa_id == company.id,
            CostCenters.centro_id == center.centro_id,
            CostCenters.id != center.id,
        ).first()
        if duplicate_center:
            return jsonify("Já existe um contrato com este número na empresa selecionada."), 409

        registrations = [
            registration for registration, in db.session.query(Employees.matricula)
            .filter(Employees.centro_id == center.id)
            .all()
        ]
        if registrations:
            duplicate_registration = Employees.query.filter(
                Employees.empresa_id == company.id,
                Employees.matricula.in_(registrations),
                Employees.centro_id != center.id,
            ).first()
            if duplicate_registration:
                return jsonify(
                    "Não é possível trocar a empresa: há matrícula duplicada na empresa de destino."
                ), 409

        previous_company_id = center.empresa_id
        center.empresa_id = company.id
        Employees.query.filter(Employees.centro_id == center.id).update(
            {Employees.empresa_id: company.id},
            synchronize_session=False,
        )
        db.session.commit()
        current_app.logger.info(
            "Empresa do contrato alterada",
            extra={
                "centro_custo_id": center.id,
                "empresa_anterior_id": previous_company_id,
                "empresa_nova_id": company.id,
                "alterado_por_usuario_id": token_data.get("id"),
            },
        )
        return jsonify({
            "message": "Empresa do contrato alterada com sucesso.",
            "contrato": {
                "id": center.id,
                "empresa_id": company.id,
                "empresa_nome": company.nome,
            },
        })

    @safe_route
    def create(self, token_data):
        body = request.get_json(silent=True) or {}
        kind = _text(body.get("tipo")).lower()
        try:
            center_id = int(body.get("centro_custo_id"))
        except (TypeError, ValueError):
            return jsonify("Selecione um contrato válido."), 400
        if not can_access_cost_center(token_data, center_id):
            return jsonify("Você não possui acesso à filial deste contrato."), 403
        if not db.session.get(CostCenters, center_id):
            return jsonify("Contrato não encontrado."), 404

        name = _text(body.get("nome"))
        if not name:
            return jsonify("Informe o nome."), 400
        description = _text(body.get("descricao")) or None

        if kind == "local":
            duplicate = StructureLocation.query.filter(
                StructureLocation.centro_custo_id == center_id,
                db.func.lower(StructureLocation.nome) == name.lower(),
            ).first()
            if duplicate:
                return jsonify("Este local já está cadastrado no contrato."), 409
            parent_id = body.get("parent_id") or None
            if parent_id:
                try:
                    parent_id = int(parent_id)
                except (TypeError, ValueError):
                    return jsonify("Estrutura pai invÃ¡lida."), 400
                parent = db.session.get(StructureLocation, parent_id)
                if not parent or parent.centro_custo_id != center_id:
                    return jsonify("A estrutura pai nÃ£o pertence a este contrato."), 400
            item = StructureLocation(
                centro_custo_id=center_id,
                parent_id=parent_id,
                ordem=int(body.get("ordem") or 0),
                nome=name.upper(),
                descricao=description,
            )
        elif kind == "ativo":
            category = _text(body.get("categoria"))
            if not category:
                return jsonify("Informe o tipo/categoria do ativo."), 400
            local_id = body.get("local_id") or None
            if local_id:
                try:
                    local_id = int(local_id)
                except (TypeError, ValueError):
                    return jsonify("Local inválido."), 400
                local = db.session.get(StructureLocation, local_id)
                if not local or local.centro_custo_id != center_id:
                    return jsonify("O local selecionado não pertence a este contrato."), 400
            patrimonio = _text(body.get("patrimonio")).upper()
            if patrimonio and StructureAsset.query.filter_by(patrimonio=patrimonio).first():
                return jsonify("Este patrimônio já está cadastrado."), 409
            item = StructureAsset(
                centro_custo_id=center_id,
                local_id=local_id,
                nome=name.upper(),
                categoria=category.upper(),
                patrimonio=patrimonio or "PENDENTE",
                descricao=description,
            )
            db.session.add(item)
            db.session.flush()
            if not patrimonio:
                item.patrimonio = f"TMH-{center_id}-{item.id:06d}"
        else:
            return jsonify("Escolha entre local ou ativo."), 400

        db.session.add(item)
        db.session.commit()
        return jsonify({"message": "Cadastro realizado com sucesso.", "item": item.to_dict()}), 201

    @safe_route
    def delete(self, token_data):
        body = request.get_json(silent=True) or {}
        kind = _text(body.get("tipo")).lower()
        try:
            item_id = int(body.get("id"))
        except (TypeError, ValueError):
            return jsonify("Registro inválido."), 400

        model = {"local": StructureLocation, "ativo": StructureAsset}.get(kind)
        if not model:
            return jsonify("Escolha entre local ou ativo."), 400
        item = db.session.get(model, item_id)
        if not item:
            return jsonify("Registro não encontrado."), 404
        if not can_access_cost_center(token_data, item.centro_custo_id):
            return jsonify("Você não possui acesso à filial deste contrato."), 403

        if kind == "local":
            now = TMOpsService._now()
            routines = SchedularRoutine.query.filter_by(local_id=item.id).all()
            handled_ids = set()
            for routine in routines:
                related = [routine]
                if not routine.rotina_pai_id:
                    related.extend(
                        SchedularRoutine.query.filter_by(
                            rotina_pai_id=routine.id,
                        ).all(),
                    )
                for current in related:
                    if current.id in handled_ids:
                        continue
                    TMOpsService._remove_routine_operationally(current, now)
                    handled_ids.add(current.id)

            # A routine may also be linked to this local as an additional
            # structure. Cancel its pending tasks and detach that link only.
            links = SchedularRoutineStructure.query.filter_by(
                estrutura_id=item.id,
            ).all()
            for link in links:
                TMOpsService._cancel_unfinished_tasks(
                    SchedularTask.query.filter(
                        SchedularTask.rotina_estrutura_id == link.id,
                    ),
                    now,
                )
                link.ativo = False
                link.estrutura_id = None

        db.session.delete(item)
        db.session.commit()
        return jsonify("Registro excluído com sucesso."), 200
    @safe_route
    def update_location(self, location_id, token_data):
        location = db.session.get(StructureLocation, location_id)
        if not location:
            return jsonify("Local nÃ£o encontrado."), 404
        if not can_access_cost_center(token_data, location.centro_custo_id):
            return jsonify("VocÃª nÃ£o possui acesso Ã  filial deste local."), 403
        body = request.get_json(silent=True) or {}
        parent_id = body.get("parent_id") or None
        if parent_id:
            try:
                parent_id = int(parent_id)
            except (TypeError, ValueError):
                return jsonify("Estrutura pai invÃ¡lida."), 400
            if parent_id == location.id:
                return jsonify("Uma estrutura nÃ£o pode ser pai dela mesma."), 400
            parent = db.session.get(StructureLocation, parent_id)
            if not parent or parent.centro_custo_id != location.centro_custo_id:
                return jsonify("A estrutura pai nÃ£o pertence ao mesmo contrato."), 400
            descendants = {location.id}
            pending = [location.id]
            while pending:
                child_ids = [row.id for row in StructureLocation.query.filter(StructureLocation.parent_id.in_(pending)).all()]
                descendants.update(child_ids)
                pending = child_ids
            if parent_id in descendants:
                return jsonify("NÃ£o Ã© possÃ­vel criar ciclo na hierarquia."), 400
        location.parent_id = parent_id
        if "ordem" in body:
            try:
                location.ordem = int(body.get("ordem"))
            except (TypeError, ValueError):
                return jsonify("Ordem invÃ¡lida."), 400
        if body.get("nome"):
            location.nome = _text(body.get("nome")).upper()
        db.session.commit()
        return jsonify({"message": "Estrutura atualizada com sucesso.", "item": location.to_dict()})
