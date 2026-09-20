"""Diagnostics support for FoxESS Modern."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import FoxessConfigEntry

TO_REDACT = {"serial_number"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FoxessConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    device = entry.runtime_data.device
    raw = await device.async_read_raw()

    return async_redact_data(
        {
            "model": device.model,
            "serial_number": device.serial_number,
            "readings_components": list(device._readings),
            "settings_components": list(device._settings),
            "raw": raw,
        },
        TO_REDACT,
    )
