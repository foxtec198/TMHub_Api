import base64
import hashlib
import hmac
import re
from os import getenv

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError


PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9\s]).{8,}$")
DEFAULT_PASSWORD = "Mudar@123"
ARGON2_PREFIX = "$argon2id$"

_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19 * 1024,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

def _pepper():
    value = getenv("PASSWORD_PEPPER")
    if not value or len(value) < 32:
        raise RuntimeError("PASSWORD_PEPPER deve possuir ao menos 32 caracteres.")
    return value.encode("utf-8")


def _peppered(password):
    digest = hmac.new(_pepper(), str(password).encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def is_strong_password(password):
    return bool(PASSWORD_PATTERN.fullmatch(str(password or "")))


def is_default_password(password):
    return hmac.compare_digest(str(password or "").encode("utf-8"), DEFAULT_PASSWORD.encode("utf-8"))


def hash_password(password):
    return _hasher.hash(_peppered(password))


def verify_password(password, stored_hash):
    """Return (valid, legacy_hash, needs_rehash)."""
    stored_hash = str(stored_hash or "")
    if stored_hash.startswith(ARGON2_PREFIX):
        try:
            valid = _hasher.verify(stored_hash, _peppered(password))
            return bool(valid), False, bool(valid and _hasher.check_needs_rehash(stored_hash))
        except (VerifyMismatchError, InvalidHashError):
            return False, False, False

    legacy = hashlib.sha256(str(password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored_hash), True, False
