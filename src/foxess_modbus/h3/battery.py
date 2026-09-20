"""Battery component for FoxESS H3."""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from ..model import FoxessComponent


class FoxessH3Battery(FoxessComponent):
    """High-voltage battery state and measurements for FoxESS H3."""

    voltage = gauge(31034, 0.1, signed=False, unit="V")
    current = gauge(31035, 0.1, signed=True, unit="A")
    power = integer(31036, signed=True, unit="W")
    temperature = gauge(31037, 0.1, signed=True, unit="°C")
    soc = integer(31038, signed=False, unit="%")

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
