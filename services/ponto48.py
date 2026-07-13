import csv
import re
import unicodedata
from datetime import datetime

from flask import jsonify, request as rq

from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.pt48 import Ponto48Absenteismo, Ponto48HorasExtras, Ponto48Import
from models.supervisores import Supervisors
from utils.db import db
from utils.safe_route import safe_route


PUNCH_FIELDS = [
    "1ª Entrada",
    "1ª Saída",
    "2ª Entrada",
    "2ª Saída",
    "3ª Entrada",
    "3ª Saída",
]


class Ponto48Service:
    @staticmethod
    def _is_admin(token_data):
        return str(token_data.get("perm", "")).upper() == "ADMIN"

    @staticmethod
    def _normalize_name(value):
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
        return " ".join(without_accents.upper().split())

    @staticmethod
    def _duration_minutes(value):
        match = re.fullmatch(r"(\d+):(\d{2})", str(value or "").strip())
        if not match:
            return 0
        return int(match.group(1)) * 60 + int(match.group(2))

    @staticmethod
    def _percentage(value):
        cleaned = str(value or "0").replace("%", "").replace(" ", "").replace(",", ".")
        try:
            return round(float(cleaned), 2)
        except ValueError:
            return 0

    @staticmethod
    def _read_report(upload, expected_header):
        upload.stream.seek(0)
        raw = upload.read()
        if len(raw) > 20 * 1024 * 1024:
            raise ValueError("Cada arquivo CSV deve possuir no máximo 20 MB.")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")

        lines = text.splitlines()
        period_match = re.search(r"De\s+(\d{2}/\d{2}/\d{4})\s+at[eé]\s+(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if not period_match:
            raise ValueError("O período do relatório não foi encontrado.")

        header_index = next(
            (index for index, line in enumerate(lines) if line.startswith(expected_header)),
            None,
        )
        if header_index is None:
            raise ValueError(f"Cabeçalho esperado não encontrado: {expected_header}.")

        period = (
            datetime.strptime(period_match.group(1), "%d/%m/%Y").date(),
            datetime.strptime(period_match.group(2), "%d/%m/%Y").date(),
        )
        return period, list(csv.DictReader(lines[header_index:]))

    @classmethod
    def _employee_lookup(cls):
        lookup = {}
        for employee_id, name in db.session.query(Employees.id, Employees.nome).all():
            lookup.setdefault(cls._normalize_name(name), []).append(employee_id)
        return lookup

    @staticmethod
    def _resolve_employee(normalized_name, lookup):
        matches = lookup.get(normalized_name, [])
        if len(matches) == 1:
            return matches[0], "matched"
        if len(matches) > 1:
            return None, "ambiguous"
        return None, "unmatched"

    @classmethod
    def _classify_punches(cls, row):
        values = [str(row.get(field) or "").strip() for field in PUNCH_FIELDS]
        filled = [value for value in values if value]
        odd = len(filled) % 2 == 1
        reasons = []

        if odd:
            reasons.append("Quantidade ímpar de batidas")

        seen_empty = False
        has_gap = False
        for value in values:
            if not value:
                seen_empty = True
            elif seen_empty:
                has_gap = True
        if has_gap:
            reasons.append("Sequência de batidas incompleta")

        timeline = []
        offset = 0
        rollovers = 0
        previous = None
        for value in filled:
            minutes = cls._duration_minutes(value)
            current = minutes + offset
            if previous is not None and current <= previous:
                offset += 24 * 60
                rollovers += 1
                current = minutes + offset
            timeline.append(current)
            previous = current

        if rollovers > 1:
            reasons.append("Mais de uma virada de dia na sequência")
        if len(timeline) >= 2 and timeline[-1] - timeline[0] > 20 * 60:
            reasons.append("Jornada superior a 20 horas")

        for index in range(0, len(values), 2):
            entry = values[index]
            exit_value = values[index + 1]
            if not entry or not exit_value:
                continue
            entry_minutes = cls._duration_minutes(entry)
            exit_minutes = cls._duration_minutes(exit_value)
            if exit_minutes <= entry_minutes:
                exit_minutes += 24 * 60
            if exit_minutes - entry_minutes > 12 * 60:
                reasons.append(f"Período trabalhado superior a 12 horas no par {index // 2 + 1}")

        return values, len(filled), odd, bool(reasons), "; ".join(dict.fromkeys(reasons))

    @safe_route
    def import_files(self, token_data):
        if not self._is_admin(token_data):
            return jsonify("Apenas administradores podem importar relatórios de ponto."), 403

        absenteeism_file = rq.files.get("absenteismo")
        overtime_file = rq.files.get("horas_extras")
        if not absenteeism_file or not overtime_file:
            return jsonify("Envie os arquivos absenteismo e horas_extras em CSV."), 400

        try:
            absenteeism_period, absenteeism_rows = self._read_report(absenteeism_file, "Nome,Previsto")
            overtime_period, overtime_rows = self._read_report(overtime_file, "Nome,Data")
            if absenteeism_period != overtime_period:
                return jsonify("Os relatórios precisam possuir o mesmo período."), 400

            employee_lookup = self._employee_lookup()
            period_start, period_end = absenteeism_period

            existing_ids = [
                item.id for item in Ponto48Import.query.filter_by(
                    periodo_inicio=period_start,
                    periodo_fim=period_end,
                ).all()
            ]
            if existing_ids:
                Ponto48Absenteismo.query.filter(Ponto48Absenteismo.importacao_id.in_(existing_ids)).delete(synchronize_session=False)
                Ponto48HorasExtras.query.filter(Ponto48HorasExtras.importacao_id.in_(existing_ids)).delete(synchronize_session=False)
                Ponto48Import.query.filter(Ponto48Import.id.in_(existing_ids)).delete(synchronize_session=False)

            imported = Ponto48Import(
                periodo_inicio=period_start,
                periodo_fim=period_end,
                arquivo_absenteismo=absenteeism_file.filename,
                arquivo_horas_extras=overtime_file.filename,
                criado_por_usuario_id=token_data.get("id"),
            )
            db.session.add(imported)
            db.session.flush()

            absenteeism_models = []
            for row in absenteeism_rows:
                name = str(row.get("Nome") or "").strip()
                if not name or name.upper() == "TOTAIS" or not re.fullmatch(r"\d+:\d{2}", str(row.get("Previsto") or "")):
                    continue
                normalized_name = self._normalize_name(name)
                employee_id, match_status = self._resolve_employee(normalized_name, employee_lookup)
                absenteeism_models.append(Ponto48Absenteismo(
                    importacao_id=imported.id,
                    colaborador_id=employee_id,
                    nome_colaborador=name,
                    nome_normalizado=normalized_name,
                    match_status=match_status,
                    previsto_minutos=self._duration_minutes(row.get("Previsto")),
                    ausencia_minutos=self._duration_minutes(row.get("Ausência")),
                    presenca_minutos=self._duration_minutes(row.get("Presença")),
                    abs_percentual=self._percentage(row.get("ABS")),
                ))

            overtime_models = []
            for row in overtime_rows:
                date_match = re.search(r"(\d{2}/\d{2}/\d{4})", str(row.get("Data") or ""))
                name = str(row.get("Nome") or "").strip()
                if not name or not date_match:
                    continue
                normalized_name = self._normalize_name(name)
                employee_id, match_status = self._resolve_employee(normalized_name, employee_lookup)
                punches, punch_count, odd, irregular, reason = self._classify_punches(row)
                overtime_models.append(Ponto48HorasExtras(
                    importacao_id=imported.id,
                    colaborador_id=employee_id,
                    nome_colaborador=name,
                    nome_normalizado=normalized_name,
                    match_status=match_status,
                    data=datetime.strptime(date_match.group(1), "%d/%m/%Y").date(),
                    entrada_1=punches[0] or None,
                    saida_1=punches[1] or None,
                    entrada_2=punches[2] or None,
                    saida_2=punches[3] or None,
                    entrada_3=punches[4] or None,
                    saida_3=punches[5] or None,
                    horas_normais_minutos=self._duration_minutes(row.get("Horas normais")),
                    horas_extras_minutos=self._duration_minutes(row.get("Total de H.extras")),
                    motivo=str(row.get("Motivo") or "").strip() or None,
                    quantidade_batidas=punch_count,
                    batida_impar=odd,
                    batida_irregular=irregular,
                    irregularidade=reason or None,
                ))

            db.session.add_all(absenteeism_models + overtime_models)
            db.session.commit()

            match_counts = {"matched": 0, "unmatched": 0, "ambiguous": 0}
            for item in absenteeism_models + overtime_models:
                match_counts[item.match_status] += 1

            return jsonify({
                "message": "Relatórios de ponto importados com sucesso.",
                "importacao_id": imported.id,
                "periodo_inicio": period_start.isoformat(),
                "periodo_fim": period_end.isoformat(),
                "absenteismo": len(absenteeism_models),
                "horas_extras": len(overtime_models),
                "vinculos": match_counts,
            }), 201
        except (ValueError, UnicodeError, csv.Error) as error:
            db.session.rollback()
            return jsonify(str(error)), 400
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def _batch_dict(batch):
        return {
            "id": batch.id,
            "periodo_inicio": batch.periodo_inicio.isoformat(),
            "periodo_fim": batch.periodo_fim.isoformat(),
            "arquivo_absenteismo": batch.arquivo_absenteismo,
            "arquivo_horas_extras": batch.arquivo_horas_extras,
            "created_at": batch.created_at.isoformat(),
        }

    @safe_route
    def dashboard(self, token_data):
        del token_data
        batches = Ponto48Import.query.order_by(Ponto48Import.periodo_inicio.desc(), Ponto48Import.created_at.desc()).all()
        requested_batch_id = rq.args.get("importacao_id", type=int)
        batch = db.session.get(Ponto48Import, requested_batch_id) if requested_batch_id else (batches[0] if batches else None)
        if not batch:
            return jsonify({"importacoes": [], "importacao": None, "resumo": {}, "colaboradores": []}), 200

        absenteeism_rows = Ponto48Absenteismo.query.filter_by(importacao_id=batch.id).all()
        overtime_rows = Ponto48HorasExtras.query.filter_by(importacao_id=batch.id).order_by(Ponto48HorasExtras.data.desc()).all()
        employee_ids = {item.colaborador_id for item in absenteeism_rows + overtime_rows if item.colaborador_id}

        employee_info = {}
        if employee_ids:
            employees = (
                db.session.query(
                    Employees.id,
                    Employees.nome,
                    Employees.matricula,
                    CostCenters.id.label("centro_id"),
                    CostCenters.local.label("centro"),
                    CostCenters.departamento,
                    Supervisors.id.label("supervisor_id"),
                    Supervisors.nome.label("supervisor"),
                )
                .outerjoin(CostCenters, CostCenters.id == Employees.centro_id)
                .outerjoin(Supervisors, Supervisors.id == CostCenters.supervisor_id)
                .filter(Employees.id.in_(employee_ids))
                .all()
            )
            employee_info = {employee.id: employee._asdict() for employee in employees}

        combined = {}

        def ensure_item(source):
            key = f"employee:{source.colaborador_id}" if source.colaborador_id else f"name:{source.nome_normalizado}"
            if key not in combined:
                info = employee_info.get(source.colaborador_id, {})
                combined[key] = {
                    "key": key,
                    "colaborador_id": source.colaborador_id,
                    "nome": info.get("nome") or source.nome_colaborador,
                    "matricula": info.get("matricula"),
                    "centro_id": info.get("centro_id"),
                    "centro": info.get("centro"),
                    "departamento": info.get("departamento"),
                    "supervisor_id": info.get("supervisor_id"),
                    "supervisor": info.get("supervisor"),
                    "match_status": source.match_status,
                    "previsto_minutos": 0,
                    "ausencia_minutos": 0,
                    "presenca_minutos": 0,
                    "abs_percentual": 0,
                    "horas_extras_minutos": 0,
                    "dias_com_he": 0,
                    "batidas_impares": 0,
                    "batidas_irregulares": 0,
                    "batidas_corretas": 0,
                    "registros": [],
                }
            return combined[key]

        for absence in absenteeism_rows:
            item = ensure_item(absence)
            item["previsto_minutos"] += absence.previsto_minutos
            item["ausencia_minutos"] += absence.ausencia_minutos
            item["presenca_minutos"] += absence.presenca_minutos

        for overtime in overtime_rows:
            item = ensure_item(overtime)
            item["horas_extras_minutos"] += overtime.horas_extras_minutos
            item["dias_com_he"] += 1
            item["batidas_impares"] += int(overtime.batida_impar)
            item["batidas_irregulares"] += int(overtime.batida_irregular)
            item["batidas_corretas"] += int(not overtime.batida_irregular)
            item["registros"].append({
                "id": overtime.id,
                "data": overtime.data.isoformat(),
                "batidas": [
                    overtime.entrada_1,
                    overtime.saida_1,
                    overtime.entrada_2,
                    overtime.saida_2,
                    overtime.entrada_3,
                    overtime.saida_3,
                ],
                "horas_normais_minutos": overtime.horas_normais_minutos,
                "horas_extras_minutos": overtime.horas_extras_minutos,
                "batida_impar": overtime.batida_impar,
                "batida_irregular": overtime.batida_irregular,
                "irregularidade": overtime.irregularidade,
                "motivo": overtime.motivo,
            })

        employees = list(combined.values())
        for employee in employees:
            employee["abs_percentual"] = round(
                employee["ausencia_minutos"] * 100 / employee["previsto_minutos"],
                2,
            ) if employee["previsto_minutos"] else 0
            employee["dias_problematicos"] = employee["batidas_irregulares"]

        employees.sort(key=lambda item: (
            item["dias_problematicos"],
            item["abs_percentual"],
            item["horas_extras_minutos"],
        ), reverse=True)

        return jsonify({
            "importacoes": [self._batch_dict(item) for item in batches],
            "importacao": self._batch_dict(batch),
            "resumo": {
                "colaboradores": len(employees),
                "com_irregularidade": sum(1 for item in employees if item["dias_problematicos"]),
                "batidas_impares": sum(item["batidas_impares"] for item in employees),
                "batidas_irregulares": sum(item["batidas_irregulares"] for item in employees),
                "batidas_corretas": sum(item["batidas_corretas"] for item in employees),
                "ausencia_minutos": sum(item["ausencia_minutos"] for item in employees),
                "horas_extras_minutos": sum(item["horas_extras_minutos"] for item in employees),
                "nao_vinculados": sum(1 for item in employees if item["match_status"] != "matched"),
            },
            "colaboradores": employees,
        }), 200
