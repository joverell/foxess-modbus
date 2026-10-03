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

WORK_MODE_SELF_USE = "Self Use"
WORK_MODE_FEED_IN_FIRST = "Feed-in First"
WORK_MODE_BACK_UP = "Back-up"
WORK_MODE_FORCE_CHARGE = "Force Charge"
WORK_MODE_FORCE_DISCHARGE = "Force Discharge"

_HARDWARE_WORK_MODES: dict[str, WorkMode] = {
    WORK_MODE_SELF_USE: WorkMode.SELF_USE,
    WORK_MODE_FEED_IN_FIRST: WorkMode.FEED_IN_FIRST,
    WORK_MODE_BACK_UP: WorkMode.BACK_UP,
}
_REVERSE_WORK_MODE_MAP: dict[WorkMode, str] = {v: k for k, v in _HARDWARE_WORK_MODES.items()}

_ALL_WORK_MODES: list[str] = [
    WORK_MODE_SELF_USE,
    WORK_MODE_FEED_IN_FIRST,
    WORK_MODE_BACK_UP,
    WORK_MODE_FORCE_CHARGE,
    WORK_MODE_FORCE_DISCHARGE,
]


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

    bus_lock = getattr(entry.runtime_data, "bus_lock", None)
    async_add_entities([
        FoxessWorkModeSelect(
            coordinator,
            device,
            serial,
            target_entity_id=target_id,
            bus_lock=bus_lock,
        )
    ])


class FoxessWorkModeSelect(CoordinatorEntity[FoxessDataUpdateCoordinator], SelectEntity):
    """Select entity for inverter work mode."""

    _attr_has_entity_name = False
    _attr_options = _ALL_WORK_MODES

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
        bus_lock: asyncio.Lock | None = None,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._device = device
        self._bus_lock = bus_lock
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
        if hasattr(self._device, "control"):
            remote_enable = getattr(self._device.control, "remote_enable", 0)
            if remote_enable == 1:
                power = getattr(self._device.control, "remote_active_power", 0)
                if power is not None:
                    if power < 0:
                        return WORK_MODE_FORCE_CHARGE
                    elif power > 0:
                        return WORK_MODE_FORCE_DISCHARGE

            mode = getattr(self._device.control, "work_mode", None)
            if isinstance(mode, WorkMode):
                return _REVERSE_WORK_MODE_MAP.get(mode, WORK_MODE_SELF_USE)

        return WORK_MODE_SELF_USE

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        bus_lock = self._bus_lock or getattr(
            self.coordinator,
            "bus_lock",
            getattr(self.coordinator, "_bus_lock", None),
        )

        if option == WORK_MODE_FORCE_CHARGE:
            power = 5000
            if getattr(self, "hass", None):
                if state := self.hass.states.get("number.force_charge_power"):
                    try:
                        power = int(float(state.state))
                    except (ValueError, TypeError):
                        pass
            if bus_lock:
                async with bus_lock:
                    await self._device.async_set_force_charge(power_w=power, max_soc=100)
            else:
                await self._device.async_set_force_charge(power_w=power, max_soc=100)

        elif option == WORK_MODE_FORCE_DISCHARGE:
            power = 5000
            min_soc = 10
            if getattr(self, "hass", None):
                if p_state := self.hass.states.get("number.force_discharge_power"):
                    try:
                        power = int(float(p_state.state))
                    except (ValueError, TypeError):
                        pass
                if s_state := self.hass.states.get("number.min_soc"):
                    try:
                        min_soc = int(float(s_state.state))
                    except (ValueError, TypeError):
                        pass
            if bus_lock:
                async with bus_lock:
                    await self._device.async_set_force_discharge(power_w=power, min_soc=min_soc)
            else:
                await self._device.async_set_force_discharge(power_w=power, min_soc=min_soc)

        elif option in _HARDWARE_WORK_MODES:
            mode = _HARDWARE_WORK_MODES[option]
            if bus_lock:
                async with bus_lock:
                    await self._device.async_clear_overrides()
                    await self._device.async_set_work_mode(mode)
            else:
                await self._device.async_clear_overrides()
                await self._device.async_set_work_mode(mode)

        await self.coordinator.async_request_refresh()
