"""Helpers for converting between user inputs and internal integer units."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation


class ConversionError(ValueError):
    pass


def string_to_unit(value: str, multiplier: int) -> int:
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ConversionError(f"Invalid decimal value: {value}") from exc
    quantized = (amount * multiplier).quantize(Decimal(1))
    if quantized < 0:
        raise ConversionError("Amount must be positive")
    return int(quantized)


def unit_to_decimal(value: int, multiplier: int) -> Decimal:
    return Decimal(value) / Decimal(multiplier)
