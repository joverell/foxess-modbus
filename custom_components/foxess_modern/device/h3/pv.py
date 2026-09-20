"""PV strings component for FoxESS H3 / AC3."""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from ..model import FoxessComponent


class FoxessH3PV(FoxessComponent):
    """PV strings on FoxESS H3 three-phase inverter (2 independent MPPT trackers)."""

    # MPPT 1 / PV String 1
    pv1_voltage = gauge(31000, 0.1, signed=False, unit="V")
    pv1_current = gauge(31001, 0.1, signed=False, unit="A")
    pv1_power = integer(31002, signed=False, unit="W")

    # MPPT 2 / PV String 2
    pv2_voltage = gauge(31003, 0.1, signed=False, unit="V")
    pv2_current = gauge(31004, 0.1, signed=False, unit="A")
    pv2_power = integer(31005, signed=False, unit="W")

    @property
    def pv_power_total(self) -> float:
        """Sum of both PV strings power in Watts."""
        powers = (self.pv1_power, self.pv2_power)
        return float(sum(p for p in powers if p is not None))
