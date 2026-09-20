"""Inverter health and version component for FoxESS KH10."""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from ..const import InverterState
from ..model import FoxessComponent


class FoxessKH10InverterState(FoxessComponent):
    """Inverter status, temperatures, and firmware versions on FoxESS KH10."""

    inverter_temp = gauge(31018, 0.1, signed=True, unit="°C")
    ambient_temp = gauge(31019, 0.1, signed=True, unit="°C")
    raw_state = integer(31027, signed=False)

    master_version = integer(36001, signed=False)
    slave_version = integer(36002, signed=False)
    manager_version = integer(36003, signed=False)

    @property
    def state(self) -> InverterState | int | None:
        """Inverter operational state enum."""
        if self.raw_state is None:
            return None
        try:
            return InverterState(self.raw_state)
        except ValueError:
            return self.raw_state
