import sys
from pathlib import Path

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
from utils.db import db


with app.app_context():
    columns = {column["name"] for column in inspect(db.engine).get_columns("ad_vagas")}
    if "colaborador_entrada_matricula" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE ad_vagas ADD COLUMN colaborador_entrada_matricula VARCHAR(50) NULL"
            ))
            connection.execute(text("""
                UPDATE ad_vagas AS vaga
                SET colaborador_entrada_matricula = colaborador.matricula
                FROM colaboradores AS colaborador
                WHERE vaga.colaborador_entrada_id = colaborador.id
                  AND vaga.colaborador_entrada_matricula IS NULL
            """))
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_ad_vagas_colaborador_entrada_matricula "
                "ON ad_vagas (colaborador_entrada_matricula)"
            ))
        print("Coluna ad_vagas.colaborador_entrada_matricula criada e preenchida.")
    else:
        print("Coluna ad_vagas.colaborador_entrada_matricula ja existe.")

    # A regra antiga exigia que o colaborador já existisse no cadastro. A
    # matrícula digitada passa a ser uma alternativa válida ao vínculo por ID.
    with db.engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE ad_vagas DROP CONSTRAINT IF EXISTS ck_ad_vagas_conclusao_obrigatoria"
        ))
        connection.execute(text("""
            ALTER TABLE ad_vagas
            ADD CONSTRAINT ck_ad_vagas_conclusao_obrigatoria CHECK (
                status <> 'concluido'
                OR (
                    (
                        colaborador_entrada_id IS NOT NULL
                        OR NULLIF(colaborador_entrada_matricula, '') IS NOT NULL
                    )
                    AND data_inicio IS NOT NULL
                    AND concluido_por_usuario_id IS NOT NULL
                    AND concluido_em IS NOT NULL
                    AND horario_trabalho_id IS NOT NULL
                )
            )
        """))
    print("Constraint de conclusão atualizada para aceitar matrícula sem colaborador cadastrado.")
