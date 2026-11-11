"""Política de status das reservas."""

from __future__ import annotations

BILLABLE_STATUS = "CONFIRMED"


def is_billable(status: str) -> bool:
    """Indica se a reserva entra nos totais financeiros e de noites (apenas CONFIRMED)."""
    return status == BILLABLE_STATUS
