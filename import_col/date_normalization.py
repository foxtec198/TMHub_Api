"""Normalização centralizada de datas usadas na importação de colaboradores."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from math import isfinite
from numbers import Real
from typing import Any


_EMPTY_VALUES = {"", "-", "null", "none", "n/a", "na"}
_DATE_FORMATS = (
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)
_EXCEL_EPOCH = date(1899, 12, 30)


def normalize_import_date(value: Any, *, field: str = "data") -> date | None:
    """Converte datas de planilha/JSON/banco para ``date`` sem alterar o dia.

    Aceita ``date``, ``datetime``, strings ISO ou brasileiras e seriais do
    Excel. Valores vazios retornam ``None``; valores não interpretáveis geram
    ``ValueError`` para que a importação registre a linha inválida sem abortar
    o arquivo inteiro.
    """
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, datetime):
        # Não converte fuso: campos cadastrais representam uma data civil.
        return value.date()
    if isinstance(value, date):
        return value

    to_python = getattr(value, "to_pydatetime", None)
    if callable(to_python):
        return normalize_import_date(to_python(), field=field)

    if isinstance(value, (Real, Decimal)) and not isinstance(value, bool):
        serial = float(value)
        if not isfinite(serial) or serial < 1:
            raise ValueError(f"{field} inválida: {value!r}")
        try:
            return _EXCEL_EPOCH + timedelta(days=int(serial))
        except OverflowError as error:
            raise ValueError(f"{field} inválida: {value!r}") from error

    raw = str(value).strip()
    if raw.casefold() in _EMPTY_VALUES:
        return None

    for pattern in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, pattern).date()
        except ValueError:
            continue

    try:
        # Aceita ISO com horário e offset sem aplicar conversão de timezone.
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError as error:
        raise ValueError(f"{field} inválida: {value!r}") from error
