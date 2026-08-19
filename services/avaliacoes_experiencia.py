# Regras de negócio das avaliações do período de experiência.
from collections import Counter
from datetime import date, datetime as dt, time, timedelta
from io import BytesIO
from pathlib import Path
from os import getenv
from shutil import copyfile
from uuid import uuid4
from zoneinfo import ZoneInfo

from flask import jsonify, request, send_file
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from sqlalchemy import func
from werkzeug.utils import secure_filename

from models.avaliacoes_experiencia import ExperienceEvaluation
from models.cargos import Cargos
from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.controle_faltas import AbsenceControl
from models.medidas_disciplinares import DisciplinaryMeasure
from models.supervisores import Supervisors
from models.usuarios import Users
from utils.db import db
from utils.filial_scope import apply_cost_center_scope, can_access_supervisor, is_admin
from utils.permissions import has_permission
from utils.safe_route import safe_route


SAO_PAULO = ZoneInfo("America/Sao_Paulo")
EXPERIENCE_DAYS = 90
OPEN_TASK_DAYS_BEFORE_END = 20
SUPERVISOR_DEADLINE_HOURS = 48

COMPETENCIES = (
    "adaptacao_local_trabalho",
    "iniciativa_interesse",
    "relacionamento_interpessoal",
    "capacidade_aprendizagem",
    "produtividade",
)
COMPETENCY_LABELS = {
    "adaptacao_local_trabalho": "Adaptação ao local de trabalho",
    "iniciativa_interesse": "Iniciativa e interesse",
    "relacionamento_interpessoal": "Relacionamento interpessoal",
    "capacidade_aprendizagem": "Capacidade de aprendizagem",
    "produtividade": "Produtividade",
}
RATING_LABELS = {
    "nao_atende": "Não atende",
    "atende_parcial": "Atende parcialmente",
    "atende": "Atende",
}
PROFILE_LABELS = {
    "incompativel": "Perfil incompatível; inviável a permanência.",
    "bom_desenvolvivel": "Bom perfil; pode ser desenvolvido para permanecer.",
    "excelente": "Excelente contratação.",
}
DECISION_LABELS = {
    "demitir": "Demitir",
    "efetivar": "Efetivar",
    "prorrogar": "Prorrogar",
}
OPEN_STATUSES = {"aberta", "em_preenchimento", "atrasada"}
ADMIN_EDITABLE_STATUSES = {
    "aberta", "em_preenchimento", "atrasada", "aguardando_rh", "concluida"
}
EXPERIENCE_EVALUATION_TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "avaliacao_periodo_experiencia.pdf"
)
PDF_RENDER_DPI = 200
PDF_PAGE_WIDTH = 595.28
PDF_PAGE_HEIGHT = 841.89
EXPERIENCE_SIGNATURE_DIR = Path(
    getenv("EXPERIENCE_SIGNATURE_DIR")
    or Path(__file__).resolve().parents[1] / "storage" / "avaliacoes_experiencia"
)
REGISTERED_RH_SIGNATURE_DIR = Path(
    getenv("REGISTERED_RH_SIGNATURE_DIR")
    or Path(__file__).resolve().parents[1] / "assets" / "assinaturas_rh"
)
MAX_EXPERIENCE_SIGNATURE_SIZE = 2 * 1024 * 1024
SIGNATURE_EXTENSION = ".png"


def _as_date(value):
    if isinstance(value, dt):
        return value.date()
    return value


def _date_iso(value):
    return value.isoformat() if value else None


def _datetime_iso(value):
    return value.isoformat() if value else None


def _date_br(value):
    """Converte datas persistidas para a leitura brasileira no formulário."""
    value = _as_date(value)
    if isinstance(value, str):
        try:
            value = dt.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return value
    return value.strftime("%d/%m/%Y") if isinstance(value, date) else "-"


def _download_filename(name, code):
    """Monta um nome de download legível e seguro para diferentes sistemas."""
    forbidden = '\\/:*?"<>|'
    normalized_name = " ".join(str(name or "COLABORADOR").upper().split())
    normalized_name = "".join(
        " " if character in forbidden or ord(character) < 32 else character
        for character in normalized_name
    )
    normalized_name = " ".join(normalized_name.split()) or "COLABORADOR"
    normalized_code = "".join(
        character for character in str(code or "SEM_CODIGO")
        if character not in forbidden and ord(character) >= 32
    )
    return f"{normalized_name} - {normalized_code or 'SEM_CODIGO'}.pdf"


class ExperienceEvaluationService:
    """Orquestra a abertura, avaliação, conferência e exportação em PDF."""

    @staticmethod
    def _previous_business_day(reference_date):
        """Antecipar sábado e domingo para a sexta-feira imediatamente anterior."""
        while reference_date.weekday() >= 5:
            reference_date -= timedelta(days=1)
        return reference_date

    @classmethod
    def _period_dates(cls, admission_date):
        """Mantém a mesma regra de 90 dias já usada no módulo de rescisões."""
        end_date = admission_date + timedelta(days=EXPERIENCE_DAYS - 1)
        business_reference = cls._previous_business_day(end_date)
        opening_date = cls._previous_business_day(
            business_reference - timedelta(days=OPEN_TASK_DAYS_BEFORE_END)
        )
        return end_date, business_reference, opening_date

    @staticmethod
    def _deadline(opening_date, business_reference):
        opened_at = dt.combine(opening_date, time.min, tzinfo=SAO_PAULO)
        deadline = opened_at + timedelta(hours=SUPERVISOR_DEADLINE_HOURS)
        last_possible = dt.combine(business_reference, time.max, tzinfo=SAO_PAULO)
        return min(deadline, last_possible)

    @staticmethod
    def _history_snapshot(employee_id):
        """Consolida apenas contagens, sem copiar detalhes sensíveis para a tarefa."""
        disciplinary_rows = (
            db.session.query(DisciplinaryMeasure.tipo, func.count(DisciplinaryMeasure.id))
            .filter(DisciplinaryMeasure.colaborador_id == employee_id)
            .group_by(DisciplinaryMeasure.tipo)
            .all()
        )
        disciplinary = dict(disciplinary_rows)

        absence_rows = (
            db.session.query(
                AbsenceControl.tipo_ausencia,
                AbsenceControl.classificacao,
                func.count(AbsenceControl.id),
            )
            .filter(AbsenceControl.colaborador_id == employee_id)
            .group_by(AbsenceControl.tipo_ausencia, AbsenceControl.classificacao)
            .all()
        )
        totals = Counter()
        by_type = Counter()
        by_classification = Counter()
        for absence_type, classification, quantity in absence_rows:
            quantity = int(quantity or 0)
            totals["total"] += quantity
            by_type[str(absence_type or "nao_informado")] += quantity
            by_classification[str(classification or "em_analise")] += quantity

        return {
            "advertencias": int(disciplinary.get("advertencia", 0)),
            "suspensoes": int(disciplinary.get("suspensao", 0)),
            "ausencias": {
                "total": totals["total"],
                "por_tipo": dict(by_type),
                "por_classificacao": dict(by_classification),
            },
        }

    @staticmethod
    def _employee_query(token_data=None):
        query = (
            db.session.query(
                Employees,
                CostCenters.local.label("centro_custo_nome"),
                CostCenters.departamento.label("departamento"),
                CostCenters.supervisor_id.label("supervisor_id"),
                Supervisors.nome.label("supervisor_nome"),
                Cargos.nome.label("cargo_nome"),
            )
            .join(CostCenters, CostCenters.id == Employees.centro_id)
            .join(Supervisors, Supervisors.id == CostCenters.supervisor_id)
            .outerjoin(Cargos, Cargos.id == Employees.cargo)
            .filter(Employees.situacao == 1, Employees.data_admissao.isnot(None))
        )
        return (
            apply_cost_center_scope(query, Employees.centro_id, token_data)
            if token_data is not None
            else query
        )

    @classmethod
    def _create_evaluation(cls, employee_row, opening_date, end_date, business_reference):
        employee = employee_row.Employees
        evaluation = ExperienceEvaluation(
            colaborador_id=employee.id,
            supervisor_id=employee_row.supervisor_id,
            data_fim_experiencia=end_date,
            data_referencia_util=business_reference,
            aberta_em=dt.combine(opening_date, time.min, tzinfo=SAO_PAULO),
            prazo_supervisor_em=cls._deadline(opening_date, business_reference),
            competencias={},
        )
        db.session.add(evaluation)
        return evaluation

    @classmethod
    def process_pending_tasks(cls, reference_date=None):
        """Cria tarefas elegíveis uma única vez; seguro para execução recorrente."""
        today = reference_date or dt.now(SAO_PAULO).date()
        created = 0
        skipped_without_supervisor = 0

        for employee_row in cls._employee_query().all():
            admission = _as_date(employee_row.Employees.data_admissao)
            if not admission:
                continue
            end_date, business_reference, opening_date = cls._period_dates(admission)
            if today < opening_date or today > end_date:
                continue

            existing = ExperienceEvaluation.query.filter_by(
                colaborador_id=employee_row.Employees.id,
                data_fim_experiencia=end_date,
            ).first()
            if existing:
                continue
            if not employee_row.supervisor_id:
                skipped_without_supervisor += 1
                continue

            cls._create_evaluation(employee_row, opening_date, end_date, business_reference)
            created += 1

        if created:
            db.session.commit()
        cls._refresh_overdue(commit=True)
        return {"criadas": created, "sem_supervisor": skipped_without_supervisor}

    @staticmethod
    def _refresh_overdue(commit=False):
        now = dt.now(SAO_PAULO)
        overdue = ExperienceEvaluation.query.filter(
            ExperienceEvaluation.status.in_(("aberta", "em_preenchimento")),
            ExperienceEvaluation.prazo_supervisor_em < now,
        ).all()
        for evaluation in overdue:
            evaluation.status = "atrasada"
        if overdue and commit:
            db.session.commit()
        return len(overdue)

    @staticmethod
    def _serialize(evaluation, detailed=False):
        employee = evaluation.colaborador
        center = db.session.get(CostCenters, employee.centro_id) if employee else None
        cargo = db.session.get(Cargos, employee.cargo) if employee and employee.cargo else None
        supervisor = evaluation.supervisor
        payload = {
            "id": evaluation.id,
            "status": evaluation.status,
            "colaborador": {
                "id": evaluation.colaborador_id,
                "matricula": str(employee.matricula) if employee and employee.matricula else None,
                "nome": employee.nome if employee else "Colaborador removido",
                "cargo": cargo.nome if cargo else None,
                "centro_custo": center.local if center else None,
                "departamento": str(center.departamento) if center and center.departamento is not None else None,
                "data_admissao": _date_iso(_as_date(employee.data_admissao)) if employee else None,
                "data_fim_experiencia": _date_iso(evaluation.data_fim_experiencia),
                "data_referencia_util": _date_iso(evaluation.data_referencia_util),
            },
            "supervisor": {
                "id": evaluation.supervisor_id,
                "nome": supervisor.nome if supervisor else "Supervisor removido",
            },
            "aberta_em": _datetime_iso(evaluation.aberta_em),
            "prazo_supervisor_em": _datetime_iso(evaluation.prazo_supervisor_em),
            "supervisor_concluido_em": _datetime_iso(evaluation.supervisor_concluido_em),
            "rh_concluido_em": _datetime_iso(evaluation.rh_concluido_em),
            # Nunca retornamos a imagem da assinatura ao navegador após o envio.
            "assinatura_supervisor_registrada": bool(evaluation.assinatura_supervisor),
            "assinatura_rh_registrada": bool(evaluation.assinatura_rh),
        }
        if detailed:
            payload.update({
                "historico_rh": ExperienceEvaluationService._history_snapshot(evaluation.colaborador_id),
                "competencias": evaluation.competencias or {},
                "classificacao_perfil": evaluation.classificacao_perfil,
                "decisao_supervisor": evaluation.decisao_supervisor,
                "observacoes_supervisor": evaluation.observacoes_supervisor,
                "decisao_rh": evaluation.decisao_rh,
                "observacoes_rh": evaluation.observacoes_rh,
                "motivo_cancelamento": evaluation.motivo_cancelamento,
                "created_at": _datetime_iso(evaluation.created_at),
                "updated_at": _datetime_iso(evaluation.updated_at),
            })
        return payload

    @staticmethod
    def _supervisor_can_access(token_data, evaluation):
        return can_access_supervisor(token_data, evaluation.supervisor_id)

    @staticmethod
    def _get_evaluation_in_scope(evaluation_id, token_data):
        evaluation = db.session.get(ExperienceEvaluation, evaluation_id)
        if not evaluation:
            return None, (jsonify("Avaliação não encontrada."), 404)
        scoped = apply_cost_center_scope(
            ExperienceEvaluation.query.join(Employees, Employees.id == ExperienceEvaluation.colaborador_id)
            .filter(ExperienceEvaluation.id == evaluation_id),
            Employees.centro_id,
            token_data,
        ).first()
        if not scoped:
            return None, (jsonify("Você não possui acesso à filial desta avaliação."), 403)
        return evaluation, None

    @staticmethod
    def _public_payload(evaluation):
        """Retorna somente os dados necessários para a etapa pública."""
        payload = ExperienceEvaluationService._serialize(evaluation, detailed=False)
        payload.update({
            "competencias": evaluation.competencias or {},
            "observacoes_supervisor": evaluation.observacoes_supervisor,
        })
        return payload

    @staticmethod
    def _public_evaluation(body):
        """Garante que a tarefa aberta pertence ao supervisor informado."""
        try:
            supervisor_id = int(body.get("supervisor_id"))
            evaluation_id = int(body.get("avaliacao_id"))
        except (TypeError, ValueError):
            return None, (jsonify("Supervisor ou avaliação inválidos."), 400)

        evaluation = ExperienceEvaluation.query.filter(
            ExperienceEvaluation.id == evaluation_id,
            ExperienceEvaluation.supervisor_id == supervisor_id,
            ExperienceEvaluation.status.in_(OPEN_STATUSES),
        ).first()
        if not evaluation:
            return None, (jsonify("Avaliação não encontrada para este supervisor."), 404)
        return evaluation, None

    @staticmethod
    def _signature_path(filename):
        """Resolve um arquivo de assinatura sem permitir saída do diretório privado."""
        safe_name = Path(str(filename or "")).name
        if not safe_name or safe_name != filename:
            return None
        return EXPERIENCE_SIGNATURE_DIR / safe_name

    @staticmethod
    def _registered_rh_signature_path(filename):
        """Resolve a assinatura cadastrada sem aceitar caminhos externos ao diretório privado."""
        safe_name = Path(str(filename or "")).name
        if not safe_name or safe_name != filename or Path(safe_name).suffix.lower() != SIGNATURE_EXTENSION:
            return None
        return REGISTERED_RH_SIGNATURE_DIR / safe_name

    @classmethod
    def _remove_signature_file(cls, filename):
        """Remove a assinatura anterior quando ela for substituída ou invalidada."""
        path = cls._signature_path(filename)
        if path and path.is_file():
            path.unlink()

    @staticmethod
    def _store_signature_file(upload):
        """Aplica a mesma estratégia de upload de assinatura utilizada no TMops."""
        if not upload or not upload.filename:
            return None, "Envie a assinatura coletada."
        extension = Path(secure_filename(upload.filename)).suffix.lower()
        if extension != SIGNATURE_EXTENSION:
            return None, "A assinatura deve ser enviada como PNG."
        upload.stream.seek(0, 2)
        size = upload.stream.tell()
        upload.stream.seek(0)
        if not size or size > MAX_EXPERIENCE_SIGNATURE_SIZE:
            return None, "A assinatura deve ter no máximo 2 MB."
        try:
            with Image.open(upload.stream) as signature:
                signature.verify()
                if signature.format != "PNG":
                    return None, "A assinatura deve ser enviada como PNG."
        except (UnidentifiedImageError, OSError):
            return None, "A assinatura enviada é inválida."
        upload.stream.seek(0)
        EXPERIENCE_SIGNATURE_DIR.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid4().hex}{SIGNATURE_EXTENSION}"
        upload.save(EXPERIENCE_SIGNATURE_DIR / stored_name)
        return stored_name, None

    @classmethod
    def _clear_signature(cls, evaluation, field):
        """Invalida a assinatura e remove seu arquivo privado quando necessário."""
        previous = getattr(evaluation, field)
        setattr(evaluation, field, None)
        cls._remove_signature_file(previous)

    @classmethod
    def _save_signature_upload(cls, evaluation, field):
        """Substitui uma assinatura pelo novo arquivo PNG enviado pelo formulário."""
        stored_name, error = cls._store_signature_file(request.files.get("arquivo"))
        if error:
            return error
        previous = getattr(evaluation, field)
        setattr(evaluation, field, stored_name)
        cls._remove_signature_file(previous)
        db.session.commit()
        return None

    def public_supervisors(self):
        """Lista somente supervisores que possuem tarefa pendente."""
        rows = (
            db.session.query(Supervisors.id, Supervisors.nome)
            .join(CostCenters, CostCenters.supervisor_id == Supervisors.id)
            .join(ExperienceEvaluation, ExperienceEvaluation.supervisor_id == Supervisors.id)
            .filter(
                Supervisors.nome.isnot(None),
                ExperienceEvaluation.status.in_(OPEN_STATUSES),
            )
            .distinct()
            .order_by(Supervisors.nome)
            .all()
        )
        return jsonify([{"id": row.id, "nome": row.nome} for row in rows]), 200

    def public_tasks(self):
        """Consulta pendências sem expor identificadores nos parâmetros da URL."""
        body = request.get_json(silent=True) or {}
        try:
            supervisor_id = int(body.get("supervisor_id"))
        except (TypeError, ValueError):
            return jsonify("Informe um supervisor válido."), 400

        # A criação é responsabilidade do agendador; aqui somente atualizamos atrasos.
        self._refresh_overdue(commit=True)
        tasks = ExperienceEvaluation.query.filter(
            ExperienceEvaluation.supervisor_id == supervisor_id,
            ExperienceEvaluation.status.in_(OPEN_STATUSES),
        ).order_by(ExperienceEvaluation.prazo_supervisor_em).all()
        return jsonify([self._public_payload(item) for item in tasks]), 200

    def public_detail(self):
        """Abre uma tarefa vinculada ao supervisor selecionado."""
        evaluation, error = self._public_evaluation(request.get_json(silent=True) or {})
        if error:
            return error
        return jsonify(self._public_payload(evaluation)), 200

    def public_upload_signature(self):
        """Recebe a assinatura do supervisor como arquivo, igual ao fluxo do TMops."""
        evaluation, error = self._public_evaluation(request.form)
        if error:
            return error
        if evaluation.status not in OPEN_STATUSES:
            return jsonify("A etapa do supervisor não está disponível para assinatura."), 409
        _, validation_error = self._validate_supervisor_payload(
            {"competencias": evaluation.competencias or {}},
            require_complete=True,
        )
        if validation_error:
            return jsonify("Salve as cinco competências antes de assinar."), 400
        upload_error = self._save_signature_upload(evaluation, "assinatura_supervisor")
        if upload_error:
            return jsonify(upload_error), 400
        return jsonify(self._public_payload(evaluation)), 200

    def public_save(self, complete=False):
        """Salva ou conclui exclusivamente a etapa do supervisor."""
        body = request.get_json(silent=True) or {}
        evaluation, error = self._public_evaluation(body)
        if error:
            return error

        competencies, validation_error = self._validate_supervisor_payload(
            body,
            require_complete=complete,
        )
        if validation_error:
            return jsonify(validation_error), 400
        supervisor_changed = (
            (competencies is not None and dict(competencies) != (evaluation.competencias or {}))
            or (
                "observacoes_supervisor" in body
                and (str(body.get("observacoes_supervisor") or "").strip() or None)
                != evaluation.observacoes_supervisor
            )
        )
        if competencies is not None:
            evaluation.competencias = dict(competencies)
        if "observacoes_supervisor" in body:
            evaluation.observacoes_supervisor = (
                str(body.get("observacoes_supervisor") or "").strip() or None
            )

        if supervisor_changed:
            self._clear_signature(evaluation, "assinatura_supervisor")

        if complete:
            if not evaluation.assinatura_supervisor:
                return jsonify("Assine no campo indicado antes de enviar ao RH."), 400
            evaluation.status = "aguardando_rh"
            evaluation.supervisor_concluido_em = dt.now(SAO_PAULO)
            # O fluxo público não identifica um usuário interno do TMHub.
            evaluation.supervisor_concluido_por_usuario_id = None
        elif evaluation.status == "aberta":
            evaluation.status = "em_preenchimento"

        db.session.commit()
        return jsonify(self._public_payload(evaluation)), 200

    @safe_route
    def process(self, token_data):
        if not has_permission(token_data, "controle_experiencia_rh", "edit"):
            return jsonify("Você não possui permissão para processar tarefas de experiência."), 403
        return jsonify(self.process_pending_tasks()), 200

    @safe_route
    def supervisors(self, token_data):
        can_view = (
            has_permission(token_data, "avaliacao_experiencia_supervisor", "view")
            or has_permission(token_data, "controle_experiencia_rh", "view")
        )
        if not can_view:
            return jsonify("Você não possui acesso às avaliações de experiência."), 403
        rows = (
            apply_cost_center_scope(
                db.session.query(Supervisors.id, Supervisors.nome)
                .join(CostCenters, CostCenters.supervisor_id == Supervisors.id)
                .distinct(),
                CostCenters.id,
                token_data,
            )
            .order_by(Supervisors.nome)
            .all()
        )
        return jsonify([{"id": row.id, "nome": row.nome} for row in rows]), 200

    @safe_route
    def supervisor_tasks(self, token_data):
        if not has_permission(token_data, "avaliacao_experiencia_supervisor", "view"):
            return jsonify("Você não possui acesso às avaliações de experiência."), 403
        try:
            supervisor_id = int(request.args.get("supervisor_id"))
        except (TypeError, ValueError):
            return jsonify("Informe um supervisor válido."), 400
        if not can_access_supervisor(token_data, supervisor_id):
            return jsonify("Você não possui acesso à filial deste supervisor."), 403

        self.process_pending_tasks()
        evaluations = apply_cost_center_scope(
            ExperienceEvaluation.query.join(Employees, Employees.id == ExperienceEvaluation.colaborador_id).filter(
                ExperienceEvaluation.supervisor_id == supervisor_id,
                ExperienceEvaluation.status.in_(OPEN_STATUSES),
            ),
            Employees.centro_id,
            token_data,
        ).order_by(ExperienceEvaluation.prazo_supervisor_em).all()
        return jsonify([self._serialize(item) for item in evaluations]), 200

    @safe_route
    def active_employees(self, token_data):
        if not has_permission(token_data, "controle_experiencia_rh", "view"):
            return jsonify("Você não possui acesso ao controle de experiência."), 403
        today = dt.now(SAO_PAULO).date()
        evaluations = {
            (item.colaborador_id, item.data_fim_experiencia): item
            for item in apply_cost_center_scope(
                ExperienceEvaluation.query.join(Employees, Employees.id == ExperienceEvaluation.colaborador_id),
                Employees.centro_id,
                token_data,
            ).all()
        }
        rows = []
        for employee_row in self._employee_query(token_data).all():
            admission = _as_date(employee_row.Employees.data_admissao)
            end_date, business_reference, opening_date = self._period_dates(admission)
            if admission <= today <= end_date:
                evaluation = evaluations.get((employee_row.Employees.id, end_date))
                rows.append({
                    "colaborador_id": employee_row.Employees.id,
                    "matricula": employee_row.Employees.matricula,
                    "nome": employee_row.Employees.nome,
                    "supervisor": employee_row.supervisor_nome,
                    "data_admissao": _date_iso(admission),
                    "data_fim_experiencia": _date_iso(end_date),
                    "data_referencia_util": _date_iso(business_reference),
                    "data_abertura_prevista": _date_iso(opening_date),
                    "avaliacao_id": evaluation.id if evaluation else None,
                    "status_avaliacao": evaluation.status if evaluation else "aguardando_abertura",
                })
        return jsonify(rows), 200

    @safe_route
    def read_rh(self, token_data):
        if not has_permission(token_data, "controle_experiencia_rh", "view"):
            return jsonify("Você não possui acesso ao controle de experiência."), 403
        self.process_pending_tasks()
        status = str(request.args.get("status") or "").strip().lower()
        query = ExperienceEvaluation.query
        if status:
            query = query.filter(ExperienceEvaluation.status == status)
        rows = apply_cost_center_scope(
            query.join(Employees, Employees.id == ExperienceEvaluation.colaborador_id),
            Employees.centro_id, token_data
        ).order_by(ExperienceEvaluation.prazo_supervisor_em).all()
        return jsonify([self._serialize(item) for item in rows]), 200

    @safe_route
    def detail(self, evaluation_id, token_data):
        can_view = (
            has_permission(token_data, "avaliacao_experiencia_supervisor", "view")
            or has_permission(token_data, "controle_experiencia_rh", "view")
        )
        if not can_view:
            return jsonify("Você não possui acesso a esta avaliação."), 403
        evaluation, error = self._get_evaluation_in_scope(evaluation_id, token_data)
        if error:
            return error
        if (
            not has_permission(token_data, "controle_experiencia_rh", "view")
            and not self._supervisor_can_access(token_data, evaluation)
        ):
            return jsonify("Você não possui acesso a esta avaliação."), 403
        return jsonify(self._serialize(evaluation, detailed=True)), 200

    @staticmethod
    def _validate_supervisor_payload(body, require_complete=False):
        competencies = body.get("competencias")
        if competencies is not None:
            if not isinstance(competencies, dict):
                return None, "As competências devem ser enviadas como objeto."
            invalid = {
                field: value for field, value in competencies.items()
                if field not in COMPETENCIES or (value is not None and value not in RATING_LABELS)
            }
            if invalid:
                return None, "Uma ou mais classificações de competência são inválidas."
        if require_complete:
            if (
                not isinstance(competencies, dict)
                or set(competencies) != set(COMPETENCIES)
                or any(value not in RATING_LABELS for value in competencies.values())
            ):
                return None, "Preencha as cinco competências antes de concluir."
        return competencies, None

    @safe_route
    def update_supervisor(self, evaluation_id, token_data):
        if not has_permission(token_data, "avaliacao_experiencia_supervisor", "edit"):
            return jsonify("Você não possui permissão para preencher a avaliação."), 403
        evaluation, error = self._get_evaluation_in_scope(evaluation_id, token_data)
        if error:
            return error
        if not self._supervisor_can_access(token_data, evaluation):
            return jsonify("Você não possui acesso a este supervisor."), 403
        if evaluation.status not in OPEN_STATUSES:
            return jsonify("A etapa do supervisor não está disponível para edição."), 409

        body = request.get_json(silent=True) or {}
        competencies, validation_error = self._validate_supervisor_payload(body)
        if validation_error:
            return jsonify(validation_error), 400
        if competencies is not None:
            evaluation.competencias = dict(competencies)
        if "observacoes_supervisor" in body:
            evaluation.observacoes_supervisor = (
                str(body.get("observacoes_supervisor") or "").strip() or None
            )
        if evaluation.status == "aberta":
            evaluation.status = "em_preenchimento"
        # Qualquer edição após uma devolução administrativa exige nova assinatura.
        self._clear_signature(evaluation, "assinatura_supervisor")
        db.session.commit()
        return jsonify(self._serialize(evaluation, detailed=True)), 200

    @safe_route
    def complete_supervisor(self, evaluation_id, token_data):
        if not has_permission(token_data, "avaliacao_experiencia_supervisor", "edit"):
            return jsonify("Você não possui permissão para concluir a avaliação."), 403
        evaluation, error = self._get_evaluation_in_scope(evaluation_id, token_data)
        if error:
            return error
        if not self._supervisor_can_access(token_data, evaluation):
            return jsonify("Você não possui acesso a este supervisor."), 403
        if evaluation.status not in OPEN_STATUSES:
            return jsonify("A etapa do supervisor não está disponível para conclusão."), 409

        body = request.get_json(silent=True) or {}
        competencies, validation_error = self._validate_supervisor_payload(body, require_complete=True)
        if validation_error:
            return jsonify(validation_error), 400
        if not evaluation.assinatura_supervisor:
            return jsonify("Assine no campo indicado antes de enviar ao RH."), 400
        evaluation.competencias = dict(competencies)
        evaluation.observacoes_supervisor = str(body.get("observacoes_supervisor") or "").strip() or None
        evaluation.status = "aguardando_rh"
        evaluation.supervisor_concluido_em = dt.now(SAO_PAULO)
        evaluation.supervisor_concluido_por_usuario_id = token_data.get("id")
        db.session.commit()
        return jsonify(self._serialize(evaluation, detailed=True)), 200

    @safe_route
    def upload_supervisor_signature(self, evaluation_id, token_data):
        if not has_permission(token_data, "avaliacao_experiencia_supervisor", "edit"):
            return jsonify("Você não possui permissão para assinar a avaliação."), 403
        evaluation, error = self._get_evaluation_in_scope(evaluation_id, token_data)
        if error:
            return error
        if not self._supervisor_can_access(token_data, evaluation):
            return jsonify("Você não possui acesso a este supervisor."), 403
        if evaluation.status not in OPEN_STATUSES:
            return jsonify("A etapa do supervisor não está disponível para assinatura."), 409
        _, validation_error = self._validate_supervisor_payload(
            {"competencias": evaluation.competencias or {}},
            require_complete=True,
        )
        if validation_error:
            return jsonify("Salve as cinco competências antes de assinar."), 400
        upload_error = self._save_signature_upload(evaluation, "assinatura_supervisor")
        if upload_error:
            return jsonify(upload_error), 400
        return jsonify(self._serialize(evaluation, detailed=True)), 200

    @safe_route
    def update_rh(self, evaluation_id, token_data):
        if not has_permission(token_data, "controle_experiencia_rh", "edit"):
            return jsonify("Você não possui permissão para tratar esta avaliação."), 403
        evaluation, error = self._get_evaluation_in_scope(evaluation_id, token_data)
        if error:
            return error
        administrador = is_admin(token_data)
        if evaluation.status != "aguardando_rh" and not administrador:
            return jsonify("A avaliação precisa ser concluída pelo supervisor antes do RH."), 409

        body = request.get_json(silent=True) or {}
        supervisor_changed = administrador and (
            (
                "competencias" in body
                and dict(body.get("competencias") or {}) != (evaluation.competencias or {})
            )
            or (
                "observacoes_supervisor" in body
                and (str(body.get("observacoes_supervisor") or "").strip() or None)
                != evaluation.observacoes_supervisor
            )
        )
        rh_changed = (
            (
                "classificacao_perfil" in body
                and (str(body.get("classificacao_perfil") or "").strip() or None)
                != evaluation.classificacao_perfil
            )
            or (
                "decisao_supervisor" in body
                and (str(body.get("decisao_supervisor") or "").strip() or None)
                != evaluation.decisao_supervisor
            )
            or (
                "observacoes_rh" in body
                and (str(body.get("observacoes_rh") or "").strip() or None)
                != evaluation.observacoes_rh
            )
        )
        if administrador and "competencias" in body:
            competencies, validation_error = self._validate_supervisor_payload(body)
            if validation_error:
                return jsonify(validation_error), 400
            evaluation.competencias = dict(competencies or {})
        if administrador and "observacoes_supervisor" in body:
            evaluation.observacoes_supervisor = (
                str(body.get("observacoes_supervisor") or "").strip() or None
            )
        if "classificacao_perfil" in body:
            classification = str(body.get("classificacao_perfil") or "").strip()
            if classification and classification not in PROFILE_LABELS:
                return jsonify("Classificação do perfil inválida."), 400
            evaluation.classificacao_perfil = classification or None
        if "decisao_supervisor" in body:
            decision = str(body.get("decisao_supervisor") or "").strip()
            if decision and decision not in DECISION_LABELS:
                return jsonify("Decisão do RH inválida."), 400
            evaluation.decisao_supervisor = decision or None
            evaluation.decisao_rh = decision or None
        if "observacoes_rh" in body:
            evaluation.observacoes_rh = str(body.get("observacoes_rh") or "").strip() or None

        # Uma alteração posterior invalida a assinatura correspondente.
        if supervisor_changed:
            self._clear_signature(evaluation, "assinatura_supervisor")
            evaluation.supervisor_concluido_em = None
            evaluation.supervisor_concluido_por_usuario_id = None
            self._clear_signature(evaluation, "assinatura_rh")
            evaluation.rh_concluido_em = None
            evaluation.rh_concluido_por_usuario_id = None
            evaluation.status = "em_preenchimento"
        elif rh_changed and evaluation.status == "concluida":
            self._clear_signature(evaluation, "assinatura_rh")
            evaluation.rh_concluido_em = None
            evaluation.rh_concluido_por_usuario_id = None
            evaluation.status = "aguardando_rh"
        db.session.commit()
        return jsonify(self._serialize(evaluation, detailed=True)), 200

    @safe_route
    def complete_rh(self, evaluation_id, token_data):
        if not has_permission(token_data, "controle_experiencia_rh", "edit"):
            return jsonify("Você não possui permissão para concluir esta avaliação."), 403
        evaluation, error = self._get_evaluation_in_scope(evaluation_id, token_data)
        if error:
            return error
        if evaluation.status != "aguardando_rh":
            return jsonify("A avaliação não está aguardando a tratativa do RH."), 409
        if not evaluation.assinatura_supervisor:
            return jsonify("A assinatura do supervisor é necessária antes da tratativa do RH."), 409

        body = request.get_json(silent=True) or {}
        classification = str(
            body.get("classificacao_perfil") or evaluation.classificacao_perfil or ""
        ).strip()
        decision = str(
            body.get("decisao_supervisor")
            or body.get("decisao_rh")
            or evaluation.decisao_supervisor
            or evaluation.decisao_rh
            or ""
        ).strip()
        if classification not in PROFILE_LABELS:
            return jsonify("Informe a classificação do perfil."), 400
        if decision not in DECISION_LABELS:
            return jsonify("Informe a decisão do RH."), 400
        if not evaluation.assinatura_rh:
            return jsonify("Assine no campo indicado antes de concluir."), 400
        evaluation.classificacao_perfil = classification
        evaluation.decisao_supervisor = decision
        evaluation.decisao_rh = decision
        evaluation.observacoes_rh = str(
            body.get("observacoes_rh", evaluation.observacoes_rh) or ""
        ).strip() or None
        evaluation.status = "concluida"
        evaluation.rh_concluido_em = dt.now(SAO_PAULO)
        evaluation.rh_concluido_por_usuario_id = token_data.get("id")
        db.session.commit()
        return jsonify(self._serialize(evaluation, detailed=True)), 200

    @safe_route
    def upload_rh_signature(self, evaluation_id, token_data):
        if not has_permission(token_data, "controle_experiencia_rh", "edit"):
            return jsonify("Você não possui permissão para assinar esta avaliação."), 403
        evaluation, error = self._get_evaluation_in_scope(evaluation_id, token_data)
        if error:
            return error
        if evaluation.status != "aguardando_rh":
            return jsonify("A avaliação não está disponível para assinatura do RH."), 409
        if evaluation.classificacao_perfil not in PROFILE_LABELS:
            return jsonify("Salve a classificação do perfil antes de assinar."), 400
        if evaluation.decisao_rh not in DECISION_LABELS:
            return jsonify("Salve a decisão do RH antes de assinar."), 400
        upload_error = self._save_signature_upload(evaluation, "assinatura_rh")
        if upload_error:
            return jsonify(upload_error), 400
        return jsonify(self._serialize(evaluation, detailed=True)), 200

    @safe_route
    def use_registered_rh_signature(self, evaluation_id, token_data):
        """Copia a assinatura própria do usuário ou a escolhida pelo administrador."""
        if not has_permission(token_data, "controle_experiencia_rh", "edit"):
            return jsonify("Você não possui permissão para assinar esta avaliação."), 403
        authenticated_user_id = (token_data or {}).get("id")
        body = request.get_json(silent=True) or {}
        requested_user_id = body.get("usuario_id")
        if is_admin(token_data):
            try:
                signer_id = int(requested_user_id)
            except (TypeError, ValueError):
                return jsonify("Selecione um usuário com assinatura cadastrada."), 400
        else:
            signer_id = authenticated_user_id
            if requested_user_id not in (None, "", authenticated_user_id, str(authenticated_user_id)):
                return jsonify("Você pode utilizar somente a sua própria assinatura."), 403

        signer = db.session.get(Users, signer_id)
        if not signer or not signer.assinatura_cadastrada:
            return jsonify("O usuário selecionado não possui uma assinatura cadastrada."), 409

        evaluation, error = self._get_evaluation_in_scope(evaluation_id, token_data)
        if error:
            return error
        if evaluation.status != "aguardando_rh":
            return jsonify("A avaliação não está disponível para assinatura do RH."), 409
        if evaluation.classificacao_perfil not in PROFILE_LABELS:
            return jsonify("Salve a classificação do perfil antes de assinar."), 400
        if evaluation.decisao_rh not in DECISION_LABELS:
            return jsonify("Salve a decisão do RH antes de assinar."), 400

        source = self._registered_rh_signature_path(signer.assinatura_cadastrada)
        if not source or not source.is_file():
            return jsonify("A assinatura cadastrada do usuário selecionado não foi encontrada."), 409
        try:
            with Image.open(source) as signature:
                signature.verify()
                if signature.format != "PNG":
                    return jsonify("A assinatura cadastrada deve estar em PNG."), 409
        except (UnidentifiedImageError, OSError):
            return jsonify("A assinatura cadastrada é inválida."), 409

        EXPERIENCE_SIGNATURE_DIR.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid4().hex}{SIGNATURE_EXTENSION}"
        try:
            copyfile(source, EXPERIENCE_SIGNATURE_DIR / stored_name)
        except OSError:
            return jsonify("Não foi possível preparar a assinatura cadastrada."), 500

        previous = evaluation.assinatura_rh
        evaluation.assinatura_rh = stored_name
        self._remove_signature_file(previous)
        db.session.commit()
        return jsonify(self._serialize(evaluation, detailed=True)), 200

    @safe_route
    def registered_signatures(self, token_data):
        """Lista titulares de assinaturas cadastradas apenas para administradores."""
        if not is_admin(token_data):
            return jsonify("Somente administradores podem consultar assinaturas cadastradas."), 403

        users = Users.query.filter(
            Users.assinatura_cadastrada.isnot(None),
            func.trim(Users.assinatura_cadastrada) != "",
        ).order_by(Users.nome).all()
        options = []
        for user in users:
            signature_path = self._registered_rh_signature_path(user.assinatura_cadastrada)
            if signature_path and signature_path.is_file():
                options.append({"id": user.id, "nome": user.nome})
        return jsonify(options), 200

    @safe_route
    def delete(self, evaluation_id, token_data):
        """Permite remover somente registros finalizados e por administrador."""
        if not is_admin(token_data):
            return jsonify("Somente administradores podem excluir avaliações."), 403
        evaluation, error = self._get_evaluation_in_scope(evaluation_id, token_data)
        if error:
            return error
        if evaluation.status != "concluida":
            return jsonify("Somente avaliações concluídas podem ser excluídas."), 409

        self._remove_signature_file(evaluation.assinatura_supervisor)
        self._remove_signature_file(evaluation.assinatura_rh)
        db.session.delete(evaluation)
        db.session.commit()
        return jsonify("Avaliação excluída com sucesso."), 200

    @safe_route
    def update_status(self, evaluation_id, token_data):
        """Permite ao administrador ajustar manualmente o estado da tarefa."""
        if not is_admin(token_data):
            return jsonify("Somente administradores podem alterar o estado da avaliação."), 403
        evaluation, error = self._get_evaluation_in_scope(evaluation_id, token_data)
        if error:
            return error

        body = request.get_json(silent=True) or {}
        status = str(body.get("status") or "").strip().lower()
        if status not in ADMIN_EDITABLE_STATUSES:
            return jsonify("Estado inválido para alteração manual."), 400
        if status == evaluation.status:
            return jsonify(self._serialize(evaluation, detailed=True)), 200

        if status in OPEN_STATUSES:
            # Ao devolver para o supervisor, o parecer do RH deixa de valer.
            evaluation.classificacao_perfil = None
            evaluation.decisao_supervisor = None
            evaluation.decisao_rh = None
            evaluation.observacoes_rh = None
            evaluation.rh_concluido_em = None
            evaluation.rh_concluido_por_usuario_id = None
            self._clear_signature(evaluation, "assinatura_rh")
            evaluation.supervisor_concluido_em = None
            evaluation.supervisor_concluido_por_usuario_id = None
            self._clear_signature(evaluation, "assinatura_supervisor")
        elif status == "aguardando_rh":
            if not evaluation.assinatura_supervisor:
                return jsonify(
                    "Não é possível liberar ao RH sem a assinatura do supervisor."
                ), 409
            # Mantém os campos como rascunho, mas invalida a conclusão anterior.
            evaluation.rh_concluido_em = None
            evaluation.rh_concluido_por_usuario_id = None
            self._clear_signature(evaluation, "assinatura_rh")
        elif status == "concluida":
            # Registra a baixa administrativa sem fabricar assinaturas não realizadas.
            evaluation.rh_concluido_em = dt.now(SAO_PAULO)
            evaluation.rh_concluido_por_usuario_id = token_data.get("id")

        evaluation.status = status
        evaluation.cancelada_em = None
        evaluation.motivo_cancelamento = None
        db.session.commit()
        return jsonify(self._serialize(evaluation, detailed=True)), 200

    @safe_route
    def cancel(self, evaluation_id, token_data):
        if not has_permission(token_data, "controle_experiencia_rh", "edit"):
            return jsonify("Você não possui permissão para cancelar esta avaliação."), 403
        evaluation, error = self._get_evaluation_in_scope(evaluation_id, token_data)
        if error:
            return error
        if evaluation.status == "concluida":
            return jsonify("Uma avaliação concluída não pode ser cancelada."), 409
        body = request.get_json(silent=True) or {}
        reason = str(body.get("motivo") or "").strip()
        if not reason:
            return jsonify("Informe o motivo do cancelamento."), 400
        evaluation.status = "cancelada"
        evaluation.motivo_cancelamento = reason
        evaluation.cancelada_em = dt.now(SAO_PAULO)
        db.session.commit()
        return jsonify(self._serialize(evaluation, detailed=True)), 200

    @staticmethod
    def _pdf_font(size, bold=False):
        """Carrega uma fonte disponível no servidor, com alternativa segura."""
        font_name = "arialbd.ttf" if bold else "arial.ttf"
        fallback_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        font_paths = (
            EXPERIENCE_EVALUATION_TEMPLATE.parent / "fonts" / font_name,
            Path("C:/Windows/Fonts") / font_name,
            Path("/usr/share/fonts/truetype/msttcorefonts") / font_name,
            Path("/usr/share/fonts/truetype/dejavu") / fallback_name,
        )
        for font_path in font_paths:
            if font_path.is_file():
                return ImageFont.truetype(str(font_path), size=size)
        return ImageFont.load_default(size=size)

    @staticmethod
    def _pdf_lines(draw, value, width, font):
        """Quebra textos conforme a largura real da imagem gerada do modelo."""
        words = str(value or "").split()
        lines, current = [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and draw.textlength(candidate, font=font) > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines or ["-"]

    @classmethod
    def _pdf(cls, evaluation):
        """Rasteriza o modelo corporativo, preenche os dados e o exporta como PDF."""
        if not EXPERIENCE_EVALUATION_TEMPLATE.is_file():
            raise FileNotFoundError(
                "Modelo de avaliação de experiência não encontrado em assets."
            )

        data = cls._serialize(evaluation, detailed=True)
        collaborator = data["colaborador"]
        supervisor = data["supervisor"]
        history = data["historico_rh"] or {}
        absences = history.get("ausencias") or {}
        local = str(collaborator.get("centro_custo") or "-")

        def text(x, y, value, size=7.5, bold=False, width=None):
            font = cls._pdf_font(max(10, round(size * scale_y)), bold)
            lines = (
                cls._pdf_lines(draw, value, width * scale_x, font)
                if width
                else [str(value or "-")]
            )
            pixel_x, pixel_y = point(x, y)
            for index, line in enumerate(lines):
                line_y = pixel_y - font.size - (index * round((size + 1.5) * scale_y))
                draw.text((pixel_x, line_y), line, fill="black", font=font)

        def check(x, y):
            font = cls._pdf_font(round(10 * scale_y), bold=True)
            pixel_x, pixel_y = point(x, y)
            left, _, right, _ = draw.textbbox((0, 0), "X", font=font)
            draw.text(
                (pixel_x - ((right - left) / 2), pixel_y - font.size),
                "X",
                fill="black",
                font=font,
            )

        def fitted_text(x, y, value, width, preferred_size=7, minimum_size=5.5):
            """Reduz somente o texto do supervisor para mantê-lo no cabeçalho."""
            value = str(value or "-")
            size = preferred_size
            while size >= minimum_size:
                font = cls._pdf_font(max(9, round(size * scale_y)))
                if draw.textlength(value, font=font) <= width * scale_x:
                    pixel_x, pixel_y = point(x, y)
                    draw.text((pixel_x, pixel_y - font.size), value, fill="black", font=font)
                    return
                size -= 0.5
            # O nome completo continua disponível na aplicação; no impresso,
            # evita que um texto excepcionalmente longo ultrapasse a margem.
            font = cls._pdf_font(max(9, round(minimum_size * scale_y)))
            available = width * scale_x
            truncated = value
            while truncated and draw.textlength(f"{truncated}...", font=font) > available:
                truncated = truncated[:-1]
            pixel_x, pixel_y = point(x, y)
            draw.text((pixel_x, pixel_y - font.size), f"{truncated}...", fill="black", font=font)

        def date_fields(y, value):
            if not value:
                return
            # Remove os sublinhados do modelo antes de escrever uma data legível.
            left, top = point(70, y + 15)
            right, bottom = point(220, y - 10)
            draw.rectangle((left, top, right, bottom), fill="white")
            text(76, y, _date_br(value), 7.2)

        # O PDF é transformado em imagem de alta resolução. As referências abaixo
        # são proporcionais à página, evitando dependência da geometria interna do PDF.
        document = pdfium.PdfDocument(str(EXPERIENCE_EVALUATION_TEMPLATE))
        page = document[0]
        try:
            image = page.render(scale=PDF_RENDER_DPI / 72).to_pil().convert("RGB")
        finally:
            page.close()
            document.close()

        draw = ImageDraw.Draw(image)
        scale_x = image.width / PDF_PAGE_WIDTH
        scale_y = image.height / PDF_PAGE_HEIGHT

        def point(x, y):
            return round(x * scale_x), round((PDF_PAGE_HEIGHT - y) * scale_y)

        def paste_signature(signature_filename, x, y, width, height):
            """Centraliza a assinatura manuscrita acima da linha correspondente."""
            signature_path = cls._signature_path(signature_filename)
            if not signature_path or not signature_path.is_file():
                return
            try:
                with Image.open(signature_path) as source:
                    signature = source.convert("RGBA")
            except (UnidentifiedImageError, OSError):
                return

            # O canvas do celular pode conter área transparente ao redor do traço.
            # Cortamos essa área para centralizar o desenho, não o canvas inteiro.
            ink_bounds = signature.getchannel("A").getbbox()
            if ink_bounds:
                signature = signature.crop(ink_bounds)

            left, top = point(x, y + height)
            right, bottom = point(x + width, y)
            target_width, target_height = right - left, bottom - top
            signature.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
            signature_x = left + ((target_width - signature.width) // 2)
            signature_y = top + ((target_height - signature.height) // 2)
            image.paste(signature, (signature_x, signature_y), signature)

        # Cabeçalho e identificação do colaborador.
        text(77, 775, local, 7, width=180)
        text(304, 775, collaborator.get("matricula"), 7, width=72)
        fitted_text(438, 775, supervisor.get("nome"), width=145)
        text(100, 675, collaborator.get("nome"), 7.5, width=265)
        text(405, 675, collaborator.get("departamento"), 7.5, width=140)
        text(74, 660, collaborator.get("cargo"), 7.5, width=290)
        admission_date = _date_br(collaborator.get("data_admissao"))
        end_date = _date_br(collaborator.get("data_fim_experiencia"))
        text(422, 660, admission_date, 7.5, width=120)
        text(136, 645, f"{admission_date} a {end_date}", 7.5, width=225)
        text(442, 645, end_date, 7.5, width=100)

        # Histórico consolidado automaticamente pelo RH.
        history_lines = [
            f"Advertências: {history.get('advertencias', 0)}    Suspensões: {history.get('suspensoes', 0)}    Ausências: {absences.get('total', 0)}",
            "Por tipo: " + (", ".join(f"{key}: {value}" for key, value in (absences.get("por_tipo") or {}).items()) or "Nenhuma"),
            "Por classificação: " + (", ".join(f"{key}: {value}" for key, value in (absences.get("por_classificacao") or {}).items()) or "Nenhuma"),
        ]
        for index, line in enumerate(history_lines):
            text(52, 617 - (index * 11), line, 7.5, width=490)

        # Marca a avaliação do supervisor na coluna correspondente.
        rating_coordinates = {
            "nao_atende": 320,
            "atende_parcial": 412,
            "atende": 505,
        }
        rating_rows = (544, 510, 476, 442, 408)
        for key, y in zip(COMPETENCIES, rating_rows):
            coordinate = rating_coordinates.get((evaluation.competencias or {}).get(key))
            if coordinate:
                check(coordinate, y)

        profile_coordinates = {
            "incompativel": (55, 368),
            "bom_desenvolvivel": (55, 357),
            "excelente": (55, 346),
        }
        profile_coordinate = profile_coordinates.get(evaluation.classificacao_perfil)
        if profile_coordinate:
            check(*profile_coordinate)

        decision_coordinates = {
            "demitir": (55, 304),
            "efetivar": (130, 304),
            "prorrogar": (203, 304),
        }
        decision_coordinate = decision_coordinates.get(
            evaluation.decisao_rh or evaluation.decisao_supervisor
        )
        if decision_coordinate:
            check(*decision_coordinate)

        # O modelo possui um único campo de observação; os dois pareceres ficam identificados.
        observations = [
            f"Supervisor: {evaluation.observacoes_supervisor or '-'}",
            f"RH: {evaluation.observacoes_rh or '-'}",
        ]
        y = 274
        observation_font = cls._pdf_font(max(10, round(7.5 * scale_y)))
        for observation in observations:
            for line in cls._pdf_lines(draw, observation, 485 * scale_x, observation_font):
                text(52, y, line, 7.5)
                y -= 10

        operation_date = _as_date(evaluation.supervisor_concluido_em)
        rh_date = _as_date(evaluation.rh_concluido_em)
        # Datas e assinaturas registradas no celular ocupam os campos do formulário.
        date_fields(178, rh_date)
        date_fields(133, operation_date)
        paste_signature(evaluation.assinatura_rh, 300, 174, 190, 44)
        paste_signature(evaluation.assinatura_supervisor, 300, 120, 190, 44)
        output = BytesIO()
        image.save(output, format="PDF", resolution=PDF_RENDER_DPI)
        output.seek(0)
        return output

    @safe_route
    def export_pdf(self, evaluation_id, token_data):
        if not has_permission(token_data, "controle_experiencia_rh", "view"):
            return jsonify("Você não possui permissão para exportar esta avaliação."), 403
        evaluation, error = self._get_evaluation_in_scope(evaluation_id, token_data)
        if error:
            return error
        if evaluation.status != "concluida":
            return jsonify("O PDF é liberado somente após a finalização pelo RH."), 409
        matricula = evaluation.colaborador.matricula if evaluation.colaborador else evaluation.colaborador_id
        colaborador = evaluation.colaborador.nome if evaluation.colaborador else "COLABORADOR"
        filename = _download_filename(colaborador, matricula)
        return send_file(
            self._pdf(evaluation),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
