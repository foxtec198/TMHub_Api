# Utilitários de validação de campos.
def check_field(**kwargs) -> tuple[bool, str|None]: # Verifica os campos obrigatórios
    faltando = [campo for campo, valor in kwargs.items() if not valor]

    if faltando: return False, f"Faltam os campos: {', '.join(faltando)}"
    return True, None
