"""Select platform for FoxESS Modern work mode configuration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FoxessConfigEntry
from .const import CONF_MAPPINGS
from .coordinator import FoxessDataUpdateCoordinator
from .device.const import WorkMode

_WORK_MODE_OPTIONS: dict[str, WorkMode] = {
    "Self Use": WorkMode.SELF_USE,
    "Feed-in First": WorkMode.FEED_IN_FIRST,
    "Back-up": WorkMode.BACK_UP,
}
_REVERSE_WORK_MODE_MAP: dict[WorkMode, str] = {v: k for k, v in _WORK_MODE_OPTIONS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FoxessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FoxESS Modern select entities from a config entry."""
    coordinator = entry.runtime_data.settings_coordinator
    device = entry.runtime_data.device
    serial = str(entry.unique_id)
    mappings: dict[str, str] = entry.options.get(
        CONF_MAPPINGS, entry.data.get(CONF_MAPPINGS, {})
    )
    mapped_id = mappings.get("work_mode")
    suggested_id = mapped_id.split(".", 1)[-1] if mapped_id else None

    async_add_entities([
        FoxessWorkModeSelect(coordinator, device, serial, suggested_object_id=suggested_id)
    ])


class FoxessWorkModeSelect(CoordinatorEntity[FoxessDataUpdateCoordinator], SelectEntity):
    """Select entity for inverter work mode."""

    _attr_options = list(_WORK_MODE_OPTIONS.keys())

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        device: Any,
        serial: str,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_work_mode"
        self._attr_name = "Work Mode"
        self._attr_device_info = coordinator.device_info
        if suggested_object_id:
            self._attr_suggested_object_id = suggested_object_id

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        mode = self._device.control.work_mode
        if isinstance(mode, WorkMode):
            return _REVERSE_WORK_MODE_MAP.get(mode)
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        mode = _WORK_MODE_OPTIONS[option]
        await self._device.async_set_work_mode(mode)
        await self.coordinator.async_request_refresh()
