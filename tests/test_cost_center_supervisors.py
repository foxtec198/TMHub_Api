"""Testes de escopo com banco SQLite descartável, sem usar o DB_URI real."""
import unittest

from flask import Flask

from migrations.startup import _migrate_cost_center_supervisors
from models.cidades import Cities  # Registra a FK dos centros.
from models.centros_de_custo import CostCenters, centro_custo_supervisores
from models.colaboradores import Employees
from models.empresas import Company
from models.filiais import Branch
from models.usuarios import Users
from services.centros import CostsCenterService
from services.funcionarios import EmployeesService
from utils.db import db
from utils.filial_scope import supervisor_cost_center_ids


class CostCenterSupervisorsTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", TESTING=True)
        db.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        users = [Users(id=1, nome="Admin", role="ADMIN")]
        users += [Users(id=i, nome=f"Supervisor {i}", role="SUPERVISOR") for i in (2, 3, 4)]
        company = Company(id=1, nome="Empresa")
        centers = [CostCenters(id=i, empresa=company, centro_id=i, nome=f"Centro {i}", local=f"Centro {i}") for i in (10, 20, 30)]
        centers[0].supervisores_usuarios = [users[1], users[2]]
        centers[1].supervisores_usuarios = [users[2]]
        branch = Branch(id=2, nome="Filial", usuarios=users, centros_custo=centers)
        db.session.add(branch)
        db.session.add_all([Employees(id=i, matricula=i, nome=f"Colaborador {i}", centro_id=center.id, empresa=company) for i, center in zip((100, 200, 300), centers)])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def lookup(self, user_id, supervisor_id=None, headers=None):
        query = {"contexto": "requisicao"}
        if supervisor_id is not None:
            query["supervisor_usuario_id"] = supervisor_id
        with self.app.test_request_context("/funcionarios", query_string=query, headers=headers):
            response, status = EmployeesService.read.__wrapped__(EmployeesService(), {"id": user_id})
            return response.get_json(), status

    def test_both_supervisors_share_a_center(self):
        self.assertEqual(supervisor_cost_center_ids(2), {10})
        self.assertEqual(supervisor_cost_center_ids(3), {10, 20})
        self.assertEqual([row["id"] for row in self.lookup(2)[0]], [100])
        self.assertEqual([row["id"] for row in self.lookup(3)[0]], [100, 200])

    def test_supervisor_cannot_impersonate_another(self):
        self.assertEqual(self.lookup(2, 3)[1], 403)

    def test_unassigned_supervisor_sees_no_employees(self):
        self.assertEqual(self.lookup(4), ([], 200))

    def test_admin_lookup_respects_selected_supervisor(self):
        self.assertEqual([row["id"] for row in self.lookup(1, 2)[0]], [100])
        self.assertEqual(self.lookup(1)[1], 400)

    def test_global_filter_does_not_expand_responsibility(self):
        self.assertEqual(self.lookup(2, headers={"X-Centro-Custo-Ids": "[20]"}), ([], 200))

    def test_multiselect_validation_and_serialization(self):
        self.assertEqual([row.id for row in CostsCenterService._supervisors([2, 3, 2])], [2, 3])
        with self.assertRaises(ValueError):
            CostsCenterService._supervisors([1])
        payload = CostsCenterService._serialize_center(db.session.get(CostCenters, 10))
        self.assertEqual(payload["supervisor_usuario_ids"], [2, 3])

    def test_legacy_backfill_is_idempotent(self):
        center = db.session.get(CostCenters, 30)
        center.supervisor_usuario_id = 2
        db.session.commit()
        tables = {"centro_de_custo", "centro_custo_supervisores"}
        _migrate_cost_center_supervisors(tables)
        _migrate_cost_center_supervisors(tables)
        self.assertEqual(supervisor_cost_center_ids(2), {10, 30})
        self.assertEqual(db.session.query(centro_custo_supervisores).count(), 4)


if __name__ == "__main__":
    unittest.main()
