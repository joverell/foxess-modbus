"""Control and configuration component for FoxESS H1."""

from __future__ import annotations

from modbus_connection.model import integer

from ..const import WorkMode
from ..model import FoxessComponent


class FoxessH1Control(FoxessComponent):
    """Writable registers for FoxESS H1 inverter configuration."""

    raw_work_mode = integer(41000, writable=True)
    min_soc = integer(41009, writable=True, unit="%")
    max_soc = integer(41010, writable=True, unit="%")

    # Remote charge/discharge overrides
    remote_enable = integer(44000, writable=True)
    remote_timeout = integer(44001, writable=True, unit="s")
    remote_active_power = integer(44002, signed=True, writable=True, unit="W")

    @property
    def work_mode(self) -> WorkMode:
        """Inverter work mode mapped to WorkMode enum."""
        if self.raw_work_mode is None:
            return WorkMode.UNKNOWN
        try:
            return WorkMode(self.raw_work_mode)
        except ValueError:
            return WorkMode.UNKNOWN
