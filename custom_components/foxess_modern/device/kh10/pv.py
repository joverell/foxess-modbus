"""PV strings component for FoxESS KH10."""

from __future__ import annotations

from modbus_connection.model import gauge, uint32

from ..model import FoxessComponent


class FoxessKH10PV(FoxessComponent):
    """PV strings on FoxESS KH10 inverter."""

    pv1_voltage = gauge(39070, 0.1, signed=False, unit="V")
    pv1_current = gauge(39071, 0.01, signed=False, unit="A")
    pv1_power = uint32(39279, unit="W")

    pv2_voltage = gauge(39072, 0.1, signed=False, unit="V")
    pv2_current = gauge(39073, 0.01, signed=False, unit="A")
    pv2_power = uint32(39281, unit="W")

    @property
    def pv_power_total(self) -> float:
        """Sum of PV1 and PV2 power in Watts."""
        p1 = self.pv1_power or 0.0
        p2 = self.pv2_power or 0.0
        return float(p1 + p2)
