"""Nomes enviados ao Jellyfin, sem conexao com o banco ou servidor real."""
from types import SimpleNamespace
import unittest

from services.oidc import _claims, _username


class OidcUsernameTest(unittest.TestCase):
    def user(self, name, user_id=42):
        return SimpleNamespace(id=user_id, nome=name, email="test@example.invalid")

    def test_requested_names(self):
        for name, expected in [("Amanda Lemos", "amanda.lemos"), ("Timo Bot", "timo.bot")]:
            with self.subTest(name=name):
                self.assertEqual(_username(self.user(name)), expected)

    def test_only_first_two_names(self):
        self.assertEqual(_username(self.user("Amanda Lemos Silva")), "amanda.lemos")

    def test_accents_case_and_whitespace(self):
        self.assertEqual(_username(self.user("  JOAO\u0303   GONÇALVES\tSilva  ")), "joao.goncalves")

    def test_punctuation_is_removed(self):
        self.assertEqual(_username(self.user("Ana-Maria D'Avila")), "anamaria.davila")

    def test_single_name(self):
        self.assertEqual(_username(self.user("Amanda")), "amanda")

    def test_unusable_name_keeps_id_fallback(self):
        for name in (None, "", "   ", "... ---", "机器人"):
            with self.subTest(name=name):
                self.assertEqual(_username(self.user(name)), "tmhub-42")

    def test_claims_keep_original_name_and_stable_subject(self):
        claims = _claims(self.user("Amanda Lemos", 28))
        self.assertEqual(claims["preferred_username"], "amanda.lemos")
        self.assertEqual(claims["name"], "Amanda Lemos")
        self.assertEqual(claims["sub"], "28")

    def test_namesakes_remain_distinct_identities(self):
        first = _claims(self.user("Amanda Lemos", 28))
        second = _claims(self.user("Amanda Lemos", 29))
        self.assertEqual(first["preferred_username"], second["preferred_username"])
        self.assertNotEqual(first["sub"], second["sub"])


if __name__ == "__main__":
    unittest.main()
