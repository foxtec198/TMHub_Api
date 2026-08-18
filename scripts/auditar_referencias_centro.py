"""Auditoria somente leitura dos relacionamentos atuais de centro de custo."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app import app
from utils.db import db


def main():
    with app.app_context():
        print("DATABASE", db.session.execute(text("SELECT current_database()")).scalar())
        foreign_keys = db.session.execute(text("""
            SELECT tc.table_name, kcu.column_name,
                   ccu.table_name AS referenced_table,
                   ccu.column_name AS referenced_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND ccu.table_name = 'centro_de_custo'
            ORDER BY tc.table_name, kcu.column_name
        """)).all()
        print("CENTER_FKS", foreign_keys)
        columns = db.session.execute(text("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND (column_name ILIKE '%centro%' OR column_name = 'cc')
            ORDER BY table_name, column_name
        """)).all()
        print("CENTER_COLUMNS", columns)
    return 0


if __name__ == "__main__":
    status = main()
    sys.stdout.flush()
    os._exit(status)
