from flask import jsonify, request as rq
from models.cargos import Cargos
from models.centros_de_custo import CostCenters
from models.situacoes import Situations
from utils.safe_route import safe_route
from sqlalchemy import String, func, or_, cast
from models.colaboradores import Employees, db
from utils.filial_scope import apply_active_department_scope, apply_cost_center_scope
from utils.token import decode_token

class EmployeesService:
    def read(self):
        if str(rq.args.get("fields") or "").strip().lower() == "tm_ops":
            return self._read_tm_ops_lookup()
        search_fields = [
            Employees.nome,
            cast(Employees.matricula, String),
            Employees.cpf,
            Cargos.nome,
            Situations.tipo,
            CostCenters.local,
        ]

        bd = rq.args
        situation_id = bd.get("situacao", None)
        center_id = bd.get("centro_id", None) or bd.get("centro_custo_id", None)
        supervisor_id = bd.get("supervisor_id", None)
        public_lookup = str(bd.get("publico", "")).strip().lower() in {"1", "true", "sim"}
        require_center = str(bd.get("com_local", "")).strip().lower() in {"1", "true", "sim"}
        limit = bd.get("limit")
        search = bd.get("search")

        emp = (
            db.session.query(
                Employees.id,
                Employees.matricula,
                Employees.nome,
                Employees.data_admissao,
                Employees.centro_id,
                CostCenters.local.label("centro_local"),
                CostCenters.departamento,
                CostCenters.valor_diaria_glosa.label("valor_diaria_glosa"),
                Cargos.nome.label("cargo"),
                Situations.tipo.label("situacao"),
            )
            .select_from(Employees)
            .outerjoin(Cargos, Cargos.id == Employees.cargo)
            .outerjoin(Situations, Situations.id == Employees.situacao)
            .outerjoin(CostCenters, CostCenters.id == Employees.centro_id)
            .order_by(Employees.nome.asc())
        )
        emp = apply_active_department_scope(emp, Employees.centro_id)

        access_token = rq.headers.get("Access-Token")
        if access_token and not public_lookup:
            emp = apply_cost_center_scope(emp, Employees.centro_id, decode_token(access_token))
        elif supervisor_id and not public_lookup:
            try:
                emp = emp.filter(CostCenters.supervisor_id == int(supervisor_id))
            except (TypeError, ValueError):
                return jsonify("Supervisor inválido."), 400
        elif not public_lookup:
            # A tela pública não possui filial autenticada; o supervisor escolhido
            # é o contexto mínimo necessário para impedir uma consulta global.
            return jsonify([]), 200

        if center_id: emp = emp.filter(Employees.centro_id == int(center_id))
        if situation_id: emp = emp.filter(Situations.id == int(situation_id))
        if require_center: emp = emp.filter(CostCenters.id.isnot(None))
        if search: emp = emp.filter(or_(*[field.ilike(f"%{search}%") for field in search_fields]))
        if public_lookup:
            # O modo publico alimenta seletores globais de colaboradores e deve
            # abranger todas as situacoes, inclusive colaboradores demitidos.
            emp = emp.limit(min(int(limit or 50), 50))
        elif limit:
            emp = emp.limit(int(limit))
            
        emp = emp.all()  # Obtem tudo
        return jsonify([e._asdict() for e in emp]), 200

    def _read_tm_ops_lookup(self):
        """Busca leve e paginada usada pelos seletores do TM Ops."""
        try:
            page = max(int(rq.args.get("page", 1)), 1)
            per_page = min(max(int(rq.args.get("per_page", 20)), 1), 50)
        except (TypeError, ValueError):
            return jsonify("Paginação inválida."), 400

        query = db.session.query(
            Employees.id,
            Employees.matricula,
            Employees.nome,
        ).filter(Employees.situacao == 1)

        access_token = rq.headers.get("Access-Token")
        if not access_token:
            return jsonify("Token de acesso obrigatório."), 401
        query = apply_cost_center_scope(
            query, Employees.centro_id, decode_token(access_token)
        )

        requested_ids = []
        for value in str(rq.args.get("ids") or "").split(","):
            if value.strip().isdigit():
                requested_ids.append(int(value.strip()))
        if requested_ids:
            query = query.filter(Employees.id.in_(set(requested_ids)))
        else:
            search = str(rq.args.get("search") or "").strip()
            if search:
                pattern = f"{search}%"
                filters = [Employees.nome.ilike(pattern)]
                digits = "".join(character for character in search if character.isdigit())
                if digits:
                    if search.isdigit():
                        filters.append(Employees.matricula == int(search))
                    normalized_cpf = func.replace(
                        func.replace(func.replace(Employees.cpf, ".", ""), "-", ""),
                        " ",
                        "",
                    )
                    filters.append(normalized_cpf.like(f"{digits}%"))
                query = query.filter(or_(*filters))

        pagination = query.order_by(Employees.nome.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return jsonify({
            "items": [row._asdict() for row in pagination.items],
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }), 200

    @safe_route
    def create(self): ...

    @safe_route
    def update(self): ...

    @safe_route
    def delete(self): ...
