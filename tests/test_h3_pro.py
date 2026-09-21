"""Unit tests for FoxESS H3-Pro commercial three-phase inverter model (6 strings)."""

import pytest
from modbus_connection.mock import MockModbusConnection

from foxess_modbus import FoxessH3ProInverter, identify_model, create_inverter


@pytest.fixture
def h3_pro_unit():
    """Create a mock unit with representative FoxESS H3-Pro holding registers."""
    conn = MockModbusConnection()
    unit = conn.for_unit(247)

    unit.holding.update({
        # PV registers (6 strings / 3 MPPTs)
        # MPPT 1
        39070: 5500,  # PV1 Voltage: 550.0 V
        39071: 850,   # PV1 Current: 8.50 A
        39279: 0, 39280: 4675,  # PV1 Power: 4675 W
        39072: 5450,  # PV2 Voltage: 545.0 V
        39073: 840,   # PV2 Current: 8.40 A
        39281: 0, 39282: 4578,  # PV2 Power: 4578 W

        # MPPT 2
        39074: 5600,  # PV3 Voltage: 560.0 V
        39075: 860,   # PV3 Current: 8.60 A
        39283: 0, 39284: 4816,  # PV3 Power: 4816 W
        39076: 5550,  # PV4 Voltage: 555.0 V
        39077: 850,   # PV4 Current: 8.50 A
        39285: 0, 39286: 4717,  # PV4 Power: 4717 W

        # MPPT 3 (PV5 and PV6)
        39078: 5400,  # PV5 Voltage: 540.0 V
        39079: 830,   # PV5 Current: 8.30 A
        39287: 0, 39288: 4482,  # PV5 Power: 4482 W
        39080: 5380,  # PV6 Voltage: 538.0 V
        39081: 820,   # PV6 Current: 8.20 A
        39289: 0, 39290: 4411,  # PV6 Power: 4411 W

        # Three-Phase Grid
        31006: 2300, 31009: 200, 31012: 4600,  # Phase R
        31007: 2300, 31010: 200, 31013: 4600,  # Phase S
        31008: 2300, 31011: 200, 31014: 4600,  # Phase T
        31015: 5000,                           # 50 Hz

        # Battery
        31034: 5000, 31035: 200, 31036: 10000, 31037: 250, 31038: 90,

        # Inverter health
        31032: 450, 31033: 250, 31041: 2,

        # Control
        41000: 0, 41009: 10, 41010: 100, 44000: 0, 44001: 0, 44002: 0,
    })
    return unit


@pytest.mark.asyncio
async def test_h3_pro_six_pv_strings(h3_pro_unit):
    """Test reading all 6 PV strings on FoxESS H3-Pro."""
    inverter = FoxessH3ProInverter(h3_pro_unit, serial_number="60TB12345678")
    assert inverter.model == "H3-Pro"

    report = await inverter.async_update_readings()
    assert "pv" in report.updated

    # Verify PV1 - PV4
    assert inverter.pv.pv1_voltage == pytest.approx(550.0)
    assert inverter.pv.pv1_power == 4675
    assert inverter.pv.pv2_voltage == pytest.approx(545.0)
    assert inverter.pv.pv2_power == 4578
    assert inverter.pv.pv3_voltage == pytest.approx(560.0)
    assert inverter.pv.pv3_power == 4816
    assert inverter.pv.pv4_voltage == pytest.approx(555.0)
    assert inverter.pv.pv4_power == 4717

    # Verify PV5 and PV6
    assert inverter.pv.pv5_voltage == pytest.approx(540.0)
    assert inverter.pv.pv5_current == pytest.approx(8.30)
    assert inverter.pv.pv5_power == 4482

    assert inverter.pv.pv6_voltage == pytest.approx(538.0)
    assert inverter.pv.pv6_current == pytest.approx(8.20)
    assert inverter.pv.pv6_power == 4411

    # Total PV Power across all 6 strings
    expected_total = 4675 + 4578 + 4816 + 4717 + 4482 + 4411
    assert inverter.pv.pv_power_total == expected_total


def test_h3_pro_identification(h3_pro_unit):
    """Test model identification for H3-Pro serials and model names."""
    assert identify_model("60TB12345678") == "H3_PRO"
    assert identify_model("60TA98765432") == "H3_PRO"
    assert identify_model("H3-Pro-20.0") == "H3_PRO"
    assert identify_model("H3_PRO_15.0") == "H3_PRO"

    inv = create_inverter(h3_pro_unit, model="H3-Pro")
    assert isinstance(inv, FoxessH3ProInverter)
