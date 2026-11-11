"""Conversão de valores para BRL."""

from __future__ import annotations

from decimal import Decimal

from ..exceptions import InputFileError


def convert_to_brl(amount: Decimal, currency: str, rates: dict[str, Decimal]) -> Decimal:
    """Converte um valor na moeda informada para BRL (``amount * rate_to_brl``), em Decimal exato."""
    try:
        rate = rates[currency.upper()]
    except KeyError as err:
        raise InputFileError(f"moeda sem taxa de câmbio: {currency}") from err
    return amount * rate
