"""Inverter model identification and factory helpers."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit
    from modbus_connection.model import Device


_SERIAL_PREFIXES: tuple[tuple[str, str], ...] = (
    ("60KB", "KH"),
    ("60KA", "KH"),
    ("60HB", "H1"),
    ("60HA", "H1"),
    ("60AB", "H1"),  # AC1 / AIO-H1
    ("60AA", "H1"),
    ("60PB", "H3"),
    ("60PA", "H3"),
    ("60TB", "H3_PRO"),  # H3-Pro (6 strings)
    ("60TA", "H3_PRO"),
)

_MODEL_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^KH", re.IGNORECASE), "KH"),
    (re.compile(r"^(?:H1|AC1|AIO-H1|P1)", re.IGNORECASE), "H1"),
    (re.compile(r"^(?:H3-PRO|H3_PRO)", re.IGNORECASE), "H3_PRO"),
    (re.compile(r"^(?:H3|AC3|AIO-H3|P3)", re.IGNORECASE), "H3"),
)


def identify_model(identifier: str) -> str:
    """Identify inverter model family ('KH', 'H1', 'H3', 'H3_PRO') from serial number or model name.

    Returns the identified family string, or 'KH' by default if unknown.
    """
    cleaned = identifier.strip().upper()

    # 1. Check serial prefix
    for prefix, family in _SERIAL_PREFIXES:
        if cleaned.startswith(prefix):
            return family

    # 2. Check model regex
    for pattern, family in _MODEL_PATTERNS:
        if pattern.search(cleaned):
            return family

    return "KH"


def create_inverter(
    unit: ModbusUnit,
    *,
    serial_number: str | None = None,
    model: str | None = None,
) -> Device:
    """Instantiate the appropriate FoxESS inverter device for the given unit and model/serial."""
    # Lazy imports to avoid circular dependencies
    from .h1 import FoxessH1Inverter
    from .h3 import FoxessH3Inverter
    from .h3_pro import FoxessH3ProInverter
    from .kh10 import FoxessKH10Inverter

    target_id = model or serial_number or ""
    family = identify_model(target_id)

    if family == "H1":
        return FoxessH1Inverter(unit, serial_number=serial_number, model=model or "H1")
    if family == "H3_PRO":
        return FoxessH3ProInverter(unit, serial_number=serial_number, model=model or "H3-Pro")
    if family == "H3":
        return FoxessH3Inverter(unit, serial_number=serial_number, model=model or "H3")

    # Default to KH
    return FoxessKH10Inverter(unit, serial_number=serial_number, model=model or "KH10")
