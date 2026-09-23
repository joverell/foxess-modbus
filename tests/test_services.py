"""Unit tests for FoxESS Modern custom services and power scaling."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.foxess_modern import (
    async_setup,
    SERVICE_SET_FORCE_CHARGE,
    SERVICE_SET_FORCE_DISCHARGE,
    SERVICE_CLEAR_OVERRIDES,
    SERVICE_SET_WORK_MODE,
)
from custom_components.foxess_modern.const import DOMAIN
from custom_components.foxess_modern.number import get_max_inverter_power
from foxess_modbus import FoxessKH10Inverter, FoxessH1Inverter, FoxessH3Inverter, WorkMode
from modbus_connection.mock import MockModbusConnection


@pytest.fixture
def mock_unit():
    """Mock ModbusUnit with control registers."""
    conn = MockModbusConnection()
    unit = conn.for_unit(247)
    unit.holding.update({
        41000: 0,
        44000: 0,
        44001: 0,
        44002: 0,
    })
    return unit


@pytest.fixture
def mock_kh10(mock_unit):
    """Mock KH10 device with control registers."""
    return FoxessKH10Inverter(mock_unit, serial_number="KH10ABC1234567")


@pytest.fixture
def mock_hass(mock_kh10):
    """Mock HomeAssistant instance with registered entries."""
    hass = MagicMock()
    entry = MagicMock(
        runtime_data=MagicMock(
            device=mock_kh10,
            settings_coordinator=MagicMock(async_request_refresh=AsyncMock()),
        )
    )
    hass.config_entries.async_entries.return_value = [entry]
    return hass


@pytest.mark.asyncio
async def test_service_set_force_charge(mock_hass, mock_kh10, mock_unit):
    """Test set_force_charge sets remote registers to charge the battery."""
    handlers = {}

    def register_service(domain, service, handler, schema=None):
        handlers[service] = handler

    mock_hass.services.async_register = register_service

    await async_setup(mock_hass, {})
    assert SERVICE_SET_FORCE_CHARGE in handlers

    call = MagicMock(data={"device_id": "KH10ABC1234567", "power": 3500, "duration": 1800})
    await handlers[SERVICE_SET_FORCE_CHARGE](call)

    # Forcing charge writes remote_enable=1, remote_timeout=1800, remote_power=-3500
    assert mock_unit.holding[44000] == 1
    assert mock_unit.holding[44001] == 1800
    assert mock_unit.holding[44002] == 65536 - 3500  # signed -3500 in 16-bit register


@pytest.mark.asyncio
async def test_service_set_force_discharge(mock_hass, mock_kh10, mock_unit):
    """Test set_force_discharge sets remote registers to discharge the battery."""
    handlers = {}

    def register_service(domain, service, handler, schema=None):
        handlers[service] = handler

    mock_hass.services.async_register = register_service

    await async_setup(mock_hass, {})
    call = MagicMock(data={"device_id": "KH10ABC1234567", "power": 4000, "duration": 3600})
    await handlers[SERVICE_SET_FORCE_DISCHARGE](call)

    # Forcing discharge writes remote_enable=1, remote_timeout=3600, remote_power=4000
    assert mock_unit.holding[44000] == 1
    assert mock_unit.holding[44001] == 3600
    assert mock_unit.holding[44002] == 4000


@pytest.mark.asyncio
async def test_service_clear_overrides(mock_hass, mock_kh10, mock_unit):
    """Test clear_overrides disables remote control."""
    handlers = {}

    def register_service(domain, service, handler, schema=None):
        handlers[service] = handler

    mock_hass.services.async_register = register_service

    await async_setup(mock_hass, {})
    # Set registers to non-zero first
    mock_unit.holding[44000] = 1
    mock_unit.holding[44001] = 600
    mock_unit.holding[44002] = 2000

    call = MagicMock(data={"device_id": "KH10ABC1234567"})
    await handlers[SERVICE_CLEAR_OVERRIDES](call)

    assert mock_unit.holding[44000] == 0


@pytest.mark.asyncio
async def test_service_set_work_mode(mock_hass, mock_kh10, mock_unit):
    """Test set_work_mode sets the inverter work mode."""
    handlers = {}

    def register_service(domain, service, handler, schema=None):
        handlers[service] = handler

    mock_hass.services.async_register = register_service

    await async_setup(mock_hass, {})
    call = MagicMock(data={"device_id": "KH10ABC1234567", "work_mode": "Back-up"})
    await handlers[SERVICE_SET_WORK_MODE](call)

    assert mock_unit.holding[41000] == 2


def test_dynamic_power_scaling():
    """Verify max power scaling dynamically according to device series."""
    # H3-Pro
    dev_pro = MagicMock(spec=["series"])
    dev_pro.series = "H3-Pro"
    assert get_max_inverter_power(dev_pro) == 30000.0

    # H3
    dev_h3 = MagicMock(spec=["series"])
    dev_h3.series = "H3"
    assert get_max_inverter_power(dev_h3) == 12000.0

    # KH
    dev_kh = MagicMock(spec=["series"])
    dev_kh.series = "KH"
    assert get_max_inverter_power(dev_kh) == 10500.0

    # H1
    dev_h1 = MagicMock(spec=["series"])
    dev_h1.series = "H1"
    assert get_max_inverter_power(dev_h1) == 6000.0
