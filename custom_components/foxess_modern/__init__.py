"""The FoxESS Modern Modbus integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from modbus_connection import ModbusTcpParams

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_UNIT_ID,
    DOMAIN,
    SCAN_INTERVAL,
    SETTINGS_SCAN_INTERVAL,
)
from .coordinator import FoxessDataUpdateCoordinator
from .device import create_inverter

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
]


@dataclass
class FoxessRuntimeData:
    """Runtime data held by the FoxESS Modern config entry."""

    readings_coordinator: FoxessDataUpdateCoordinator
    settings_coordinator: FoxessDataUpdateCoordinator
    device: FoxessKH10Inverter


type FoxessConfigEntry = ConfigEntry[FoxessRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: FoxessConfigEntry) -> bool:
    """Set up FoxESS Modern from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    unit_id = entry.data[CONF_UNIT_ID]
    serial = entry.unique_id or f"{host}_{port}_{unit_id}"

    # Request a shared unit from Home Assistant's central Modbus broker
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=host, port=port),
        unit_id,
    )

    device = create_inverter(unit, serial_number=serial, model=entry.data.get("model"))

    readings_coordinator = FoxessDataUpdateCoordinator(
        hass,
        entry,
        device,
        device.async_update_readings,
        timedelta(seconds=SCAN_INTERVAL),
    )
    settings_coordinator = FoxessDataUpdateCoordinator(
        hass,
        entry,
        device,
        device.async_update_settings,
        timedelta(seconds=SETTINGS_SCAN_INTERVAL),
    )

    # Initial data refresh
    try:
        await readings_coordinator.async_config_entry_first_refresh()
        await settings_coordinator.async_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Could not connect to FoxESS inverter: {err}") from err

    entry.runtime_data = FoxessRuntimeData(
        readings_coordinator=readings_coordinator,
        settings_coordinator=settings_coordinator,
        device=device,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FoxessConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
