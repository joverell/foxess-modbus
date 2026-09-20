"""Unit tests for FoxESS H1 inverter model."""

import pytest
from modbus_connection.mock import MockModbusConnection

from foxess_modbus import FoxessH1Inverter, InverterState, WorkMode


@pytest.fixture
def h1_unit():
    """Create a mock unit with representative FoxESS H1 holding registers."""
    conn = MockModbusConnection()
    unit = conn.for_unit(247)

    unit.holding.update({
        # PV registers (2 MPPT trackers)
        31000: 3600,  # PV1 Voltage: 360.0 V
        31001: 85,    # PV1 Current: 8.5 A
        31002: 3060,  # PV1 Power: 3060 W
        31003: 3550,  # PV2 Voltage: 355.0 V
        31004: 80,    # PV2 Current: 8.0 A
        31005: 2840,  # PV2 Power: 2840 W

        # Grid registers (single-phase)
        31006: 2400,  # Grid Voltage: 240.0 V
        31007: 245,   # Inverter Current: 24.5 A
        31008: 5500,  # Inverter Power: 5500 W
        31009: 5001,  # Grid Frequency: 50.01 Hz
        31016: 1200,  # Load Power: 1200 W
        31014: -400,  # CT meter power: -400 W (importing)

        # Inverter health
        31018: 410,   # Inverter Temp: 41.0 °C
        31019: 220,   # Ambient Temp: 22.0 °C
        31027: 2,     # State: On-grid

        # Battery registers
        31020: 3800,  # Battery Voltage: 380.0 V
        31021: 120,   # Battery Current: 12.0 A (discharging)
        31022: 4560,  # Battery Power: 4560 W
        31023: 250,   # Battery Temp: 25.0 °C
        31024: 78,    # Battery SOC: 78%

        # Control registers
        41000: 0,     # Work Mode: Self Use
        41009: 10,    # Min SOC: 10%
        41010: 100,   # Max SOC: 100%
        44000: 0,     # Remote Enable: Off
        44001: 0,     # Remote Timeout
        44002: 0,     # Remote Active Power
    })
    return unit


@pytest.mark.asyncio
async def test_h1_readings(h1_unit):
    """Test polling telemetry readings on FoxESS H1."""
    inverter = FoxessH1Inverter(h1_unit, serial_number="60HB50123456789")
    report = await inverter.async_update_readings()

    assert "pv" in report.updated
    assert "battery" in report.updated
    assert "grid" in report.updated
    assert "inverter" in report.updated
    assert not report.failed

    # PV checks
    assert inverter.pv.pv1_voltage == pytest.approx(360.0)
    assert inverter.pv.pv1_current == pytest.approx(8.5)
    assert inverter.pv.pv1_power == 3060
    assert inverter.pv.pv2_voltage == pytest.approx(355.0)
    assert inverter.pv.pv2_current == pytest.approx(8.0)
    assert inverter.pv.pv2_power == 2840
    assert inverter.pv.pv_power_total == pytest.approx(5900.0)

    # Grid checks
    assert inverter.grid.voltage == pytest.approx(240.0)
    assert inverter.grid.current == pytest.approx(24.5)
    assert inverter.grid.power == 5500
    assert inverter.grid.frequency == pytest.approx(50.01)
    assert inverter.grid.load_power == 1200
    assert inverter.grid.grid_import_power == pytest.approx(400.0)
    assert inverter.grid.grid_export_power == 0.0

    # Battery checks
    assert inverter.battery.voltage == pytest.approx(380.0)
    assert inverter.battery.current == pytest.approx(12.0)
    assert inverter.battery.power == 4560
    assert inverter.battery.soc == 78
    assert inverter.battery.temperature == pytest.approx(25.0)
    assert inverter.battery.discharge_power == pytest.approx(4560.0)
    assert inverter.battery.charge_power == 0.0

    # Inverter checks
    assert inverter.inverter.inverter_temp == pytest.approx(41.0)
    assert inverter.inverter.ambient_temp == pytest.approx(22.0)
    assert inverter.inverter.state == InverterState.ON_GRID


@pytest.mark.asyncio
async def test_h1_controls(h1_unit):
    """Test control and setpoint commands on FoxESS H1."""
    inverter = FoxessH1Inverter(h1_unit)
    report = await inverter.async_update_settings()

    assert "control" in report.updated
    assert inverter.control.work_mode == WorkMode.SELF_USE
    assert inverter.control.min_soc == 10

    # Work mode change
    await inverter.async_set_work_mode(WorkMode.FEED_IN_FIRST)
    assert h1_unit.holding[41000] == 1

    # Force charge
    await inverter.async_set_force_charge(power_w=3000, max_soc=90, timeout_sec=1200)
    assert h1_unit.holding[44000] == 1
    assert h1_unit.holding[44001] == 1200
    assert h1_unit.holding[44002] & 0xFFFF == (-3000) & 0xFFFF

    # Clear override
    await inverter.async_clear_overrides()
    assert h1_unit.holding[44000] == 0


@pytest.mark.asyncio
async def test_h1_read_raw(h1_unit):
    """Test reading undecoded raw registers for diagnostics."""
    inverter = FoxessH1Inverter(h1_unit)
    raw = await inverter.async_read_raw()

    assert "holding" in raw
    assert 31000 in raw["holding"]  # PV1 voltage
    assert 31024 in raw["holding"]  # Battery SOC
