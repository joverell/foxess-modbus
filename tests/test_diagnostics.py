"""Tests for FoxESS Modern diagnostics platform."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from custom_components.foxess_modern.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.asyncio
async def test_diagnostics_output():
    """Verify diagnostic payload structure and redaction."""
    mock_hass = MagicMock()

    mock_unit = MagicMock()
    mock_unit.is_leased = True
    mock_unit.host = "192.168.86.162"
    mock_unit.port = 502
    mock_unit.unit_id = 247
    mock_unit.timeout = 5.0
    mock_unit.unit = MagicMock()
    mock_unit.unit.message_spacing = 0.25

    mock_coord_readings = MagicMock()
    mock_coord_readings.name = "foxess_modern_test_readings"
    mock_coord_readings.update_interval.total_seconds.return_value = 15.0
    mock_coord_readings.last_update_success = True
    mock_coord_readings.is_available = True
    mock_coord_readings._timeouts = 0
    mock_coord_readings._failed_subsystems = frozenset()

    mock_coord_settings = MagicMock()
    mock_coord_settings.name = "foxess_modern_test_settings"
    mock_coord_settings.update_interval.total_seconds.return_value = 60.0
    mock_coord_settings.last_update_success = True
    mock_coord_settings.is_available = True
    mock_coord_settings._timeouts = 0
    mock_coord_settings._failed_subsystems = frozenset(["bms"])

    mock_device = MagicMock()
    mock_device.model = "KH10"
    mock_device.serial_number = "60KB1030617A"
    mock_device.capabilities = ["pv", "battery", "grid"]
    mock_device.has_bms = True
    mock_device.has_meter = True

    mock_runtime_data = MagicMock()
    mock_runtime_data.unit = mock_unit
    mock_runtime_data.readings_coordinator = mock_coord_readings
    mock_runtime_data.settings_coordinator = mock_coord_settings
    mock_runtime_data.device = mock_device

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_diag_123"
    mock_entry.domain = "foxess_modern"
    mock_entry.title = "FoxESS KH10"
    mock_entry.data = {
        "host": "192.168.86.162",
        "port": 502,
        "unit_id": 247,
        "serial_number": "60KB1030617A",
    }
    mock_entry.options = {}
    mock_entry.unique_id = "192.168.86.162_502_247"
    mock_entry.runtime_data = mock_runtime_data

    result = await async_get_config_entry_diagnostics(mock_hass, mock_entry)

    assert result["entry"]["entry_id"] == "test_entry_diag_123"
    assert result["entry"]["domain"] == "foxess_modern"
    assert result["transport"]["is_leased"] is True
    assert result["transport"]["host"] == "192.168.86.162"
    assert result["transport"]["port"] == 502
    assert result["transport"]["unit_id"] == 247
    assert result["transport"]["message_spacing"] == 0.25
    assert result["coordinators"]["readings"]["is_available"] is True
    assert result["coordinators"]["settings"]["failed_subsystems"] == ["bms"]
    assert result["device"]["model"] == "KH10"
    assert result["device"]["has_bms"] is True
