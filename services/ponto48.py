import csv
import json
import re
import shutil
import tempfile
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from uuid import UUID

from flask import current_app, jsonify, request as rq

from models.centros_de_custo import CostCenters
from models.colaboradores import Employees
from models.pt48 import (
    Ponto48Absenteismo,
    Ponto48Ajuste,
    Ponto48AjusteImport,
    Ponto48Espelho,
    Ponto48EspelhoImport,
    Ponto48HorasExtras,
    Ponto48Import,
)
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

PONTO48_UPLOAD_FIELDS = {"absenteismo", "horas_extras", "ajustes", "espelho"}
PONTO48_CHUNK_SIZE_LIMIT = 700 * 1024
PONTO48_FILE_SIZE_LIMIT = 30 * 1024 * 1024


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
    def _normalize_registration(value):
        return "".join(str(value or "").upper().split())

    @classmethod
    def _row_registration(cls, row):
        for field in ("Matrícula", "Matricula", "MATRÍCULA", "MATRICULA"):
            if row.get(field):
                return cls._normalize_registration(row[field])
        return ""

    @staticmethod
    def _duration_minutes(value):
        match = re.fullmatch(r"(\d+):(\d{2})", str(value or "").strip())
        if not match:
            return 0
        return int(match.group(1)) * 60 + int(match.group(2))

    @staticmethod
    def _signed_duration_minutes(value):
        match = re.fullmatch(r"(-?)(\d+):(\d{2})", str(value or "").strip())
        if not match:
            return 0
        minutes = int(match.group(2)) * 60 + int(match.group(3))
        return -minutes if match.group(1) else minutes

    @staticmethod
    def _percentage(value):
        cleaned = str(value or "0").replace("%", "").replace(" ", "").replace(",", ".")
        try:
            return round(float(cleaned), 2)
        except ValueError:
            return 0

    @staticmethod
    def _report_datetime(value):
        try:
            return datetime.strptime(str(value or "").strip(), "%d/%m/%Y %H:%M")
        except ValueError:
            return None

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

    @staticmethod
    def _read_journey_report(upload):
        upload.stream.seek(0)
        raw = upload.read()
        if len(raw) > 30 * 1024 * 1024:
            raise ValueError("O arquivo de espelho deve possuir no máximo 30 MB.")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")

        period_match = re.search(
            r"De\s+(\d{2}/\d{2}/\d{4})\s+at[eé]\s+(\d{2}/\d{2}/\d{4})",
            text,
            re.IGNORECASE,
        )
        if not period_match:
            raise ValueError("O período do relatório de Jornada não foi encontrado.")

        records = []
        employee_name = None
        for row in csv.reader(text.splitlines()):
            if not row:
                continue
            if row[0] == "Colaborador":
                employee_name = str(row[1] if len(row) > 1 else "").strip()
                continue
            if not employee_name or row[0] in {"Data", "TOTAIS"}:
                continue
            date_match = re.search(r"(\d{2}/\d{2}/\d{4})", str(row[0] or ""))
            if not date_match:
                continue
            row += [""] * (16 - len(row))
            records.append({
                "nome": employee_name,
                "data": date_match.group(1),
                "batidas": row[1:7],
                "credito": row[7],
                "debito": row[8],
                "intervalo": row[9],
                "horas_normais": row[10],
                "horas_extras_1": row[11],
                "horas_extras_2": row[12],
                "adicional_noturno": row[13],
                "saldo": row[14],
                "motivo": str(row[15] or "").strip() or None,
            })

        period = (
            datetime.strptime(period_match.group(1), "%d/%m/%Y").date(),
            datetime.strptime(period_match.group(2), "%d/%m/%Y").date(),
        )
        return period, records

    @classmethod
    def _employee_lookup(cls):
        lookup = {}
        employees = db.session.query(Employees.id, Employees.nome, Employees.matricula).all()
        for employee_id, name, registration in employees:
            lookup.setdefault(cls._normalize_name(name), []).append({
                "id": employee_id,
                "registration": cls._normalize_registration(registration),
            })
        return lookup

    @classmethod
    def _resolve_employee(cls, normalized_name, lookup, source_registration=""):
        matches = lookup.get(normalized_name, [])

        # Prefer the source registration whenever the report provides it.
        if source_registration:
            registration_matches = [
                item for item in matches
                if item["registration"] == cls._normalize_registration(source_registration)
            ]
            if registration_matches:
                return min(item["id"] for item in registration_matches), "matched"
            return None, "unmatched"

        if len(matches) == 1:
            return matches[0]["id"], "matched"
        if len(matches) > 1:
            registrations = {item["registration"] for item in matches if item["registration"]}
            # Duplicate database rows with the same name and registration represent one person.
            if len(registrations) == 1 and all(item["registration"] for item in matches):
                return min(item["id"] for item in matches), "matched"
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

    def _prepare_adjustment_import(self, upload, period, rows, employee_lookup, token_data):
        period_start, period_end = period
        existing_ids = [
            item.id for item in Ponto48AjusteImport.query.filter_by(
                periodo_inicio=period_start,
                periodo_fim=period_end,
            ).all()
        ]
        if existing_ids:
            Ponto48Ajuste.query.filter(
                Ponto48Ajuste.importacao_id.in_(existing_ids)
            ).delete(synchronize_session=False)
            Ponto48AjusteImport.query.filter(
                Ponto48AjusteImport.id.in_(existing_ids)
            ).delete(synchronize_session=False)

        imported = Ponto48AjusteImport(
            periodo_inicio=period_start,
            periodo_fim=period_end,
            arquivo_ajustes=upload.filename,
            criado_por_usuario_id=token_data.get("id"),
        )
        db.session.add(imported)
        db.session.flush()

        models = []
        for row in rows:
            name = str(row.get("Nome") or "").strip()
            date_match = re.search(r"(\d{2}/\d{2}/\d{4})", str(row.get("Data") or ""))
            if not name or name.upper() in {"RESUMO", "TOTAL"} or not date_match:
                continue

            normalized_name = self._normalize_name(name)
            employee_id, match_status = self._resolve_employee(
                normalized_name,
                employee_lookup,
                self._row_registration(row),
            )
            punches, punch_count, odd, _, _ = self._classify_punches(row)
            models.append(Ponto48Ajuste(
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
                quantidade_batidas=punch_count,
                batida_impar=odd,
                ajustado_por=str(row.get("Quem ajustou/aprovou") or "").strip() or None,
                alterado_em=self._report_datetime(row.get("Data da alteração")),
                solicitado_em=self._report_datetime(row.get("Data da criação")),
                motivo=str(row.get("Motivo") or "").strip() or None,
                solicitacao=self._normalize_name(row.get("É solicitação?")) == "SIM",
            ))
        db.session.add_all(models)
        return imported, models

    def _prepare_mirror_import(self, upload, period, rows, employee_lookup, token_data):
        period_start, period_end = period
        existing_ids = [
            item.id for item in Ponto48EspelhoImport.query.filter_by(
                periodo_inicio=period_start,
                periodo_fim=period_end,
            ).all()
        ]
        if existing_ids:
            Ponto48Espelho.query.filter(
                Ponto48Espelho.importacao_id.in_(existing_ids)
            ).delete(synchronize_session=False)
            Ponto48EspelhoImport.query.filter(
                Ponto48EspelhoImport.id.in_(existing_ids)
            ).delete(synchronize_session=False)

        imported = Ponto48EspelhoImport(
            periodo_inicio=period_start,
            periodo_fim=period_end,
            arquivo_espelho=upload.filename,
            criado_por_usuario_id=token_data.get("id"),
        )
        db.session.add(imported)
        db.session.flush()

        models = []
        for row in rows:
            name = row["nome"]
            normalized_name = self._normalize_name(name)
            employee_id, match_status = self._resolve_employee(normalized_name, employee_lookup)
            punches = [str(value or "").strip() for value in row["batidas"]]
            punch_count = sum(bool(value) for value in punches)
            models.append(Ponto48Espelho(
                importacao_id=imported.id,
                colaborador_id=employee_id,
                nome_colaborador=name,
                nome_normalizado=normalized_name,
                match_status=match_status,
                data=datetime.strptime(row["data"], "%d/%m/%Y").date(),
                entrada_1=punches[0] or None,
                saida_1=punches[1] or None,
                entrada_2=punches[2] or None,
                saida_2=punches[3] or None,
                entrada_3=punches[4] or None,
                saida_3=punches[5] or None,
                quantidade_batidas=punch_count,
                batida_impar=punch_count % 2 == 1,
                credito_minutos=self._signed_duration_minutes(row["credito"]),
                debito_minutos=self._signed_duration_minutes(row["debito"]),
                intervalo_minutos=self._signed_duration_minutes(row["intervalo"]),
                horas_normais_minutos=self._signed_duration_minutes(row["horas_normais"]),
                horas_extras_1_minutos=self._signed_duration_minutes(row["horas_extras_1"]),
                horas_extras_2_minutos=self._signed_duration_minutes(row["horas_extras_2"]),
                adicional_noturno_minutos=self._signed_duration_minutes(row["adicional_noturno"]),
                saldo_minutos=self._signed_duration_minutes(row["saldo"]),
                motivo=row["motivo"],
            ))
        db.session.add_all(models)
        return imported, models

    @staticmethod
    def _chunk_upload_dir(upload_id):
        try:
            normalized_id = str(UUID(str(upload_id)))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Identificador de upload inválido.")
        return Path(tempfile.gettempdir()) / "tmhub-ponto48-uploads" / normalized_id

    @staticmethod
    def _cleanup_stale_uploads(upload_root):
        if not upload_root.is_dir():
            return
        expiration = time.time() - (24 * 60 * 60)
        for candidate in upload_root.iterdir():
            try:
                if candidate.is_dir() and candidate.stat().st_mtime < expiration:
                    shutil.rmtree(candidate, ignore_errors=True)
            except OSError:
                continue

    @safe_route
    def upload_import_chunk(self, token_data):
        if not self._is_admin(token_data):
            return jsonify("Apenas administradores podem importar relatórios de ponto."), 403

        try:
            upload_id = rq.args.get("upload_id")
            field = str(rq.args.get("arquivo") or "")
            chunk_index = int(rq.args.get("indice", "-1"))
            total_chunks = int(rq.args.get("total", "0"))
            if field not in PONTO48_UPLOAD_FIELDS:
                raise ValueError("Tipo de arquivo inválido.")
            if chunk_index < 0 or total_chunks < 1 or chunk_index >= total_chunks:
                raise ValueError("Sequência de upload inválida.")

            chunk = rq.get_data(cache=False)
            if not chunk or len(chunk) > PONTO48_CHUNK_SIZE_LIMIT:
                raise ValueError("Cada bloco deve possuir entre 1 byte e 700 KB.")

            upload_dir = self._chunk_upload_dir(upload_id)
            self._cleanup_stale_uploads(upload_dir.parent)
            upload_dir.mkdir(parents=True, exist_ok=True)
            owner_file = upload_dir / "owner.json"
            owner = str(token_data.get("id"))
            if owner_file.exists():
                stored_owner = json.loads(owner_file.read_text(encoding="utf-8")).get("user_id")
                if stored_owner != owner:
                    return jsonify("Este upload pertence a outro usuário."), 403
            else:
                owner_file.write_text(json.dumps({"user_id": owner}), encoding="utf-8")

            chunk_path = upload_dir / f"{field}.{chunk_index:05d}.part"
            chunk_path.write_bytes(chunk)
            return jsonify({"recebido": chunk_index + 1, "total": total_chunks}), 201
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            return jsonify(str(error)), 400

    @safe_route
    def finalize_chunked_import(self, token_data):
        if not self._is_admin(token_data):
            return jsonify("Apenas administradores podem importar relatórios de ponto."), 403

        upload_dir = None
        opened_files = []
        try:
            payload = rq.get_json(silent=True) or {}
            upload_dir = self._chunk_upload_dir(payload.get("upload_id"))
            files = payload.get("arquivos") or {}
            if set(files) != PONTO48_UPLOAD_FIELDS:
                raise ValueError("Informe os quatro relatórios para concluir a importação.")
            if not upload_dir.is_dir():
                raise ValueError("Upload não encontrado ou expirado.")

            owner = json.loads((upload_dir / "owner.json").read_text(encoding="utf-8")).get("user_id")
            if owner != str(token_data.get("id")):
                return jsonify("Este upload pertence a outro usuário."), 403

            multipart_data = {}
            for field in PONTO48_UPLOAD_FIELDS:
                metadata = files[field] or {}
                total_chunks = int(metadata.get("total", 0))
                filename = Path(str(metadata.get("nome") or f"{field}.csv")).name
                if total_chunks < 1:
                    raise ValueError(f"Quantidade de blocos inválida para {field}.")

                assembled_path = upload_dir / f"{field}.csv"
                total_size = 0
                with assembled_path.open("wb") as assembled:
                    for index in range(total_chunks):
                        chunk_path = upload_dir / f"{field}.{index:05d}.part"
                        if not chunk_path.is_file():
                            raise ValueError(f"Falta o bloco {index + 1} do arquivo {filename}.")
                        total_size += chunk_path.stat().st_size
                        if total_size > PONTO48_FILE_SIZE_LIMIT:
                            raise ValueError(f"O arquivo {filename} excede o limite de 30 MB.")
                        with chunk_path.open("rb") as chunk_file:
                            shutil.copyfileobj(chunk_file, assembled)

                file_handle = assembled_path.open("rb")
                opened_files.append(file_handle)
                multipart_data[field] = (file_handle, filename)

            with current_app.test_request_context(
                "/dash/ponto-48h/importar",
                method="POST",
                data=multipart_data,
                content_type="multipart/form-data",
            ):
                return self.import_files.__wrapped__(self, token_data)
        except (ValueError, TypeError, OSError, json.JSONDecodeError) as error:
            db.session.rollback()
            return jsonify(str(error)), 400
        finally:
            for file_handle in opened_files:
                if not file_handle.closed:
                    file_handle.close()
            if upload_dir and upload_dir.is_dir():
                shutil.rmtree(upload_dir, ignore_errors=True)

    @safe_route
    def import_files(self, token_data):
        if not self._is_admin(token_data):
            return jsonify("Apenas administradores podem importar relatórios de ponto."), 403

        absenteeism_file = rq.files.get("absenteismo")
        overtime_file = rq.files.get("horas_extras")
        adjustments_file = rq.files.get("ajustes")
        mirror_file = rq.files.get("espelho")
        if not absenteeism_file or not overtime_file or not adjustments_file or not mirror_file:
            return jsonify("Envie os arquivos absenteismo, horas_extras, ajustes e espelho em CSV."), 400

        try:
            absenteeism_period, absenteeism_rows = self._read_report(absenteeism_file, "Nome,Previsto")
            overtime_period, overtime_rows = self._read_report(overtime_file, "Nome,Data")
            adjustments_period, adjustments_rows = self._read_report(adjustments_file, "Nome,Data")
            mirror_period, mirror_rows = self._read_journey_report(mirror_file)
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
                employee_id, match_status = self._resolve_employee(
                    normalized_name,
                    employee_lookup,
                    self._row_registration(row),
                )
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
                employee_id, match_status = self._resolve_employee(
                    normalized_name,
                    employee_lookup,
                    self._row_registration(row),
                )
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

            adjustments_import, adjustment_models = self._prepare_adjustment_import(
                adjustments_file,
                adjustments_period,
                adjustments_rows,
                employee_lookup,
                token_data,
            )
            mirror_import, mirror_models = self._prepare_mirror_import(
                mirror_file,
                mirror_period,
                mirror_rows,
                employee_lookup,
                token_data,
            )
            db.session.add_all(absenteeism_models + overtime_models)
            db.session.commit()

            match_counts = {"matched": 0, "unmatched": 0, "ambiguous": 0}
            for item in absenteeism_models + overtime_models:
                match_counts[item.match_status] += 1

            return jsonify({
                "message": "Absenteísmo, horas extras, ajustes e espelho importados com sucesso.",
                "importacao_id": imported.id,
                "importacao_ajustes_id": adjustments_import.id,
                "importacao_espelho_id": mirror_import.id,
                "periodo_inicio": period_start.isoformat(),
                "periodo_fim": period_end.isoformat(),
                "absenteismo": len(absenteeism_models),
                "horas_extras": len(overtime_models),
                "ajustes": len(adjustment_models),
                "espelho": len(mirror_models),
                "vinculos": match_counts,
            }), 201
        except (ValueError, UnicodeError, csv.Error) as error:
            db.session.rollback()
            return jsonify(str(error)), 400
        except Exception:
            db.session.rollback()
            raise

    @safe_route
    def import_adjustments(self, token_data):
        if not self._is_admin(token_data):
            return jsonify("Apenas administradores podem importar ajustes de ponto."), 403

        adjustments_file = rq.files.get("ajustes")
        if not adjustments_file:
            return jsonify("Envie o arquivo ajustes em CSV."), 400

        try:
            period, rows = self._read_report(adjustments_file, "Nome,Data")
            period_start, period_end = period
            employee_lookup = self._employee_lookup()

            existing_ids = [
                item.id for item in Ponto48AjusteImport.query.filter_by(
                    periodo_inicio=period_start,
                    periodo_fim=period_end,
                ).all()
            ]
            if existing_ids:
                Ponto48Ajuste.query.filter(
                    Ponto48Ajuste.importacao_id.in_(existing_ids)
                ).delete(synchronize_session=False)
                Ponto48AjusteImport.query.filter(
                    Ponto48AjusteImport.id.in_(existing_ids)
                ).delete(synchronize_session=False)

            imported = Ponto48AjusteImport(
                periodo_inicio=period_start,
                periodo_fim=period_end,
                arquivo_ajustes=adjustments_file.filename,
                criado_por_usuario_id=token_data.get("id"),
            )
            db.session.add(imported)
            db.session.flush()

            adjustment_models = []
            for row in rows:
                name = str(row.get("Nome") or "").strip()
                date_match = re.search(r"(\d{2}/\d{2}/\d{4})", str(row.get("Data") or ""))
                if not name or name.upper() in {"RESUMO", "TOTAL"} or not date_match:
                    continue

                normalized_name = self._normalize_name(name)
                employee_id, match_status = self._resolve_employee(
                    normalized_name,
                    employee_lookup,
                    self._row_registration(row),
                )
                punches, punch_count, odd, _, _ = self._classify_punches(row)
                adjustment_models.append(Ponto48Ajuste(
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
                    quantidade_batidas=punch_count,
                    batida_impar=odd,
                    ajustado_por=str(row.get("Quem ajustou/aprovou") or "").strip() or None,
                    alterado_em=self._report_datetime(row.get("Data da alteração")),
                    solicitado_em=self._report_datetime(row.get("Data da criação")),
                    motivo=str(row.get("Motivo") or "").strip() or None,
                    solicitacao=self._normalize_name(row.get("É solicitação?")) == "SIM",
                ))

            db.session.add_all(adjustment_models)
            db.session.commit()
            return jsonify({
                "message": "Relatório de ajustes importado com sucesso.",
                "importacao_id": imported.id,
                "periodo_inicio": period_start.isoformat(),
                "periodo_fim": period_end.isoformat(),
                "ajustes": len(adjustment_models),
            }), 201
        except (ValueError, UnicodeError, csv.Error) as error:
            db.session.rollback()
            return jsonify(str(error)), 400
        except Exception:
            db.session.rollback()
            raise

    @safe_route
    def delete_imported_data(self, token_data):
        if not self._is_admin(token_data):
            return jsonify("Apenas administradores podem limpar dados importados."), 403

        body = rq.get_json(silent=True) or {}
        import_id = body.get("importacao_id")
        if not import_id:
            return jsonify("Informe o importacao_id da referência que será removida."), 400

        imported = db.session.get(Ponto48Import, import_id)
        if not imported:
            return jsonify("Referência de importação não encontrada."), 404

        try:
            period_start = imported.periodo_inicio.isoformat()
            adjustment_import_ids = [
                item.id for item in Ponto48AjusteImport.query.filter_by(
                    periodo_inicio=imported.periodo_inicio,
                ).all()
            ]
            mirror_import_ids = [
                item.id for item in Ponto48EspelhoImport.query.filter_by(
                    periodo_inicio=imported.periodo_inicio,
                ).all()
            ]
            deleted_absenteeism = Ponto48Absenteismo.query.filter_by(
                importacao_id=imported.id,
            ).delete(synchronize_session=False)
            deleted_overtime = Ponto48HorasExtras.query.filter_by(
                importacao_id=imported.id,
            ).delete(synchronize_session=False)
            deleted_adjustments = 0
            if adjustment_import_ids:
                deleted_adjustments = Ponto48Ajuste.query.filter(
                    Ponto48Ajuste.importacao_id.in_(adjustment_import_ids)
                ).delete(synchronize_session=False)
                Ponto48AjusteImport.query.filter(
                    Ponto48AjusteImport.id.in_(adjustment_import_ids)
                ).delete(synchronize_session=False)

            deleted_mirror = 0
            if mirror_import_ids:
                deleted_mirror = Ponto48Espelho.query.filter(
                    Ponto48Espelho.importacao_id.in_(mirror_import_ids)
                ).delete(synchronize_session=False)
                Ponto48EspelhoImport.query.filter(
                    Ponto48EspelhoImport.id.in_(mirror_import_ids)
                ).delete(synchronize_session=False)

            db.session.delete(imported)
            db.session.commit()
            return jsonify({
                "message": "Dados importados da referência removidos com sucesso.",
                "periodo_inicio": period_start,
                "absenteismo": deleted_absenteeism,
                "horas_extras": deleted_overtime,
                "ajustes": deleted_adjustments,
                "espelho": deleted_mirror,
            }), 200
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

    @safe_route
    def adjustments_dashboard(self, token_data):
        del token_data
        batches = Ponto48AjusteImport.query.order_by(
            Ponto48AjusteImport.periodo_inicio.desc(),
            Ponto48AjusteImport.created_at.desc(),
        ).all()
        requested_batch_id = rq.args.get("importacao_id", type=int)
        batch = db.session.get(Ponto48AjusteImport, requested_batch_id) if requested_batch_id else (batches[0] if batches else None)
        if not batch:
            return jsonify({"importacoes": [], "importacao": None, "resumo": {}, "ajustes": []}), 200

        adjustments = Ponto48Ajuste.query.filter_by(importacao_id=batch.id).order_by(
            Ponto48Ajuste.data.desc(),
            Ponto48Ajuste.alterado_em.desc(),
        ).all()
        employee_ids = {item.colaborador_id for item in adjustments if item.colaborador_id}
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

        records = []
        for adjustment in adjustments:
            info = employee_info.get(adjustment.colaborador_id, {})
            delay_minutes = None
            if adjustment.alterado_em and adjustment.solicitado_em:
                delay_minutes = max(0, int((adjustment.alterado_em - adjustment.solicitado_em).total_seconds() // 60))
            records.append({
                "id": adjustment.id,
                "colaborador_id": adjustment.colaborador_id,
                "nome": info.get("nome") or adjustment.nome_colaborador,
                "matricula": info.get("matricula"),
                "centro_id": info.get("centro_id"),
                "centro": info.get("centro"),
                "departamento": info.get("departamento"),
                "supervisor_id": info.get("supervisor_id"),
                "supervisor": info.get("supervisor"),
                "match_status": adjustment.match_status,
                "data": adjustment.data.isoformat(),
                "batidas": [
                    adjustment.entrada_1,
                    adjustment.saida_1,
                    adjustment.entrada_2,
                    adjustment.saida_2,
                    adjustment.entrada_3,
                    adjustment.saida_3,
                ],
                "quantidade_batidas": adjustment.quantidade_batidas,
                "batida_impar": adjustment.batida_impar,
                "ajustado_por": adjustment.ajustado_por,
                "alterado_em": adjustment.alterado_em.isoformat() if adjustment.alterado_em else None,
                "solicitado_em": adjustment.solicitado_em.isoformat() if adjustment.solicitado_em else None,
                "tempo_ajuste_minutos": delay_minutes,
                "motivo": adjustment.motivo,
                "solicitacao": adjustment.solicitacao,
            })

        delay_values = [item["tempo_ajuste_minutos"] for item in records if item["tempo_ajuste_minutos"] is not None]
        unique_employees = {
            f"employee:{item['colaborador_id']}" if item["colaborador_id"] else f"name:{self._normalize_name(item['nome'])}"
            for item in records
        }
        return jsonify({
            "importacoes": [{
                "id": item.id,
                "periodo_inicio": item.periodo_inicio.isoformat(),
                "periodo_fim": item.periodo_fim.isoformat(),
                "arquivo_ajustes": item.arquivo_ajustes,
                "created_at": item.created_at.isoformat(),
            } for item in batches],
            "importacao": {
                "id": batch.id,
                "periodo_inicio": batch.periodo_inicio.isoformat(),
                "periodo_fim": batch.periodo_fim.isoformat(),
                "arquivo_ajustes": batch.arquivo_ajustes,
                "created_at": batch.created_at.isoformat(),
            },
            "resumo": {
                "ajustes": len(records),
                "colaboradores": len(unique_employees),
                "solicitacoes": sum(item["solicitacao"] for item in records),
                "ajustes_diretos": sum(not item["solicitacao"] for item in records),
                "sem_batidas": sum(item["quantidade_batidas"] == 0 for item in records),
                "batidas_impares": sum(item["batida_impar"] for item in records),
                "tempo_medio_minutos": round(sum(delay_values) / len(delay_values)) if delay_values else 0,
                "nao_vinculados": sum(item["match_status"] != "matched" for item in records),
            },
            "ajustes": records,
        }), 200

    @safe_route
    def mirror_dashboard(self, token_data):
        del token_data
        batches = Ponto48EspelhoImport.query.order_by(
            Ponto48EspelhoImport.periodo_inicio.desc(),
            Ponto48EspelhoImport.created_at.desc(),
        ).all()
        requested_batch_id = rq.args.get("importacao_id", type=int)
        batch = db.session.get(Ponto48EspelhoImport, requested_batch_id) if requested_batch_id else (batches[0] if batches else None)
        if not batch:
            return jsonify({"importacoes": [], "importacao": None, "resumo": {}, "colaboradores": []}), 200

        mirror_rows = Ponto48Espelho.query.filter_by(importacao_id=batch.id).order_by(
            Ponto48Espelho.data.asc(),
            Ponto48Espelho.id.asc(),
        ).all()
        employee_ids = {item.colaborador_id for item in mirror_rows if item.colaborador_id}
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
        for mirror in mirror_rows:
            key = f"employee:{mirror.colaborador_id}" if mirror.colaborador_id else f"name:{mirror.nome_normalizado}"
            if key not in combined:
                info = employee_info.get(mirror.colaborador_id, {})
                combined[key] = {
                    "key": key,
                    "colaborador_id": mirror.colaborador_id,
                    "nome": info.get("nome") or mirror.nome_colaborador,
                    "matricula": info.get("matricula"),
                    "centro_id": info.get("centro_id"),
                    "centro": info.get("centro"),
                    "departamento": info.get("departamento"),
                    "supervisor_id": info.get("supervisor_id"),
                    "supervisor": info.get("supervisor"),
                    "match_status": mirror.match_status,
                    "credito_minutos": 0,
                    "debito_minutos": 0,
                    "intervalo_minutos": 0,
                    "horas_normais_minutos": 0,
                    "horas_extras_minutos": 0,
                    "adicional_noturno_minutos": 0,
                    "saldo_final_minutos": 0,
                    "dias_batida_impar": 0,
                    "dias_sem_batida": 0,
                    "registros": [],
                }
            employee = combined[key]
            employee["credito_minutos"] += mirror.credito_minutos
            employee["debito_minutos"] += mirror.debito_minutos
            employee["intervalo_minutos"] += mirror.intervalo_minutos
            employee["horas_normais_minutos"] += mirror.horas_normais_minutos
            employee["horas_extras_minutos"] += mirror.horas_extras_1_minutos + mirror.horas_extras_2_minutos
            employee["adicional_noturno_minutos"] += mirror.adicional_noturno_minutos
            employee["saldo_final_minutos"] = mirror.saldo_minutos
            employee["dias_batida_impar"] += int(mirror.batida_impar)
            employee["dias_sem_batida"] += int(mirror.quantidade_batidas == 0)
            employee["registros"].append({
                "id": mirror.id,
                "data": mirror.data.isoformat(),
                "batidas": [
                    mirror.entrada_1,
                    mirror.saida_1,
                    mirror.entrada_2,
                    mirror.saida_2,
                    mirror.entrada_3,
                    mirror.saida_3,
                ],
                "quantidade_batidas": mirror.quantidade_batidas,
                "batida_impar": mirror.batida_impar,
                "credito_minutos": mirror.credito_minutos,
                "debito_minutos": mirror.debito_minutos,
                "intervalo_minutos": mirror.intervalo_minutos,
                "horas_normais_minutos": mirror.horas_normais_minutos,
                "horas_extras_minutos": mirror.horas_extras_1_minutos + mirror.horas_extras_2_minutos,
                "adicional_noturno_minutos": mirror.adicional_noturno_minutos,
                "saldo_minutos": mirror.saldo_minutos,
                "motivo": mirror.motivo,
            })

        employees = list(combined.values())
        employees.sort(key=lambda item: (item["saldo_final_minutos"], -item["dias_batida_impar"]))
        return jsonify({
            "importacoes": [{
                "id": item.id,
                "periodo_inicio": item.periodo_inicio.isoformat(),
                "periodo_fim": item.periodo_fim.isoformat(),
                "arquivo_espelho": item.arquivo_espelho,
                "created_at": item.created_at.isoformat(),
            } for item in batches],
            "importacao": {
                "id": batch.id,
                "periodo_inicio": batch.periodo_inicio.isoformat(),
                "periodo_fim": batch.periodo_fim.isoformat(),
                "arquivo_espelho": batch.arquivo_espelho,
                "created_at": batch.created_at.isoformat(),
            },
            "resumo": {
                "colaboradores": len(employees),
                "registros": len(mirror_rows),
                "saldo_positivo": sum(item["saldo_final_minutos"] > 0 for item in employees),
                "saldo_negativo": sum(item["saldo_final_minutos"] < 0 for item in employees),
                "saldo_zerado": sum(item["saldo_final_minutos"] == 0 for item in employees),
                "credito_minutos": sum(item["credito_minutos"] for item in employees),
                "debito_minutos": sum(item["debito_minutos"] for item in employees),
                "horas_normais_minutos": sum(item["horas_normais_minutos"] for item in employees),
                "horas_extras_minutos": sum(item["horas_extras_minutos"] for item in employees),
                "dias_batida_impar": sum(item["dias_batida_impar"] for item in employees),
                "nao_vinculados": sum(item["match_status"] != "matched" for item in employees),
            },
            "colaboradores": employees,
        }), 200
