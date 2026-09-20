"""Grid and power flow component for FoxESS H3 (three-phase)."""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from ..model import FoxessComponent


class FoxessH3Grid(FoxessComponent):
    """Three-phase grid measurements (Phase R, S, T) for FoxESS H3."""

    # Phase R
    voltage_r = gauge(31006, 0.1, signed=False, unit="V")
    current_r = gauge(31009, 0.1, signed=False, unit="A")
    power_r = integer(31012, signed=True, unit="W")

    # Phase S
    voltage_s = gauge(31007, 0.1, signed=False, unit="V")
    current_s = gauge(31010, 0.1, signed=False, unit="A")
    power_s = integer(31013, signed=True, unit="W")

    # Phase T
    voltage_t = gauge(31008, 0.1, signed=False, unit="V")
    current_t = gauge(31011, 0.1, signed=False, unit="A")
    power_t = integer(31014, signed=True, unit="W")

    frequency = gauge(31015, 0.01, signed=False, unit="Hz")

    @property
    def grid_power_total(self) -> float:
        """Sum of AC power across all 3 phases in Watts."""
        phases = (self.power_r, self.power_s, self.power_t)
        return float(sum(p for p in phases if p is not None))
