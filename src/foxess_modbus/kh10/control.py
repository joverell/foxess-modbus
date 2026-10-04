"""Control and configuration component for FoxESS KH10."""

from __future__ import annotations

from typing import Any

from modbus_connection.model import gauge, int32, integer

from ..const import WorkMode
from ..model import FoxessComponent


class FoxessKH10Control(FoxessComponent):
    """Writable configuration, work modes, and remote power limits."""

    register_space = "holding"
    register_ranges = (
        (41000, 41002),
        (41007, 41008),
        (41009, 41011),
        (46501, 46502),
        (46616, 46617),
    )
    max_gap = 0

    raw_work_mode = integer(41000, writable=True)
    max_charge_current = gauge(41007, 0.1, signed=False, writable=True, unit="A")
    max_discharge_current = gauge(41008, 0.1, signed=False, writable=True, unit="A")
    min_soc = integer(41009, writable=True, unit="%")
    max_soc = integer(41010, writable=True, unit="%")
    min_soc_on_grid = integer(41011, writable=True, unit="%")

    import_power_limit = int32(46501, writable=True, unit="W")
    export_power_limit = int32(46616, writable=True, unit="W")

    def __init__(self, unit: Any) -> None:
        """Initialize KH10 control component with write-only register state tracking."""
        super().__init__(unit)
        self.remote_enable: int = 0
        self.remote_timeout: int = 0
        self.remote_active_power: int = 0

    @property
    def work_mode(self) -> WorkMode | int | None:
        """Active work mode enum."""
        if self.raw_work_mode is None:
            return None
        try:
            return WorkMode(self.raw_work_mode)
        except ValueError:
            return self.raw_work_mode
