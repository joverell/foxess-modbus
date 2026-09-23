"""Select platform for FoxESS Modern work mode configuration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FoxessConfigEntry
from .const import CONF_MAPPINGS
from .coordinator import FoxessDataUpdateCoordinator
from .device.const import WorkMode
from .migration import adopt_legacy_entity_id

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
    entity_reg = er.async_get(hass)
    target_id = adopt_legacy_entity_id(
        entity_reg,
        key="work_mode",
        domain="select",
        serial=serial,
        explicit_mapped_id=mappings.get("work_mode"),
    )

    async_add_entities([
        FoxessWorkModeSelect(coordinator, device, serial, target_entity_id=target_id)
    ])


class FoxessWorkModeSelect(CoordinatorEntity[FoxessDataUpdateCoordinator], SelectEntity):
    """Select entity for inverter work mode."""

    _attr_has_entity_name = False
    _attr_options = list(_WORK_MODE_OPTIONS.keys())

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.is_available

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        device: Any,
        serial: str,
        target_entity_id: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_work_mode"
        self._attr_name = "Work Mode"
        self._attr_device_info = coordinator.device_info
        raw_id = target_entity_id or suggested_object_id
        if raw_id:
            if not raw_id.startswith("select."):
                raw_id = f"select.{raw_id}"
            self.entity_id = raw_id
            self._attr_suggested_object_id = raw_id.split(".", 1)[-1]
        elif suggested_object_id:
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
