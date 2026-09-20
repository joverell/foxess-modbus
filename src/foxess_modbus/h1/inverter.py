"""Inverter telemetry and state component for FoxESS H1."""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from ..const import InverterState
from ..model import FoxessComponent


class FoxessH1InverterState(FoxessComponent):
    """Internal inverter telemetry for FoxESS H1."""

    inverter_temp = gauge(31018, 0.1, signed=True, unit="°C")
    ambient_temp = gauge(31019, 0.1, signed=True, unit="°C")
    raw_state = integer(31027, signed=False)

    @property
    def state(self) -> InverterState:
        """Inverter operating status mapped to InverterState enum."""
        if self.raw_state is None:
            return InverterState.UNKNOWN
        try:
            return InverterState(self.raw_state)
        except ValueError:
            return InverterState.UNKNOWN
