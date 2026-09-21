"""PV strings component for FoxESS H3-Pro (6 strings / 3 MPPT trackers)."""

from __future__ import annotations

from modbus_connection.model import gauge, uint32

from ..model import FoxessComponent


class FoxessH3ProPV(FoxessComponent):
    """PV strings on FoxESS H3-Pro inverter (up to 6 independent strings)."""

    # MPPT 1
    pv1_voltage = gauge(39070, 0.1, signed=False, unit="V")
    pv1_current = gauge(39071, 0.01, signed=False, unit="A")
    pv1_power = uint32(39279, unit="W")

    pv2_voltage = gauge(39072, 0.1, signed=False, unit="V")
    pv2_current = gauge(39073, 0.01, signed=False, unit="A")
    pv2_power = uint32(39281, unit="W")

    # MPPT 2
    pv3_voltage = gauge(39074, 0.1, signed=False, unit="V")
    pv3_current = gauge(39075, 0.01, signed=False, unit="A")
    pv3_power = uint32(39283, unit="W")

    pv4_voltage = gauge(39076, 0.1, signed=False, unit="V")
    pv4_current = gauge(39077, 0.01, signed=False, unit="A")
    pv4_power = uint32(39285, unit="W")

    # MPPT 3
    pv5_voltage = gauge(39078, 0.1, signed=False, unit="V")
    pv5_current = gauge(39079, 0.01, signed=False, unit="A")
    pv5_power = uint32(39287, unit="W")

    pv6_voltage = gauge(39080, 0.1, signed=False, unit="V")
    pv6_current = gauge(39081, 0.01, signed=False, unit="A")
    pv6_power = uint32(39289, unit="W")

    @property
    def pv_power_total(self) -> float:
        """Sum of all 6 PV strings power in Watts."""
        powers = (
            self.pv1_power,
            self.pv2_power,
            self.pv3_power,
            self.pv4_power,
            self.pv5_power,
            self.pv6_power,
        )
        return float(sum(p for p in powers if p is not None))
