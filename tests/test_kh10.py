"""Unit tests for FoxESS KH10 inverter model."""

import pytest
from modbus_connection.mock import MockModbusConnection

from foxess_modbus import FoxessKH10Inverter, WorkMode
from foxess_modbus.const import InverterState


@pytest.fixture
def kh10_unit():
    """Create a mock unit with representative FoxESS KH10 holding registers."""
    conn = MockModbusConnection()
    unit = conn.for_unit(247)

    # Populate realistic holding registers for KH10
    unit.holding.update({
        # PV registers
        39070: 3805,  # PV1 Voltage: 380.5 V
        39071: 812,   # PV1 Current: 8.12 A
        39279: 0,     # PV1 Power high word
        39280: 3089,  # PV1 Power low word -> 3089 W
        39072: 3752,  # PV2 Voltage: 375.2 V
        39073: 750,   # PV2 Current: 7.50 A
        39281: 0,     # PV2 Power high word
        39282: 2814,  # PV2 Power low word -> 2814 W

        # Grid registers
        31006: 2425,  # Grid Voltage: 242.5 V
        31007: 245,   # Inverter Current: 24.5 A
        31008: 5900,  # Inverter Power: 5900 W
        31009: 5002,  # Grid Frequency: 50.02 Hz
        31016: 1250,  # House Load: 1250 W
        # Grid CT active power: 32-bit signed -> -500 W (importing)
        39168: 0xFFFF,
        39169: 0xFE0C,

        # Battery registers
        31020: 3450,  # Battery Voltage: 345.0 V
        31021: 150,   # Battery Current: 15.0 A (discharging)
        31022: 5175,  # Battery Power: 5175 W
        31024: 85,    # Battery SOC: 85%
        31023: 245,   # Battery Temp: 24.5 °C
        31025: 500,   # BMS max charge: 50.0 A
        31026: 500,   # BMS max discharge: 50.0 A
        37002: 1,     # BMS connected

        # Inverter health
        31018: 425,   # Inverter Temp: 42.5 °C
        31019: 230,   # Ambient Temp: 23.0 °C
        31027: 2,     # State: On-grid (2)
        36001: 133,   # Master version: 1.33
        36002: 100,   # Slave version: 1.00
        36003: 115,   # Manager version: 1.15

        # Control registers
        41000: 0,     # Work mode: Self Use (0)
        41009: 10,    # Min SOC: 10%
        41010: 100,   # Max SOC: 100%
        41011: 15,    # Min SOC on grid: 15%
        44000: 0,     # Remote enable: Off
        44001: 0,     # Remote timeout
        44002: 0,     # Remote power
    })
    return unit


@pytest.mark.asyncio
async def test_kh10_readings(kh10_unit):
    """Test polling telemetry readings."""
    inverter = FoxessKH10Inverter(kh10_unit, serial_number="60KB1030617A039")
    report = await inverter.async_update_readings()

    assert "pv" in report.updated
    assert "battery" in report.updated
    assert "grid" in report.updated
    assert "inverter" in report.updated
    assert not report.failed

    # PV checks
    assert inverter.pv.pv1_voltage == pytest.approx(380.5)
    assert inverter.pv.pv1_current == pytest.approx(8.12)
    assert inverter.pv.pv1_power == 3089
    assert inverter.pv.pv2_voltage == pytest.approx(375.2)
    assert inverter.pv.pv2_current == pytest.approx(7.50)
    assert inverter.pv.pv2_power == 2814
    assert inverter.pv.pv_power_total == pytest.approx(5903.0)

    # Battery checks
    assert inverter.battery.voltage == pytest.approx(345.0)
    assert inverter.battery.current == pytest.approx(15.0)
    assert inverter.battery.power == pytest.approx(5175.0)
    assert inverter.battery.soc == 85
    assert inverter.battery.temperature == pytest.approx(24.5)
    assert inverter.battery.discharge_power == pytest.approx(5175.0)
    assert inverter.battery.charge_power == 0.0

    # Grid checks
    assert inverter.grid.voltage == pytest.approx(242.5)
    assert inverter.grid.frequency == pytest.approx(50.02)
    assert inverter.grid.load_power == pytest.approx(1250.0)
    assert inverter.grid.ct_meter_power == -500
    assert inverter.grid.grid_import_power == pytest.approx(500.0)
    assert inverter.grid.grid_export_power == 0.0

    # Inverter checks
    assert inverter.inverter.inverter_temp == pytest.approx(42.5)
    assert inverter.inverter.ambient_temp == pytest.approx(23.0)
    assert inverter.inverter.state == InverterState.ON_GRID


@pytest.mark.asyncio
async def test_kh10_settings(kh10_unit):
    """Test polling configuration and settings."""
    inverter = FoxessKH10Inverter(kh10_unit)
    report = await inverter.async_update_settings()

    assert "control" in report.updated
    assert inverter.control.work_mode == WorkMode.SELF_USE
    assert inverter.control.min_soc == 10
    assert inverter.control.max_soc == 100


@pytest.mark.asyncio
async def test_kh10_control_commands(kh10_unit):
    """Test writing control commands and setpoints."""
    inverter = FoxessKH10Inverter(kh10_unit)

    # Test work mode switch
    await inverter.async_set_work_mode(WorkMode.FEED_IN_FIRST)
    assert kh10_unit.holding[41000] == 1

    # Test min SOC adjustment
    await inverter.async_set_min_soc(20)
    assert kh10_unit.holding[41009] == 20

    # Test force charge (commands negative power in Watts)
    await inverter.async_set_force_charge(power_w=5000, max_soc=95, timeout_sec=1800)
    assert kh10_unit.holding[44000] == 1
    assert kh10_unit.holding[44001] == 1800
    # Register 44002 is signed 16-bit negative (-5000)
    assert kh10_unit.holding[44002] & 0xFFFF == (-5000) & 0xFFFF
    assert kh10_unit.holding[41010] == 95

    # Test clear overrides
    await inverter.async_clear_overrides()
    assert kh10_unit.holding[44000] == 0
    assert kh10_unit.holding[41000] == 0  # Reverted to Self Use
