"""Base model classes for FoxESS Modbus components and devices."""

from __future__ import annotations

from modbus_connection.model import Component

try:
    from modbus_connection.model import Device
except ImportError:
    try:
        from modbus_connection.model.device import Device
    except ImportError:
        from modbus_connection import ModbusUnit

        class Device:
            """Minimal Device protocol fallback."""

            def __init__(self, unit: ModbusUnit) -> None:
                self.modbus_unit = unit

try:
    from modbus_connection.model import Raw
except ImportError:
    try:
        from modbus_connection.model._const import Raw
    except ImportError:
        Raw = dict[str, dict[int, int | bool]]

try:
    from modbus_connection.model import UpdateReport
except ImportError:
    try:
        from modbus_connection.model.device import UpdateReport
    except ImportError:
        from dataclasses import dataclass, field
        from modbus_connection import ModbusError

        @dataclass
        class UpdateReport:
            """What one poll managed to refresh."""

            updated: set[str] = field(default_factory=set)
            failed: dict[str, ModbusError] = field(default_factory=dict)

            @property
            def complete(self) -> bool:
                """Whether every sub-system the poll covered refreshed."""
                return not self.failed


class FoxessComponent(Component):
    """Base class for FoxESS Modbus components.

    max_span controls the maximum contiguous register count requested
    in a single frame. FoxESS AUX UART microcontrollers have limited
    FIFO buffers, so keeping this bounded (max_span = 8) prevents stalls.
    """

    max_span = 8


class FoxessDevice(Device):
    """Base class for FoxESS inverters reached through a ModbusUnit.

    Inherits upstream modbus_connection.model.Device with zero deviation:
    - Fast propagation of ModbusConnectionError on connection loss.
    - Propagation of ModbusTimeoutError when link is dead for coordinator recycling.
    - Recording of individual sub-system errors in report.failed during normal polls.
    """
