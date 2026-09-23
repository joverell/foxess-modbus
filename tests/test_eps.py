"""Unit tests for EPS (Emergency Power Supply) telemetry across FoxESS models."""

import pytest
from modbus_connection.mock import MockModbusConnection

from foxess_modbus import FoxessKH10Inverter, FoxessH1Inverter, FoxessH3Inverter


@pytest.mark.asyncio
async def test_kh10_eps_telemetry():
    """Verify single-phase EPS readings on FoxESS KH10."""
    conn = MockModbusConnection()
    unit = conn.for_unit(247)
    unit.holding.update({
        31006: 0,     # Grid voltage 0 during power cut
        31007: 0,
        31008: 0,
        31009: 0,
        31010: 2305,  # EPS Voltage: 230.5 V
        31011: 152,   # EPS Current: 15.2 A
        31012: 3500,  # EPS Power: 3500 W
        31013: 5001,  # EPS Frequency: 50.01 Hz
        31014: 250,   # EPS Reactive Power: 250 var
        31016: 3500,  # House load
        39168: 0,
        39169: 0,
    })

    inverter = FoxessKH10Inverter(unit, serial_number="KH10EPS1234567")
    report = await inverter.async_update_readings()

    assert inverter.grid.eps_voltage == pytest.approx(230.5)
    assert inverter.grid.eps_current == pytest.approx(15.2)
    assert inverter.grid.eps_power == pytest.approx(3500.0)
    assert inverter.grid.eps_frequency == pytest.approx(50.01)
    assert inverter.grid.eps_reactive_power == pytest.approx(250.0)


@pytest.mark.asyncio
async def test_h1_eps_telemetry():
    """Verify single-phase EPS readings on FoxESS H1."""
    conn = MockModbusConnection()
    unit = conn.for_unit(247)
    unit.holding.update({
        31006: 0,
        31007: 0,
        31008: 0,
        31009: 0,
        31010: 2300,  # EPS Voltage: 230.0 V
        31011: 120,   # EPS Current: 12.0 A
        31012: 2760,  # EPS Power: 2760 W
        31013: 5000,  # EPS Frequency: 50.00 Hz
        31014: 0,
        31016: 2760,
    })

    inverter = FoxessH1Inverter(unit, serial_number="H1EPS1234567")
    report = await inverter.async_update_readings()

    assert inverter.grid.eps_voltage == pytest.approx(230.0)
    assert inverter.grid.eps_current == pytest.approx(12.0)
    assert inverter.grid.eps_power == 2760
    assert inverter.grid.eps_frequency == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_h3_eps_telemetry():
    """Verify three-phase EPS readings and total calculation on FoxESS H3."""
    conn = MockModbusConnection()
    unit = conn.for_unit(247)
    unit.holding.update({
        31006: 0,
        31007: 0,
        31008: 0,
        31009: 0,
        31010: 0,
        31011: 0,
        31012: 0,
        31013: 0,
        31014: 0,
        31015: 0,
        31022: 1500,  # EPS Power Phase R: 1500 W
        31023: 1200,  # EPS Power Phase S: 1200 W
        31024: 1800,  # EPS Power Phase T: 1800 W
        31025: 5002,  # EPS Frequency: 50.02 Hz
    })

    inverter = FoxessH3Inverter(unit, serial_number="H3EPS1234567")
    report = await inverter.async_update_readings()

    assert inverter.grid.eps_power_r == 1500
    assert inverter.grid.eps_power_s == 1200
    assert inverter.grid.eps_power_t == 1800
    assert inverter.grid.eps_frequency == pytest.approx(50.02)
    assert inverter.grid.eps_power_total == 4500.0
