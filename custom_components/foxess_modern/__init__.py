"""The FoxESS Modern Modbus integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from typing import Any
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .connection import ResilientModbusUnit, async_get_modbus_unit
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DOMAIN,
    SCAN_INTERVAL,
    SETTINGS_SCAN_INTERVAL,
)
from .coordinator import FoxessDataUpdateCoordinator
from .device import create_inverter
from .device.const import WorkMode

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
]

SERVICE_SET_FORCE_CHARGE = "set_force_charge"
SERVICE_SET_FORCE_DISCHARGE = "set_force_discharge"
SERVICE_CLEAR_OVERRIDES = "clear_overrides"
SERVICE_SET_WORK_MODE = "set_work_mode"


from modbus_connection import ModbusConnection


@dataclass
class FoxessRuntimeData:
    """Runtime data held by the FoxESS Modern config entry."""

    readings_coordinator: FoxessDataUpdateCoordinator
    settings_coordinator: FoxessDataUpdateCoordinator
    device: Any
    unit: ResilientModbusUnit
    connection: ModbusConnection | None
    bus_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


type FoxessConfigEntry = ConfigEntry[FoxessRuntimeData]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the FoxESS Modern component and register services."""

    async def async_handle_set_force_charge(call: ServiceCall) -> None:
        """Handle force charge service call."""
        power = int(call.data.get("power", 5000))
        max_soc = int(call.data.get("max_soc", 100))
        duration = int(call.data.get("duration", 3600))
        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                bus_lock = getattr(
                    entry.runtime_data,
                    "bus_lock",
                    getattr(entry.runtime_data.unit, "bus_lock", None),
                )
                if bus_lock is not None:
                    async with bus_lock:
                        await entry.runtime_data.device.async_set_force_charge(
                            power_w=power, max_soc=max_soc, timeout_sec=duration
                        )
                        await entry.runtime_data.settings_coordinator.async_request_refresh()
                else:
                    await entry.runtime_data.device.async_set_force_charge(
                        power_w=power, max_soc=max_soc, timeout_sec=duration
                    )
                    await entry.runtime_data.settings_coordinator.async_request_refresh()

    async def async_handle_set_force_discharge(call: ServiceCall) -> None:
        """Handle force discharge service call."""
        power = int(call.data.get("power", 5000))
        min_soc = int(call.data.get("min_soc", 10))
        duration = int(call.data.get("duration", 3600))
        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                bus_lock = getattr(
                    entry.runtime_data,
                    "bus_lock",
                    getattr(entry.runtime_data.unit, "bus_lock", None),
                )
                if bus_lock is not None:
                    async with bus_lock:
                        await entry.runtime_data.device.async_set_force_discharge(
                            power_w=power, min_soc=min_soc, timeout_sec=duration
                        )
                        await entry.runtime_data.settings_coordinator.async_request_refresh()
                else:
                    await entry.runtime_data.device.async_set_force_discharge(
                        power_w=power, min_soc=min_soc, timeout_sec=duration
                    )
                    await entry.runtime_data.settings_coordinator.async_request_refresh()

    async def async_handle_clear_overrides(call: ServiceCall) -> None:
        """Handle clear overrides service call."""
        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                bus_lock = getattr(
                    entry.runtime_data,
                    "bus_lock",
                    getattr(entry.runtime_data.unit, "bus_lock", None),
                )
                if bus_lock is not None:
                    async with bus_lock:
                        await entry.runtime_data.device.async_clear_overrides()
                        await entry.runtime_data.settings_coordinator.async_request_refresh()
                else:
                    await entry.runtime_data.device.async_clear_overrides()
                    await entry.runtime_data.settings_coordinator.async_request_refresh()

    async def async_handle_set_work_mode(call: ServiceCall) -> None:
        """Handle set work mode service call."""
        mode_str = call.data.get("work_mode", "Self Use")
        mode_map = {
            "Self Use": WorkMode.SELF_USE,
            "Feed-in First": WorkMode.FEED_IN_FIRST,
            "Back-up": WorkMode.BACK_UP,
        }
        mode = mode_map.get(mode_str, WorkMode.SELF_USE)
        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                bus_lock = getattr(
                    entry.runtime_data,
                    "bus_lock",
                    getattr(entry.runtime_data.unit, "bus_lock", None),
                )
                if bus_lock is not None:
                    async with bus_lock:
                        await entry.runtime_data.device.async_set_work_mode(mode)
                        await entry.runtime_data.settings_coordinator.async_request_refresh()
                else:
                    await entry.runtime_data.device.async_set_work_mode(mode)
                    await entry.runtime_data.settings_coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_SET_FORCE_CHARGE, async_handle_set_force_charge
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_FORCE_DISCHARGE, async_handle_set_force_discharge
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_OVERRIDES, async_handle_clear_overrides
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_WORK_MODE, async_handle_set_work_mode
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: FoxessConfigEntry) -> bool:
    """Set up FoxESS Modern from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    unit_id = entry.data[CONF_UNIT_ID]
    serial = entry.unique_id or f"{host}_{port}_{unit_id}"

    unit = async_get_modbus_unit(hass, entry, host=host, port=port, unit_id=unit_id)
    device = create_inverter(unit, serial_number=serial, model=entry.data.get("model"))

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL)
    )

    bus_lock = asyncio.Lock()

    readings_coordinator = FoxessDataUpdateCoordinator(
        hass,
        entry,
        device,
        device.async_update_readings,
        timedelta(seconds=scan_interval),
        is_fast_poll=True,
        bus_lock=bus_lock,
    )
    settings_coordinator = FoxessDataUpdateCoordinator(
        hass,
        entry,
        device,
        device.async_update_settings,
        timedelta(seconds=SETTINGS_SCAN_INTERVAL),
        is_fast_poll=False,
        bus_lock=bus_lock,
    )

    # Initial data refresh
    try:
        await readings_coordinator.async_config_entry_first_refresh()
        await settings_coordinator.async_refresh()
    except Exception as err:
        await unit.close()
        raise ConfigEntryNotReady(f"Could not connect to FoxESS inverter: {err}") from err

    entry.runtime_data = FoxessRuntimeData(
        readings_coordinator=readings_coordinator,
        settings_coordinator=settings_coordinator,
        device=device,
        unit=unit,
        connection=unit.connection,
        bus_lock=bus_lock,
    )

    entry.async_on_unload(entry.add_update_listener(update_listener))

    from .migration import async_migrate_entity_registry

    await async_migrate_entity_registry(hass, entry)

    # Clean up any legacy Repairs advisory issues
    try:
        from homeassistant.helpers import issue_registry as ir

        ir.async_delete_issue(
            hass,
            DOMAIN,
            f"modbus_standalone_advisory_{entry.entry_id}",
        )
    except Exception as issue_err:
        _LOGGER.debug("Could not clean up issue registry: %s", issue_err)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def update_listener(hass: HomeAssistant, entry: FoxessConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: FoxessConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        from homeassistant.helpers import issue_registry as ir

        ir.async_delete_issue(hass, DOMAIN, f"modbus_standalone_advisory_{entry.entry_id}")
    except Exception:
        pass

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and hasattr(entry, "runtime_data") and entry.runtime_data:
        await entry.runtime_data.unit.close()
    return unload_ok

