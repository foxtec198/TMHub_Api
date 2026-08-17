# Utilitários de autenticação de agendamentos.
"""Alias temporário para a autenticação legada do Scheduler."""

# Módulos internos da aplicação.
from utils.tm_ops_auth import (
    decode_tm_ops_session as decode_schedular_session,
    issue_tm_ops_token as issue_schedular_token,
    tm_ops_route as schedular_route,
    tmhub_admin_session,
    verify_tm_ops_password as verify_schedular_password,
)
