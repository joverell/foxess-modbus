"""Unit tests for resilience, exception handling, and entity availability continuity."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from modbus_connection.exceptions import ModbusConnectionError, ModbusError, ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection
from modbus_connection.model import UpdateReport

from foxess_modbus import FoxessKH10Inverter
from custom_components.foxess_modern.coordinator import FoxessDataUpdateCoordinator
from custom_components.foxess_modern.sensor import (
    BASE_SENSOR_DESCRIPTIONS,
    FoxessEnergySensor,
    FoxessSensorEntity,
)


@pytest.mark.asyncio
async def test_device_async_poll_handles_subsystem_timeout():
    """Verify that a sub-system ModbusTimeoutError after an earlier read records in report.failed and does not abort remaining sub-systems."""
    conn = MockModbusConnection()
    unit = conn.for_unit(247)
    inv = FoxessKH10Inverter(unit)

    # Make battery sub-system fail with ModbusTimeoutError (pv is polled first and succeeds)
    with patch.object(
        inv.battery, "async_update", side_effect=ModbusTimeoutError("Battery frame dropped")
    ):
        report = await inv.async_update_readings()

    # pv succeeded, battery recorded in failed, grid and inverter succeeded
    assert "pv" in report.updated
    assert "battery" in report.failed
    assert "grid" in report.updated
    assert "inverter" in report.updated


@pytest.mark.asyncio
async def test_coordinator_timeout_and_recycling():
    """Verify coordinator tracks consecutive timeouts and recycles link via disconnect() after 3 failures."""
    hass = MagicMock()
    entry = MagicMock()
    entry.unique_id = "test_entry"
    device = MagicMock()
    device.model = "KH10"
    device.modbus_unit = MagicMock()
    device.modbus_unit.disconnect = AsyncMock()

    fail_call = AsyncMock(side_effect=ModbusTimeoutError("Transient timeout"))
    coordinator = FoxessDataUpdateCoordinator(
        hass,
        entry,
        device,
        fail_call,
        timedelta(seconds=15),
        is_fast_poll=True,
    )

    assert coordinator._timeouts == 0

    # 1st timeout
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._timeouts == 1
    device.modbus_unit.disconnect.assert_not_called()

    # 2nd timeout
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._timeouts == 2
    device.modbus_unit.disconnect.assert_not_called()

    # 3rd timeout -> triggers disconnect()
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._timeouts == 3
    device.modbus_unit.disconnect.assert_called_once()

    # Subsequent recovery resets timeouts counter
    success_report = UpdateReport(updated={"pv", "battery"})
    coordinator._update_method = AsyncMock(return_value=success_report)
    report = await coordinator._async_update_data()
    assert coordinator._timeouts == 0
    assert "pv" in report.updated


@pytest.mark.asyncio
async def test_sensor_entity_available_continuity():
    """Verify sensor entity reflects coordinator success and energy sensors remain permanently available."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.is_available = True
    coordinator.device_info = MagicMock()

    desc = BASE_SENSOR_DESCRIPTIONS[0]
    dev = MagicMock()
    entity = FoxessSensorEntity(coordinator, desc, dev, "serial_123")

    assert entity.available is True

    # When sustained outage marks coordinator unavailable, standard entity reflects it
    coordinator.last_update_success = False
    coordinator.is_available = False
    assert entity.available is False

    # Cumulative energy sensor stays available even when coordinator is unavailable (night sleep)
    energy_sensor = FoxessEnergySensor(
        coordinator=coordinator,
        key="test_energy",
        name="Test Energy",
        power_fn=lambda d: 100.0,
        device=dev,
        serial="serial_123",
    )
    assert energy_sensor.available is True
