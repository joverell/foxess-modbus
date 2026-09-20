"""Control and configuration component for FoxESS KH10."""

from __future__ import annotations

from modbus_connection.model import int32, integer

from ..const import WorkMode
from ..model import FoxessComponent


class FoxessKH10Control(FoxessComponent):
    """Writable configuration, work modes, and remote power limits."""

    raw_work_mode = integer(41000, writable=True)
    min_soc = integer(41009, writable=True, unit="%")
    max_soc = integer(41010, writable=True, unit="%")
    min_soc_on_grid = integer(41011, writable=True, unit="%")

    # Export power limit (signed 32-bit integer in Watts)
    export_power_limit = int32(46616, writable=True, unit="W")

    # Remote control registers
    remote_enable = integer(44000, writable=True)
    remote_timeout = integer(44001, writable=True)
    # Active power: signed 16-bit (+ve discharge to grid, -ve charge from grid)
    remote_active_power = integer(44002, signed=True, writable=True, unit="W")

    @property
    def work_mode(self) -> WorkMode | int | None:
        """Active work mode enum."""
        if self.raw_work_mode is None:
            return None
        try:
            return WorkMode(self.raw_work_mode)
        except ValueError:
            return self.raw_work_mode
