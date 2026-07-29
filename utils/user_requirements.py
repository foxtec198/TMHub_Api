import base64
import binascii
import re


PHOTO_PATTERN = re.compile(r"^data:image/(png|jpe?g|webp);base64,([A-Za-z0-9+/=]+)$")
MAX_PHOTO_BYTES = 1_500_000


def normalize_cpf(value):
    return re.sub(r"\D", "", str(value or ""))


def is_valid_cpf(value):
    cpf = normalize_cpf(value)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for size in (9, 10):
        total = sum(int(cpf[index]) * (size + 1 - index) for index in range(size))
        digit = (total * 10) % 11
        if digit == 10:
            digit = 0
        if digit != int(cpf[size]):
            return False
    return True


def validate_profile_photo(value):
    value = str(value or "")
    if len(value) > 2_100_000:
        return False
    match = PHOTO_PATTERN.fullmatch(value)
    if not match:
        return False
    try:
        content = base64.b64decode(match.group(2), validate=True)
    except (ValueError, binascii.Error):
        return False
    if not content or len(content) > MAX_PHOTO_BYTES:
        return False
    kind = match.group(1).lower()
    if kind == "png":
        return content.startswith(b"\x89PNG\r\n\x1a\n") and content.endswith(b"\x00\x00\x00\x00IEND\xaeB`\x82")
    if kind in {"jpg", "jpeg"}:
        return content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9")
    return len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"


def refresh_user_requirements(user):
    user.cpf_pendente = not is_valid_cpf(user.cpf)
    user.foto_pendente = False
    user.primeiro_acesso = bool(user.cpf_pendente)


def auth_requirements(user, hash_needs_migration=False):
    cpf_pending = bool(user.cpf_pendente)
    photo_pending = False
    password_required = bool(user.troca_senha_obrigatoria)
    default_password = bool(user.senha_padrao)
    first_access = cpf_pending
    mandatory = cpf_pending or password_required
    return {
        "primeiro_acesso": first_access,
        "cpf_pendente": cpf_pending,
        "foto_pendente": photo_pending,
        "troca_senha_obrigatoria": password_required,
        "senha_padrao": default_password,
        "hash_precisa_migracao": bool(hash_needs_migration),
        "pendencia_obrigatoria": mandatory,
        "interacao_pendente": mandatory or default_password,
    }
