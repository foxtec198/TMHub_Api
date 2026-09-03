"""Conversao de decimais da importacao, sem acesso ao banco real."""
from decimal import Decimal
from datetime import date
import unittest
from unittest.mock import MagicMock

from import_col.cadInBd import create_employees, parse_decimal


class ImportDecimalTest(unittest.TestCase):
    def test_dot_is_not_stripped_from_hours_or_salary(self):
        for value, expected in [("220.00", 220), ("220.0", 220), ("180.50", 180.5), ("2500.75", 2500.75), ("1.234", 1.234)]:
            with self.subTest(value=value):
                self.assertEqual(parse_decimal(value), expected)

    def test_brazilian_values_keep_their_decimal_places(self):
        for value, expected in [("220,00", 220), ("2.500,75", 2500.75), ("1.234.567,89", 1234567.89), (" 0,00 ", 0)]:
            with self.subTest(value=value):
                self.assertEqual(parse_decimal(value), expected)

    def test_native_numbers_and_decimal_objects(self):
        for value in (220, 220.0, Decimal("220.00")):
            self.assertEqual(parse_decimal(value), 220)
        self.assertEqual(parse_decimal(Decimal("2500.75")), 2500.75)

    def test_absent_value_respects_default(self):
        for value in (None, "", "  "):
            self.assertIsNone(parse_decimal(value, default=None))
            self.assertEqual(parse_decimal(value), 0.0)

    def test_invalid_values_are_rejected(self):
        for value in ("220.00.00", "1,234.56", "abc", True, float("inf"), float("nan"), "1e9999"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_decimal(value)

    def employee(self):
        return {
            "_matricula": 123, "_empresa_id": 1, "_admissao": date(2025, 1, 10),
            "_centro_db_id": 10, "nome": "Colaborador Teste",
            "hor": "220.00", "salario": "2500.75",
        }

    def test_new_employee_insert_keeps_hours_and_cents(self):
        connection = MagicMock()
        connection.execute.return_value.mappings.return_value = []
        self.assertEqual(create_employees(connection, [self.employee()], positions={}), (1, 0, 0))
        inserted = connection.execute.call_args.args[1][0]
        self.assertEqual(inserted["carga_horaria"], 220)
        self.assertEqual(inserted["salario"], 2500.75)

    def existing(self, hours, salary):
        return {
            "id": 99, "matricula": 123, "empresa_id": 1, "nome": "Colaborador Teste",
            "centro_id": 10, "data_admissao": date(2025, 1, 10),
            "carga_horaria": hours, "salario": salary,
        }

    def test_update_payload_replaces_inflated_values_only(self):
        connection = MagicMock()
        connection.execute.return_value.mappings.return_value = [self.existing(22000, 250075)]
        self.assertEqual(create_employees(connection, [self.employee()], positions={}), (0, 1, 0))
        self.assertEqual(connection.execute.call_args.args[1], [{
            "id": 99, "carga_horaria": 220.0, "salario": 2500.75,
        }])

    def test_already_correct_values_are_not_overwritten(self):
        connection = MagicMock()
        connection.execute.return_value.mappings.return_value = [self.existing(220, Decimal("2500.75"))]
        self.assertEqual(create_employees(connection, [self.employee()], positions={}), (0, 0, 1))
        self.assertEqual(connection.execute.call_count, 1)


if __name__ == "__main__":
    unittest.main()
