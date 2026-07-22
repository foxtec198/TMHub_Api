import sys
from pathlib import Path

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
from models.rp_requisicao import Requisicao
from services.controle_faltas import AbsenceControlService
from utils.db import db


with app.app_context():
    columns = {column["name"] for column in inspect(db.engine).get_columns("usuarios")}
    if "gerencia_faltas" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE usuarios ADD COLUMN gerencia_faltas BOOLEAN NOT NULL DEFAULT FALSE"))

    absence_columns = {column["name"] for column in inspect(db.engine).get_columns("controle_faltas")}
    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE controle_faltas ALTER COLUMN colaborador_id DROP NOT NULL"))
        connection.execute(text(
            "ALTER TABLE controle_faltas DROP CONSTRAINT IF EXISTS controle_faltas_colaborador_id_fkey"
        ))
        connection.execute(text("""
            ALTER TABLE controle_faltas
            ADD CONSTRAINT controle_faltas_colaborador_id_fkey
            FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id) ON DELETE SET NULL
        """))
        if "colaborador_nome" not in absence_columns:
            connection.execute(text(
                "ALTER TABLE controle_faltas ADD COLUMN colaborador_nome VARCHAR(255) NOT NULL DEFAULT 'Colaborador não encontrado'"
            ))
        if "colaborador_matricula" not in absence_columns:
            connection.execute(text(
                "ALTER TABLE controle_faltas ADD COLUMN colaborador_matricula VARCHAR(50) NULL"
            ))

    created = 0
    for requisition in Requisicao.query.all():
        absence = AbsenceControlService.ensure_for_request(requisition)
        if absence.id is None:
            created += 1
    db.session.commit()
    AbsenceControlService._expire_certificates()
    print(f"Controle de faltas preparado; {created} registros criados a partir das requisições existentes.")
