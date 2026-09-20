"""Unit tests for FoxESS H3 three-phase inverter model."""

import pytest
from modbus_connection.mock import MockModbusConnection

from foxess_modbus import FoxessH3Inverter, InverterState, WorkMode


@pytest.fixture
def h3_unit():
    """Create a mock unit with representative FoxESS H3 holding registers."""
    conn = MockModbusConnection()
    unit = conn.for_unit(247)

    unit.holding.update({
        # PV registers (2 MPPT trackers)
        31000: 5800,  # PV1 Voltage: 580.0 V
        31001: 90,    # PV1 Current: 9.0 A
        31002: 5220,  # PV1 Power: 5220 W
        31003: 5600,  # PV2 Voltage: 560.0 V
        31004: 85,    # PV2 Current: 8.5 A
        31005: 4760,  # PV2 Power: 4760 W

        # Grid registers (Three-Phase: R, S, T)
        31006: 2320,  # Voltage R: 232.0 V
        31009: 142,   # Current R: 14.2 A
        31012: 3300,  # Power R: 3300 W

        31007: 2315,  # Voltage S: 231.5 V
        31010: 141,   # Current S: 14.1 A
        31013: 3260,  # Power S: 3260 W

        31008: 2310,  # Voltage T: 231.0 V
        31011: 140,   # Current T: 14.0 A
        31014: 3230,  # Power T: 3230 W

        31015: 5002,  # Grid Frequency: 50.02 Hz

        # Inverter health
        31032: 440,   # Inverter Temp: 44.0 °C
        31033: 240,   # Ambient Temp: 24.0 °C
        31041: 2,     # State: On-grid

        # High-voltage Battery stack registers
        31034: 4600,  # Battery Voltage: 460.0 V
        31035: 150,   # Battery Current: 15.0 A (discharging)
        31036: 6900,  # Battery Power: 6900 W
        31037: 265,   # Battery Temp: 26.5 °C
        31038: 82,    # Battery SOC: 82%

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
async def test_h3_readings(h3_unit):
    """Test polling telemetry readings on FoxESS H3."""
    inverter = FoxessH3Inverter(h3_unit, serial_number="60PB10123456789")
    report = await inverter.async_update_readings()

    assert "pv" in report.updated
    assert "battery" in report.updated
    assert "grid" in report.updated
    assert "inverter" in report.updated
    assert not report.failed

    # PV checks
    assert inverter.pv.pv1_voltage == pytest.approx(580.0)
    assert inverter.pv.pv1_current == pytest.approx(9.0)
    assert inverter.pv.pv1_power == 5220
    assert inverter.pv.pv2_voltage == pytest.approx(560.0)
    assert inverter.pv.pv2_current == pytest.approx(8.5)
    assert inverter.pv.pv2_power == 4760
    assert inverter.pv.pv_power_total == pytest.approx(9980.0)

    # Three-Phase Grid checks
    assert inverter.grid.voltage_r == pytest.approx(232.0)
    assert inverter.grid.current_r == pytest.approx(14.2)
    assert inverter.grid.power_r == 3300

    assert inverter.grid.voltage_s == pytest.approx(231.5)
    assert inverter.grid.current_s == pytest.approx(14.1)
    assert inverter.grid.power_s == 3260

    assert inverter.grid.voltage_t == pytest.approx(231.0)
    assert inverter.grid.current_t == pytest.approx(14.0)
    assert inverter.grid.power_t == 3230

    assert inverter.grid.frequency == pytest.approx(50.02)
    assert inverter.grid.grid_power_total == pytest.approx(9790.0)

    # HV Battery checks
    assert inverter.battery.voltage == pytest.approx(460.0)
    assert inverter.battery.current == pytest.approx(15.0)
    assert inverter.battery.power == 6900
    assert inverter.battery.soc == 82
    assert inverter.battery.temperature == pytest.approx(26.5)
    assert inverter.battery.discharge_power == pytest.approx(6900.0)
    assert inverter.battery.charge_power == 0.0

    # Inverter checks
    assert inverter.inverter.inverter_temp == pytest.approx(44.0)
    assert inverter.inverter.ambient_temp == pytest.approx(24.0)
    assert inverter.inverter.state == InverterState.ON_GRID


@pytest.mark.asyncio
async def test_h3_controls(h3_unit):
    """Test control and setpoint commands on FoxESS H3."""
    inverter = FoxessH3Inverter(h3_unit)
    report = await inverter.async_update_settings()

    assert "control" in report.updated
    assert inverter.control.work_mode == WorkMode.SELF_USE
    assert inverter.control.min_soc == 10

    # Work mode change
    await inverter.async_set_work_mode(WorkMode.BACK_UP)
    assert h3_unit.holding[41000] == 2

    # Force discharge
    await inverter.async_set_force_discharge(power_w=6000, min_soc=15, timeout_sec=1800)
    assert h3_unit.holding[44000] == 1
    assert h3_unit.holding[44001] == 1800
    assert h3_unit.holding[44002] == 6000
    assert h3_unit.holding[41009] == 15

    # Clear override
    await inverter.async_clear_overrides()
    assert h3_unit.holding[44000] == 0


@pytest.mark.asyncio
async def test_h3_read_raw(h3_unit):
    """Test reading undecoded raw registers for diagnostics."""
    inverter = FoxessH3Inverter(h3_unit)
    raw = await inverter.async_read_raw()

    assert "holding" in raw
    assert 31006 in raw["holding"]  # Voltage R
    assert 31007 in raw["holding"]  # Voltage S
    assert 31008 in raw["holding"]  # Voltage T
    assert 31038 in raw["holding"]  # Battery SOC
