"""Consultas agregadas do dashboard de infrações de jornada."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from flask import jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from utils.db import db
from utils.filial_scope import allowed_cost_center_ids
from utils.permissions import has_permission
from utils.safe_route import safe_route


INDICATORS = ("intrajornada", "interjornada", "escala")


def _parse_date(value, fallback):
    if not value:
        return fallback
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return fallback


class JourneyDashboardService:
    """Entrega somente agregações do relatório Auditoria/Jornadas."""

    @staticmethod
    def _values(name):
        return [value.strip() for value in str(request.args.get(name) or "").split(",") if value.strip()]

    @staticmethod
    def _base_from():
        return """
            FROM jornadas_infracoes i
            JOIN jornadas_importacoes imp ON imp.id = i.importacao_id
            LEFT JOIN colaboradores e ON e.id = i.colaborador_id
            LEFT JOIN centro_de_custo c ON c.id = e.centro_id
        """

    def _where(self, token_data, include_filters=True):
        conditions, params = ["1 = 1"], {}

        def add_in(column, prefix, values):
            if not values:
                return
            names = []
            for index, value in enumerate(values):
                key = f"{prefix}_{index}"
                params[key] = value
                names.append(f":{key}")
            conditions.append(f"{column} IN ({', '.join(names)})")

        allowed_centers = allowed_cost_center_ids(token_data)
        if allowed_centers is not None:
            allowed_centers = list(allowed_centers)
            if allowed_centers:
                add_in("e.centro_id", "centro", allowed_centers)
            else:
                conditions.append("1 = 0")

        start = _parse_date(request.args.get("inicio"), date.today().replace(day=1))
        end = _parse_date(request.args.get("fim"), date.today())
        if end < start:
            start, end = end, start
        conditions.extend(("i.data_ocorrencia >= :inicio", "i.data_ocorrencia <= :fim"))
        params.update({"inicio": start, "fim": end})

        if include_filters:
            add_in("i.indicador", "tipo", self._values("tipo"))
            add_in("LOWER(COALESCE(c.local, ''))", "contrato", [item.lower() for item in self._values("contrato")])
            add_in("CAST(c.departamento AS VARCHAR)", "departamento", self._values("departamento"))
            links = set(self._values("vinculo"))
            if links == {"vinculado"}:
                conditions.append("e.id IS NOT NULL")
            elif links == {"pendente"}:
                conditions.append("e.id IS NULL")

        return " AND ".join(conditions), params, start, end

    @staticmethod
    def _empty(start, end, available=True):
        return {
            "disponivel": available,
            "periodo": {"inicio": start.isoformat(), "fim": end.isoformat()},
            "indicadores": {"total": 0, "intrajornada": 0, "interjornada": 0, "escala": 0, "colaboradores": 0, "pendentes_vinculo": 0},
            "evolucao": [], "contratos": [], "departamentos": [], "ofensores": [], "recentes": [],
            "filtros": {"contratos": [], "departamentos": []}, "ultima_importacao": None,
        }

    @safe_route
    def read(self, token_data):
        if not has_permission(token_data, "dashboard_jornadas", "view"):
            return jsonify("Você não possui acesso ao Dashboard de Jornadas."), 403

        where, params, start, end = self._where(token_data)
        scoped_where, scoped_params, _, _ = self._where(token_data, include_filters=False)
        try:
            aggregate = db.session.execute(text(f"""
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(CASE WHEN i.indicador = 'intrajornada' THEN 1 ELSE 0 END), 0) AS intrajornada,
                       COALESCE(SUM(CASE WHEN i.indicador = 'interjornada' THEN 1 ELSE 0 END), 0) AS interjornada,
                       COALESCE(SUM(CASE WHEN i.indicador = 'escala' THEN 1 ELSE 0 END), 0) AS escala,
                       COUNT(DISTINCT COALESCE(CAST(i.colaborador_id AS VARCHAR), NULLIF(i.matricula, ''), i.nome_colaborador)) AS colaboradores,
                       COALESCE(SUM(CASE WHEN e.id IS NULL THEN 1 ELSE 0 END), 0) AS pendentes_vinculo
                {self._base_from()} WHERE {where}
            """), params).mappings().one()

            evolution = db.session.execute(text(f"""
                SELECT i.data_ocorrencia AS data,
                       COUNT(*) AS total,
                       COALESCE(SUM(CASE WHEN i.indicador = 'intrajornada' THEN 1 ELSE 0 END), 0) AS intrajornada,
                       COALESCE(SUM(CASE WHEN i.indicador = 'interjornada' THEN 1 ELSE 0 END), 0) AS interjornada,
                       COALESCE(SUM(CASE WHEN i.indicador = 'escala' THEN 1 ELSE 0 END), 0) AS escala
                {self._base_from()} WHERE {where}
                GROUP BY i.data_ocorrencia ORDER BY i.data_ocorrencia
            """), params).mappings().all()

            offenders = db.session.execute(text(f"""
                SELECT i.nome_colaborador AS colaborador, i.matricula,
                       COALESCE(c.local, 'Não informado') AS contrato,
                       COUNT(*) AS total,
                       COALESCE(SUM(CASE WHEN i.indicador = 'intrajornada' THEN 1 ELSE 0 END), 0) AS intrajornada,
                       COALESCE(SUM(CASE WHEN i.indicador = 'interjornada' THEN 1 ELSE 0 END), 0) AS interjornada,
                       COALESCE(SUM(CASE WHEN i.indicador = 'escala' THEN 1 ELSE 0 END), 0) AS escala
                {self._base_from()} WHERE {where}
                GROUP BY i.nome_colaborador, i.matricula, c.local
                ORDER BY total DESC, i.nome_colaborador LIMIT 10
            """), params).mappings().all()

            department_rows = db.session.execute(text(f"""
                SELECT COALESCE(CAST(c.departamento AS VARCHAR), 'Não informado') AS label,
                       COUNT(*) AS total,
                       COALESCE(SUM(CASE WHEN i.indicador = 'intrajornada' THEN 1 ELSE 0 END), 0) AS intrajornada,
                       COALESCE(SUM(CASE WHEN i.indicador = 'interjornada' THEN 1 ELSE 0 END), 0) AS interjornada,
                       COALESCE(SUM(CASE WHEN i.indicador = 'escala' THEN 1 ELSE 0 END), 0) AS escala
                {self._base_from()} WHERE {where}
                GROUP BY COALESCE(CAST(c.departamento AS VARCHAR), 'Não informado')
                ORDER BY total DESC, label LIMIT 12
            """), params).mappings().all()
            departments = [
                {
                    "label": str(row["label"]),
                    "total": int(row["total"] or 0),
                    **{indicator: int(row[indicator] or 0) for indicator in INDICATORS},
                }
                for row in department_rows
            ]
            filter_contracts = db.session.execute(text(f"SELECT DISTINCT c.local {self._base_from()} WHERE {scoped_where} AND c.local IS NOT NULL ORDER BY c.local"), scoped_params).scalars().all()
            filter_departments = db.session.execute(text(f"SELECT DISTINCT c.departamento {self._base_from()} WHERE {scoped_where} AND c.departamento IS NOT NULL ORDER BY c.departamento"), scoped_params).scalars().all()
            latest = db.session.execute(text(f"""
                SELECT imp.data_referencia, imp.arquivo_origem
                {self._base_from()} WHERE {scoped_where}
                ORDER BY imp.data_referencia DESC, imp.id DESC LIMIT 1
            """), scoped_params).mappings().first()
        except SQLAlchemyError:
            db.session.rollback()
            return jsonify(self._empty(start, end, available=False)), 200

        evolution_by_day = {row["data"]: row for row in evolution}
        business_day_evolution, cursor = [], start
        while cursor <= end:
            if cursor.weekday() < 5:
                row = evolution_by_day.get(cursor)
                business_day_evolution.append({
                    "data": cursor,
                    "total": int(row["total"] or 0) if row else 0,
                    **{indicator: int(row[indicator] or 0) if row else 0 for indicator in INDICATORS},
                })
            cursor += timedelta(days=1)
        payload = self._empty(start, end)
        payload.update({
            "indicadores": {key: int(aggregate[key] or 0) for key in ("total", *INDICATORS, "colaboradores", "pendentes_vinculo")},
            "evolucao": [{key: (row[key].isoformat() if key == "data" else int(row[key] or 0)) for key in ("data", "total", *INDICATORS)} for row in business_day_evolution],
            "departamentos": departments,
            "ofensores": [{key: row[key] for key in ("colaborador", "matricula", "contrato", "total", *INDICATORS)} for row in offenders],
            "filtros": {
                "contratos": [{"label": value, "value": value} for value in filter_contracts],
                "departamentos": [{"label": str(value), "value": str(value)} for value in filter_departments],
            },
            "ultima_importacao": {"data_referencia": latest["data_referencia"].isoformat(), "arquivo": latest["arquivo_origem"]} if latest else None,
        })
        return jsonify(payload), 200
