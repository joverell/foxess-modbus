"""Grid and power flow telemetry component for FoxESS KH10."""

from __future__ import annotations

from modbus_connection.model import gauge, int32

from ..model import FoxessComponent


class FoxessKH10Grid(FoxessComponent):
    """Grid telemetry and CT meter measurements on FoxESS KH10."""

    voltage = gauge(31006, 0.1, signed=False, unit="V")
    current = gauge(31007, 0.1, signed=False, unit="A")
    inverter_power = gauge(31008, 1.0, signed=True, unit="W")
    frequency = gauge(31009, 0.01, signed=False, unit="Hz")
    load_power = gauge(31016, 1.0, signed=True, unit="W")

    # EPS (Emergency Power Supply) telemetry
    eps_voltage = gauge(31010, 0.1, signed=False, unit="V")
    eps_current = gauge(31011, 0.1, signed=True, unit="A")
    eps_power = gauge(31012, 1.0, signed=True, unit="W")
    eps_frequency = gauge(31013, 0.01, signed=False, unit="Hz")
    eps_reactive_power = gauge(31014, 1.0, signed=True, unit="var")

    # 32-bit signed CT meter power in Watts (register 39168=high word, 39169=low word)
    # Positive = export to grid, Negative = import from grid
    ct_meter_power = int32(39168, unit="W")

    # Secondary CT meter (e.g. external PV or generator)
    ct2_power = gauge(31015, -1.0, signed=True, unit="W")

    @property
    def grid_import_power(self) -> float:
        """Instantaneous power imported from the grid in Watts."""
        if self.ct_meter_power is not None and self.ct_meter_power < 0:
            return abs(self.ct_meter_power)
        return 0.0

    @property
    def grid_export_power(self) -> float:
        """Instantaneous power exported to the grid in Watts."""
        if self.ct_meter_power is not None and self.ct_meter_power > 0:
            return float(self.ct_meter_power)
        return 0.0
