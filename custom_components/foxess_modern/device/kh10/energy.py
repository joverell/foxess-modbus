"""Hardware cumulative and daily energy counters for FoxESS KH10."""

from __future__ import annotations

from modbus_connection.model import gauge, uint32

from ..model import FoxessComponent


class FoxessKH10Energy(FoxessComponent):
    """Inverter hardware cumulative and daily energy registers (holding 32000..32023).

    max_gap is set to 0 to prevent block-reading across non-contiguous or sensitive registers
    on FoxESS KH firmware.
    """

    register_space = "holding"
    max_gap = 0

    # Solar generation (kWh)
    solar_energy_total = uint32(32000, scale=0.1, unit="kWh")
    solar_energy_today = gauge(32002, 0.1, signed=False, unit="kWh")

    # Battery charge (kWh)
    battery_charge_energy_total = uint32(32003, scale=0.1, unit="kWh")
    battery_charge_energy_today = gauge(32005, 0.1, signed=False, unit="kWh")

    # Battery discharge (kWh)
    battery_discharge_energy_total = uint32(32006, scale=0.1, unit="kWh")
    battery_discharge_energy_today = gauge(32008, 0.1, signed=False, unit="kWh")

    # Grid feed-in / export (kWh)
    grid_export_energy_total = uint32(32009, scale=0.1, unit="kWh")
    grid_export_energy_today = gauge(32011, 0.1, signed=False, unit="kWh")

    # Grid consumption / import (kWh)
    grid_import_energy_total = uint32(32012, scale=0.1, unit="kWh")
    grid_import_energy_today = gauge(32014, 0.1, signed=False, unit="kWh")

    # Inverter yield (kWh)
    total_yield_total = uint32(32015, scale=0.1, unit="kWh")
    total_yield_today = gauge(32017, 0.1, signed=False, unit="kWh")

    # Inverter input energy (kWh)
    input_energy_total = uint32(32018, scale=0.1, unit="kWh")
    input_energy_today = gauge(32020, 0.1, signed=False, unit="kWh")

    # House load energy (kWh)
    load_energy_total = uint32(32021, scale=0.1, unit="kWh")
    load_energy_today = gauge(32023, 0.1, signed=False, unit="kWh")
