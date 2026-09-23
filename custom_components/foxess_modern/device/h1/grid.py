"""Grid and power flow component for FoxESS H1 / AC1."""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from ..model import FoxessComponent


class FoxessH1Grid(FoxessComponent):
    """Grid metering and load measurements for single-phase H1 inverters."""

    voltage = gauge(31006, 0.1, signed=False, unit="V")
    current = gauge(31007, 0.1, signed=False, unit="A")
    power = integer(31008, signed=True, unit="W")
    frequency = gauge(31009, 0.01, signed=False, unit="Hz")
    load_power = integer(31016, signed=True, unit="W")
    ct_meter_power = integer(31014, signed=True, unit="W")

    # EPS (Emergency Power Supply) telemetry
    eps_voltage = gauge(31010, 0.1, signed=False, unit="V")
    eps_current = gauge(31011, 0.1, signed=True, unit="A")
    eps_power = integer(31012, signed=True, unit="W")
    eps_frequency = gauge(31013, 0.01, signed=False, unit="Hz")

    @property
    def grid_import_power(self) -> float:
        """Instantaneous power imported from the grid in Watts."""
        if self.ct_meter_power is None:
            return 0.0
        return float(abs(self.ct_meter_power)) if self.ct_meter_power < 0 else 0.0

    @property
    def grid_export_power(self) -> float:
        """Instantaneous power exported to the grid in Watts."""
        if self.ct_meter_power is None:
            return 0.0
        return float(self.ct_meter_power) if self.ct_meter_power > 0 else 0.0
