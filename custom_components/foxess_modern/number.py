"""Number platform for FoxESS Modern configuration and setpoints."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FoxessConfigEntry
from .coordinator import FoxessDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FoxessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FoxESS Modern number entities from a config entry."""
    coordinator = entry.runtime_data.settings_coordinator
    device = entry.runtime_data.device
    serial = str(entry.unique_id)

    async_add_entities([
        FoxessMinSocNumber(coordinator, device, serial),
        FoxessForceChargePowerNumber(coordinator, device, serial),
        FoxessForceDischargePowerNumber(coordinator, device, serial),
    ])


class FoxessMinSocNumber(CoordinatorEntity[FoxessDataUpdateCoordinator], NumberEntity):
    """Number entity for setting Inverter Min SOC."""

    _attr_native_min_value = 10.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = "%"
    _attr_device_class = NumberDeviceClass.BATTERY
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: FoxessDataUpdateCoordinator, device: Any, serial: str) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_min_soc"
        self._attr_name = "Min SoC"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        """Return the current min SOC."""
        val = self._device.control.min_soc
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the min SOC."""
        await self._device.async_set_min_soc(int(value))
        await self.coordinator.async_request_refresh()


class FoxessForceChargePowerNumber(CoordinatorEntity[FoxessDataUpdateCoordinator], NumberEntity):
    """Number entity for setting Force Charge Power."""

    _attr_native_min_value = 0.0
    _attr_native_max_value = 10500.0
    _attr_native_step = 100.0
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = NumberDeviceClass.POWER
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: FoxessDataUpdateCoordinator, device: Any, serial: str) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_force_charge_power"
        self._attr_name = "Force Charge Power"
        self._attr_device_info = coordinator.device_info
        self._target_power: float = 5000.0

    @property
    def native_value(self) -> float:
        """Return target force charge power."""
        return self._target_power

    async def async_set_native_value(self, value: float) -> None:
        """Set the force charge power."""
        self._target_power = value


class FoxessForceDischargePowerNumber(CoordinatorEntity[FoxessDataUpdateCoordinator], NumberEntity):
    """Number entity for setting Force Discharge Power."""

    _attr_native_min_value = 0.0
    _attr_native_max_value = 10500.0
    _attr_native_step = 100.0
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = NumberDeviceClass.POWER
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: FoxessDataUpdateCoordinator, device: Any, serial: str) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_force_discharge_power"
        self._attr_name = "Force Discharge Power"
        self._attr_device_info = coordinator.device_info
        self._target_power: float = 5000.0

    @property
    def native_value(self) -> float:
        """Return target force discharge power."""
        return self._target_power

    async def async_set_native_value(self, value: float) -> None:
        """Set the force discharge power."""
        self._target_power = value
