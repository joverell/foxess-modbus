"""Diagnostics support for FoxESS Modern."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import FoxessConfigEntry

try:
    from homeassistant.components.diagnostics import async_redact_data
except ImportError:
    def async_redact_data(data: Any, to_redact: set[str]) -> Any:
        return data

TO_REDACT = {"serial_number", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FoxessConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = entry.runtime_data
    unit = data.unit if data else None
    device = data.device if data else None

    transport_info: dict[str, Any] = {
        "is_leased": getattr(unit, "is_leased", False),
        "host": getattr(unit, "host", entry.data.get("host")),
        "port": getattr(unit, "port", entry.data.get("port")),
        "unit_id": getattr(unit, "unit_id", entry.data.get("unit_id")),
        "timeout": getattr(unit, "timeout", None),
        "message_spacing": getattr(getattr(unit, "unit", None), "message_spacing", 0.25),
    }

    readings_info: dict[str, Any] = {}
    if data and data.readings_coordinator:
        coord = data.readings_coordinator
        readings_info = {
            "name": coord.name,
            "interval_seconds": coord.update_interval.total_seconds() if coord.update_interval else None,
            "last_update_success": coord.last_update_success,
            "is_available": coord.is_available,
            "timeouts": coord._timeouts,
            "failed_subsystems": sorted(coord._failed_subsystems),
        }

    settings_info: dict[str, Any] = {}
    if data and data.settings_coordinator:
        coord = data.settings_coordinator
        settings_info = {
            "name": coord.name,
            "interval_seconds": coord.update_interval.total_seconds() if coord.update_interval else None,
            "last_update_success": coord.last_update_success,
            "is_available": coord.is_available,
            "timeouts": coord._timeouts,
            "failed_subsystems": sorted(coord._failed_subsystems),
        }

    device_info: dict[str, Any] = {}
    if device:
        device_info = {
            "model": getattr(device, "model", entry.data.get("model")),
            "serial_number": getattr(device, "serial_number", entry.unique_id),
            "capabilities": getattr(device, "capabilities", []),
            "has_bms": getattr(device, "has_bms", False),
            "has_meter": getattr(device, "has_meter", False),
        }

    raw_diagnostics = {
        "entry": {
            "entry_id": entry.entry_id,
            "domain": entry.domain,
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "transport": transport_info,
        "coordinators": {
            "readings": readings_info,
            "settings": settings_info,
        },
        "device": device_info,
    }

    return async_redact_data(raw_diagnostics, TO_REDACT)
