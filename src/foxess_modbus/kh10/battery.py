"""Battery telemetry component for FoxESS KH10."""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from ..model import FoxessComponent


class FoxessKH10Battery(FoxessComponent):
    """Battery management system telemetry on FoxESS KH10."""

    voltage = gauge(31020, 0.1, signed=False, unit="V")
    current = gauge(31021, 0.1, signed=True, unit="A")
    power = gauge(31022, 1.0, signed=True, unit="W")  # +ve = discharge, -ve = charge
    soc = integer(31024, signed=False, unit="%")
    temperature = gauge(31023, 0.1, signed=True, unit="°C")
    charge_rate_max = gauge(31025, 0.1, signed=False, unit="A")
    discharge_rate_max = gauge(31026, 0.1, signed=False, unit="A")

    @property
    def charge_power(self) -> float:
        """Instantaneous charging power in Watts."""
        if self.power is not None and self.power < 0:
            return abs(self.power)
        return 0.0

    @property
    def discharge_power(self) -> float:
        """Instantaneous discharging power in Watts."""
        if self.power is not None and self.power > 0:
            return self.power
        return 0.0
