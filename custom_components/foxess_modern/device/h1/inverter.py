"""Inverter telemetry and state component for FoxESS H1."""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from ..const import InverterState
from ..model import FoxessComponent


class FoxessH1InverterState(FoxessComponent):
    """Internal inverter telemetry for FoxESS H1."""

    version_is_hex: bool = False

    inverter_temp = gauge(31018, 0.1, signed=True, unit="°C")
    ambient_temp = gauge(31019, 0.1, signed=True, unit="°C")
    raw_state = integer(31027, signed=False)

    master_version = integer(30016, signed=False)
    slave_version = integer(30017, signed=False)
    manager_version = integer(30018, signed=False)

    STATE_MAP: dict[int, InverterState] = {
        0: InverterState.WAITING,
        1: InverterState.CHECKING,
        2: InverterState.ON_GRID,
        3: InverterState.OFF_GRID,
        4: InverterState.RECOVERABLE_FAULT,
        5: InverterState.UNRECOVERABLE_FAULT,
    }

    @property
    def state(self) -> InverterState | None:
        """Inverter operating status mapped to InverterState enum."""
        if self.raw_state is None:
            return None
        return self.STATE_MAP.get(self.raw_state, InverterState.UNKNOWN)
