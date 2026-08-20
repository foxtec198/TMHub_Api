"""Controle global de manutenção do TMHub.

Enquanto ativo, somente administradores podem utilizar a API. A configuração
fica em variável de ambiente para que a operação possa ser liberada sem uma
nova alteração de código.
"""

from os import getenv


def maintenance_mode_enabled():
    """Retorna se a operação geral deve permanecer em manutenção.

    O padrão é ligado intencionalmente nesta publicação emergencial. Para
    liberar a operação depois, defina ``MAINTENANCE_MODE=false`` no ambiente
    da API e reinicie o serviço.
    """

    return getenv("MAINTENANCE_MODE", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
