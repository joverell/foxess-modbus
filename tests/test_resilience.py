"""Unit tests for resilience, exception handling, and entity availability continuity."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from modbus_connection.exceptions import ModbusConnectionError, ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection
from modbus_connection.model import UpdateReport

from foxess_modbus import FoxessKH10Inverter
from custom_components.foxess_modern.coordinator import FoxessDataUpdateCoordinator
from custom_components.foxess_modern.sensor import (
    BASE_SENSOR_DESCRIPTIONS,
    FoxessSensorEntity,
)


@pytest.mark.asyncio
async def test_device_async_poll_handles_modbus_timeout():
    """Verify that a single sub-system ModbusTimeoutError records in report.failed and does not abort remaining sub-systems."""
    conn = MockModbusConnection()
    unit = conn.for_unit(247)
    inv = FoxessKH10Inverter(unit)

    # Make pv sub-system fail with ModbusTimeoutError
    with patch.object(
        inv.pv, "async_update", side_effect=ModbusTimeoutError("PV frame dropped")
    ):
        report = await inv.async_update_readings()

    # pv is recorded in failed, but battery, grid, inverter updated successfully
    assert "pv" in report.failed
    assert "battery" in report.updated
    assert "grid" in report.updated
    assert "inverter" in report.updated


@pytest.mark.asyncio
async def test_coordinator_availability_continuity():
    """Verify coordinator tolerates transient communication hiccups without flipping to unavailable."""
    hass = MagicMock()
    entry = MagicMock()
    entry.unique_id = "test_entry"
    device = MagicMock()
    device.model = "KH10"

    fail_call = AsyncMock(side_effect=ModbusTimeoutError("Transient timeout"))
    coordinator = FoxessDataUpdateCoordinator(
        hass,
        entry,
        device,
        fail_call,
        timedelta(seconds=15),
    )

    assert coordinator.is_available is True

    # 1st transient failure -> remains available
    await coordinator._async_update_data()
    assert coordinator.is_available is True

    # 2nd transient failure -> remains available
    await coordinator._async_update_data()
    assert coordinator.is_available is True

    # 3rd transient failure -> remains available
    await coordinator._async_update_data()
    assert coordinator.is_available is True

    # 4th transient failure -> remains available
    await coordinator._async_update_data()
    assert coordinator.is_available is True


@pytest.mark.asyncio
async def test_sensor_entity_available_continuity():
    """Verify sensor entity stays available during transient coordinator hiccups."""
    coordinator = MagicMock()
    coordinator.is_available = True
    coordinator.device_info = MagicMock()

    desc = BASE_SENSOR_DESCRIPTIONS[0]
    dev = MagicMock()
    entity = FoxessSensorEntity(coordinator, desc, dev, "serial_123")

    assert entity.available is True

    # When coordinator is available, entity is available
    coordinator.is_available = True
    assert entity.available is True

    # When sustained outage marks coordinator unavailable, entity reflects it
    coordinator.is_available = False
    assert entity.available is False
