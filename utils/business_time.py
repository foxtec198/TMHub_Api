# Utilitários de cálculo de horário comercial.
# Biblioteca padrão.
from datetime import datetime as dt, time, timedelta
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def business_hours_between(start, end, timezone=DEFAULT_TIMEZONE):
    """Conta horas corridas apenas de segunda a sexta, ignorando fins de semana."""
    if not start or not end:
        return 0.0

    start = _localized(start, timezone)
    end = _localized(end, timezone)
    if end <= start:
        return 0.0

    total_seconds = 0.0
    current_date = start.date()
    last_date = end.date()

    while current_date <= last_date:
        if current_date.weekday() < 5:
            day_start = dt.combine(current_date, time.min, tzinfo=timezone)
            day_end = day_start + timedelta(days=1)
            interval_start = max(start, day_start)
            interval_end = min(end, day_end)
            if interval_end > interval_start:
                total_seconds += (interval_end - interval_start).total_seconds()
        current_date += timedelta(days=1)

    return total_seconds / 3600


def _localized(value, timezone):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone)
    return value.astimezone(timezone)
