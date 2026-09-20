"""PV strings component for FoxESS KH10."""

from __future__ import annotations

from modbus_connection.model import gauge, uint32

from ..model import FoxessComponent


class FoxessKH10PV(FoxessComponent):
    """PV strings on FoxESS KH10 inverter (4 independent MPPT trackers)."""

    # MPPT 1 / PV String 1
    pv1_voltage = gauge(39070, 0.1, signed=False, unit="V")
    pv1_current = gauge(39071, 0.01, signed=False, unit="A")
    pv1_power = uint32(39279, unit="W")

    # MPPT 2 / PV String 2
    pv2_voltage = gauge(39072, 0.1, signed=False, unit="V")
    pv2_current = gauge(39073, 0.01, signed=False, unit="A")
    pv2_power = uint32(39281, unit="W")

    # MPPT 3 / PV String 3
    pv3_voltage = gauge(39074, 0.1, signed=False, unit="V")
    pv3_current = gauge(39075, 0.01, signed=False, unit="A")
    pv3_power = uint32(39283, unit="W")

    # MPPT 4 / PV String 4
    pv4_voltage = gauge(39076, 0.1, signed=False, unit="V")
    pv4_current = gauge(39077, 0.01, signed=False, unit="A")
    pv4_power = uint32(39285, unit="W")

    @property
    def pv_power_total(self) -> float:
        """Sum of all 4 PV strings power in Watts."""
        powers = (self.pv1_power, self.pv2_power, self.pv3_power, self.pv4_power)
        return float(sum(p for p in powers if p is not None))
