"""Unit tests for model identification and factory creation."""

from modbus_connection.mock import MockModbusConnection

from foxess_modbus import (
    FoxessH1Inverter,
    FoxessH3Inverter,
    FoxessKH10Inverter,
    create_inverter,
    identify_model,
)


def test_identify_model_from_serial():
    """Verify model detection from serial numbers."""
    # KH models
    assert identify_model("60KB1030617A039") == "KH"
    assert identify_model("60KA7012345B001") == "KH"

    # H1 / AC1 models
    assert identify_model("60HB50123456789") == "H1"
    assert identify_model("60HA60123456789") == "H1"
    assert identify_model("60AB36123456789") == "H1"

    # H3 / AC3 models
    assert identify_model("60PB10123456789") == "H3"
    assert identify_model("60PA80123456789") == "H3"
    assert identify_model("60TB15123456789") == "H3"


def test_identify_model_from_name():
    """Verify model detection from explicit model names."""
    assert identify_model("KH10") == "KH"
    assert identify_model("KH7") == "KH"
    assert identify_model("H1-5.0-E") == "H1"
    assert identify_model("AC1-6.0") == "H1"
    assert identify_model("AIO-H1-3.7") == "H1"
    assert identify_model("H3-10.0") == "H3"
    assert identify_model("AC3-8.0") == "H3"
    assert identify_model("H3-Pro-20.0") == "H3"


def test_create_inverter_factory():
    """Verify create_inverter instantiates the expected device class."""
    conn = MockModbusConnection()
    unit = conn.for_unit(247)

    # KH inverter
    dev_kh = create_inverter(unit, serial_number="60KB1030617A039")
    assert isinstance(dev_kh, FoxessKH10Inverter)

    # H1 inverter
    dev_h1 = create_inverter(unit, serial_number="60HB50123456789")
    assert isinstance(dev_h1, FoxessH1Inverter)

    # H3 inverter
    dev_h3 = create_inverter(unit, serial_number="60PB10123456789")
    assert isinstance(dev_h3, FoxessH3Inverter)

    # Explicit model override
    dev_h3_override = create_inverter(unit, model="H3-12.0")
    assert isinstance(dev_h3_override, FoxessH3Inverter)
