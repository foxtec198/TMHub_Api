from datetime import datetime, time
from sqlalchemy import or_
from models.rp_historico import History


def _get_datetime_range(period):
    """
    Converte:
        2026-08-01
        2026-08-31

    para:
        2026-08-01 00:00:00
        2026-08-31 23:59:59.999999
    """

    start_date = datetime.fromisoformat(
        period["start"]
    ).date()

    end_date = datetime.fromisoformat(
        period["end"]
    ).date()

    start = datetime.combine(
        start_date,
        time.min
    )

    end = datetime.combine(
        end_date,
        time.max
    )

    return start, end


def faltas_periodo(entities):
    period = entities["period"]

    start, end = _get_datetime_range(
        period
    )

    total = (
        History.query
        .filter(
            History.created_at.between(
                start,
                end
            )
        )
        .count()
    )

    return {
        "total": total,
        "period_label": period["label"]
    }


def reposicoes_periodo(entities):
    period = entities["period"]

    start, end = _get_datetime_range(
        period
    )

    total = (
        History.query
        .filter(
            History.created_at.between(
                start,
                end
            ),
            History.reserva_id != 0
        )
        .count()
    )

    return {
        "total": total,
        "period_label": period["label"]
    }


def postos_descobertos(entities):
    period = entities["period"]

    start, end = _get_datetime_range(
        period
    )

    total = (
        History.query
        .filter(
            History.created_at.between(
                start,
                end
            ),
            or_(
                History.reserva_id == 0,
                History.reserva_id.is_(None)
            )
        )
        .count()
    )

    return {
        "total": total,
        "period_label": period["label"]
    }


def navegar_faltas(entities):
    return {
        "action": "navigate",
        "path": "/controle-faltas"
    }


def navegar_colaboradores(entities):
    return {
        "action": "navigate",
        "path": "/colaboradores"
    }


HANDLERS = {
    "faltas_periodo": faltas_periodo,
    "reposicoes_periodo": reposicoes_periodo,
    "postos_descobertos": postos_descobertos,

    "navegar_faltas": navegar_faltas,
    "navegar_colaboradores": navegar_colaboradores,
}


def execute_intent(intent, entities):
    handler = HANDLERS.get(intent)

    if not handler:
        raise ValueError(
            f"Intent sem handler cadastrado: {intent}"
        )

    return handler(entities)