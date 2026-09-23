"""Battery Management System (BMS) detailed telemetry for FoxESS KH10."""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from ..model import FoxessComponent


class FoxessKH10BMS(FoxessComponent):
    """Detailed BMS telemetry registers on FoxESS KH10 (holding 37617..37632).

    max_gap is set to 0 to prevent block-reading across unsupported register ranges.
    """

    register_space = "holding"
    max_gap = 0

    bms_cell_temp_high = gauge(37617, 0.1, signed=True, unit="°C")
    bms_cell_temp_low = gauge(37618, 0.1, signed=True, unit="°C")
    bms_cell_mv_high = integer(37619, signed=False, unit="mV")
    bms_cell_mv_low = integer(37620, signed=False, unit="mV")
    battery_soh = integer(37624, signed=False, unit="%")
    bms_kwh_remaining = gauge(37632, 0.01, signed=False, unit="kWh")
