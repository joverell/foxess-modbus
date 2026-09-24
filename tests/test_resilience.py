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


@pytest.mark.asyncio
async def test_connection_pacing_and_bus_lock():
    """Verify DEFAULT_MESSAGE_SPACING is 250ms and ResilientModbusUnit provides a bus_lock."""
    from custom_components.foxess_modern.connection import (
        DEFAULT_MESSAGE_SPACING,
        ResilientModbusUnit,
    )
    assert DEFAULT_MESSAGE_SPACING == 0.25

    with patch("custom_components.foxess_modern.connection.ModbusConnection"):
        unit = ResilientModbusUnit("127.0.0.1", 502, 247)
        assert hasattr(unit, "bus_lock")
        assert isinstance(unit.bus_lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_connection_status_sensor_debouncing():
    """Verify connection_status entity relies on coordinator.is_available (debounced)."""
    coordinator = MagicMock()
    coordinator.last_update_success = False  # transient single poll failure
    coordinator.is_available = True         # debounced within tolerance
    coordinator.device_info = MagicMock()

    conn_desc = next(d for d in BASE_SENSOR_DESCRIPTIONS if d.key == "connection_status")
    dev = MagicMock()
    dev.modbus_unit.connected = True

    entity = FoxessSensorEntity(coordinator, conn_desc, dev, "serial_123")
    # Should report Connected while within debounce window even if last_update_success is False
    assert entity.native_value == "Connected"

    # Sustained outage marks coordinator unavailable
    coordinator.is_available = False
    assert entity.native_value == "Disconnected"


@pytest.mark.asyncio
async def test_core_modbus_unit_leasing():
    """Verify async_get_modbus_unit leases a shared unit when Core Modbus is available."""
    from custom_components.foxess_modern.connection import async_get_modbus_unit

    mock_core_unit = MagicMock()
    mock_core_unit.set_message_spacing = MagicMock()
    mock_core_unit.require_connect_delay = MagicMock()
    mock_core_unit.require_timeout = MagicMock()

    mock_modbus_module = MagicMock()
    mock_modbus_module.async_get_unit = MagicMock(return_value=mock_core_unit)

    with patch.dict("sys.modules", {"homeassistant.components.modbus": mock_modbus_module}):
        unit = async_get_modbus_unit(MagicMock(), MagicMock(), "192.168.1.100", 502, 247)
        assert unit.is_leased is True
        mock_core_unit.set_message_spacing.assert_called_once_with(0.25)
        mock_core_unit.require_connect_delay.assert_called_once_with(0.05)
        mock_core_unit.require_timeout.assert_called_once_with(5.0)

        # Closing a leased unit must not error or close a shared connection
        await unit.close()


@pytest.mark.asyncio
async def test_core_modbus_temporary_probe_unit():
    """Verify async_get_probe_unit leases an ephemeral unit during config flow probe."""
    from custom_components.foxess_modern.connection import async_get_probe_unit

    mock_core_unit = MagicMock()
    mock_core_unit.set_message_spacing = MagicMock()
    mock_core_unit.require_connect_delay = MagicMock()
    mock_core_unit.require_timeout = MagicMock()

    class MockAsyncContextManager:
        async def __aenter__(self):
            return mock_core_unit

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_modbus_module = MagicMock()
    mock_modbus_module.async_get_temporary_unit = MagicMock(return_value=MockAsyncContextManager())

    with patch.dict("sys.modules", {"homeassistant.components.modbus": mock_modbus_module}):
        async with async_get_probe_unit(MagicMock(), "192.168.1.100", 502, 247) as probe_unit:
            assert probe_unit.is_leased is True
            assert probe_unit.unit is mock_core_unit


@pytest.mark.asyncio
async def test_standalone_fallback_connection():
    """Verify fallback creates a standalone connection when Core Modbus is not present."""
    from custom_components.foxess_modern.connection import async_get_modbus_unit

    with patch.dict("sys.modules", {"homeassistant.components.modbus": None}):
        with patch("custom_components.foxess_modern.connection.ModbusConnection") as mock_conn_cls:
            mock_conn = MagicMock()
            mock_conn.for_unit = MagicMock()
            mock_conn_cls.return_value = mock_conn

            unit = async_get_modbus_unit(MagicMock(), MagicMock(), "127.0.0.1", 502, 247)
            assert unit.is_leased is False
            assert unit.connection is mock_conn


