"""Inverter telemetry and state component for FoxESS H3."""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from ..const import InverterState
from ..model import FoxessComponent


class FoxessH3InverterState(FoxessComponent):
    """Internal inverter telemetry for FoxESS H3."""

    inverter_temp = gauge(31032, 0.1, signed=True, unit="°C")
    ambient_temp = gauge(31033, 0.1, signed=True, unit="°C")
    raw_state = integer(31041, signed=False)

    master_version = integer(30016, signed=False)
    slave_version = integer(30017, signed=False)
    manager_version = integer(30018, signed=False)

    @property
    def state(self) -> InverterState:
        """Inverter operating status mapped to InverterState enum."""
        if self.raw_state is None:
            return InverterState.UNKNOWN
        try:
            return InverterState(self.raw_state)
        except ValueError:
            return InverterState.UNKNOWN
