from hashlib import sha256

def check_field(**kwargs) -> tuple[bool, str|None]: # Verifica os campos obrigatórios
    faltando = [campo for campo, valor in kwargs.items() if not valor]

    if faltando: return False, f"Faltam os campos: {', '.join(faltando)}"
    return True, None

def check_password_hash(pwd: str, hash: str) -> bool: # Confirma o hash do password
    if sha256(str(pwd).encode()).hexdigest() == hash: return True
    return False