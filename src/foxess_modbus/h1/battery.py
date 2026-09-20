"""Battery component for FoxESS H1 / AC1."""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from ..model import FoxessComponent


class FoxessH1Battery(FoxessComponent):
    """Battery state and measurements for FoxESS H1 inverters."""

    voltage = gauge(31020, 0.1, signed=False, unit="V")
    current = gauge(31021, 0.1, signed=True, unit="A")
    power = integer(31022, signed=True, unit="W")
    temperature = gauge(31023, 0.1, signed=True, unit="°C")
    soc = integer(31024, signed=False, unit="%")

    @property
    def charge_power(self) -> float:
        """Battery charging power in Watts (positive when charging)."""
        if self.power is None:
            return 0.0
        return float(abs(self.power)) if self.power < 0 else 0.0

    @property
    def discharge_power(self) -> float:
        """Battery discharging power in Watts (positive when discharging)."""
        if self.power is None:
            return 0.0
        return float(self.power) if self.power > 0 else 0.0
