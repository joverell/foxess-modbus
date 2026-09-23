"""Inverter health and version component for FoxESS KH10."""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from ..const import InverterState
from ..model import FoxessComponent


class FoxessKH10FirmwareVersion(FoxessComponent):
    """Firmware version registers on FoxESS KH10 (holding 36001..36003).

    Polled on the slower settings cycle (60s) to keep the 15s telemetry loop lean.
    """

    master_version = integer(36001, signed=False)
    slave_version = integer(36002, signed=False)
    manager_version = integer(36003, signed=False)


class FoxessKH10InverterState(FoxessComponent):
    """Inverter status and temperatures on FoxESS KH10."""

    inverter_temp = gauge(31018, 0.1, signed=True, unit="°C")
    ambient_temp = gauge(31019, 0.1, signed=True, unit="°C")
    raw_state = integer(31027, signed=False)

    def __init__(
        self, unit: Any, versions: FoxessKH10FirmwareVersion | None = None
    ) -> None:
        """Initialize inverter state component."""
        super().__init__(unit)
        self._versions = versions

    @property
    def master_version(self) -> int | None:
        """Master firmware version."""
        return self._versions.master_version if self._versions else None

    @property
    def slave_version(self) -> int | None:
        """Slave firmware version."""
        return self._versions.slave_version if self._versions else None

    @property
    def manager_version(self) -> int | None:
        """Manager firmware version."""
        return self._versions.manager_version if self._versions else None

    @property
    def state(self) -> InverterState | int | None:
        """Inverter operational state enum."""
        if self.raw_state is None:
            return None
        try:
            return InverterState(self.raw_state)
        except ValueError:
            return self.raw_state

