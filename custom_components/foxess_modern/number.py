"""Number platform for FoxESS Modern configuration and setpoints."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfElectricCurrent, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FoxessConfigEntry
from .const import CONF_MAPPINGS
from .coordinator import FoxessDataUpdateCoordinator
from .migration import adopt_legacy_entity_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FoxessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FoxESS Modern number entities from a config entry."""
    coordinator = entry.runtime_data.settings_coordinator
    device = entry.runtime_data.device
    serial = str(entry.unique_id)
    mappings: dict[str, str] = entry.options.get(
        CONF_MAPPINGS, entry.data.get(CONF_MAPPINGS, {})
    )
    entity_reg = er.async_get(hass)

    entities: list[NumberEntity] = []

    def _get_target_id(key: str) -> str:
        return adopt_legacy_entity_id(
            entity_reg,
            key=key,
            domain="number",
            serial=serial,
            explicit_mapped_id=mappings.get(key),
        )

    # 1. Min SoC
    if hasattr(device.control, "min_soc"):
        entities.append(
            FoxessMinSocNumber(
                coordinator, device, serial, target_entity_id=_get_target_id("min_soc")
            )
        )

    # 2. Max SoC
    if hasattr(device.control, "max_soc"):
        entities.append(
            FoxessMaxSocNumber(
                coordinator, device, serial, target_entity_id=_get_target_id("max_soc")
            )
        )

    # 3. Min SoC On Grid
    if hasattr(device.control, "min_soc_on_grid"):
        entities.append(
            FoxessMinSocOnGridNumber(
                coordinator,
                device,
                serial,
                target_entity_id=_get_target_id("min_soc_on_grid"),
            )
        )

    # 4. Max Charge Current
    if hasattr(device.control, "max_charge_current"):
        entities.append(
            FoxessMaxChargeCurrentNumber(
                coordinator,
                device,
                serial,
                target_entity_id=_get_target_id("max_charge_current"),
            )
        )

    # 5. Max Discharge Current
    if hasattr(device.control, "max_discharge_current"):
        entities.append(
            FoxessMaxDischargeCurrentNumber(
                coordinator,
                device,
                serial,
                target_entity_id=_get_target_id("max_discharge_current"),
            )
        )

    # 6. Export Power Limit
    if hasattr(device.control, "export_power_limit"):
        entities.append(
            FoxessExportPowerLimitNumber(
                coordinator,
                device,
                serial,
                target_entity_id=_get_target_id("export_power_limit"),
            )
        )

    # 7. Import Power Limit
    if hasattr(device.control, "import_power_limit"):
        entities.append(
            FoxessImportPowerLimitNumber(
                coordinator,
                device,
                serial,
                target_entity_id=_get_target_id("import_power_limit"),
            )
        )

    # 8. Force Charge & Force Discharge Power
    entities.append(
        FoxessForceChargePowerNumber(
            coordinator,
            device,
            serial,
            target_entity_id=_get_target_id("force_charge_power"),
        )
    )
    entities.append(
        FoxessForceDischargePowerNumber(
            coordinator,
            device,
            serial,
            target_entity_id=_get_target_id("force_discharge_power"),
        )
    )

class FoxessBaseNumberEntity(CoordinatorEntity[FoxessDataUpdateCoordinator], NumberEntity):
    """Base class for FoxESS Modern number entities."""

    _attr_has_entity_name = False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.is_available


class FoxessMinSocNumber(FoxessBaseNumberEntity):
    """Number entity for setting Inverter Min SOC."""

    _attr_native_min_value = 10.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = "%"
    _attr_device_class = NumberDeviceClass.BATTERY
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        device: Any,
        serial: str,
        target_entity_id: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_min_soc"
        self._attr_name = "Min SoC"
        self._attr_device_info = coordinator.device_info
        raw_id = target_entity_id or suggested_object_id
        if raw_id:
            if not raw_id.startswith("number."):
                raw_id = f"number.{raw_id}"
            self.entity_id = raw_id
            self._attr_suggested_object_id = raw_id.split(".", 1)[-1]
        elif suggested_object_id:
            self._attr_suggested_object_id = suggested_object_id

    @property
    def native_value(self) -> float | None:
        """Return the current min SOC."""
        val = self._device.control.min_soc
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the min SOC."""
        await self._device.async_set_min_soc(int(value))
        await self.coordinator.async_request_refresh()


class FoxessMaxSocNumber(FoxessBaseNumberEntity):
    """Number entity for setting Inverter Max SOC."""

    _attr_native_min_value = 10.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = "%"
    _attr_device_class = NumberDeviceClass.BATTERY
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        device: Any,
        serial: str,
        target_entity_id: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_max_soc"
        self._attr_name = "Max SoC"
        self._attr_device_info = coordinator.device_info
        raw_id = target_entity_id or suggested_object_id
        if raw_id:
            if not raw_id.startswith("number."):
                raw_id = f"number.{raw_id}"
            self.entity_id = raw_id
            self._attr_suggested_object_id = raw_id.split(".", 1)[-1]
        elif suggested_object_id:
            self._attr_suggested_object_id = suggested_object_id

    @property
    def native_value(self) -> float | None:
        """Return the current max SOC."""
        val = self._device.control.max_soc
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the max SOC."""
        await self._device.async_set_max_soc(int(value))
        await self.coordinator.async_request_refresh()


class FoxessMinSocOnGridNumber(FoxessBaseNumberEntity):
    """Number entity for setting Inverter Min SOC on Grid."""

    _attr_native_min_value = 10.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = "%"
    _attr_device_class = NumberDeviceClass.BATTERY
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        device: Any,
        serial: str,
        target_entity_id: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_min_soc_on_grid"
        self._attr_name = "Min SoC (On Grid)"
        self._attr_device_info = coordinator.device_info
        raw_id = target_entity_id or suggested_object_id
        if raw_id:
            if not raw_id.startswith("number."):
                raw_id = f"number.{raw_id}"
            self.entity_id = raw_id
            self._attr_suggested_object_id = raw_id.split(".", 1)[-1]
        elif suggested_object_id:
            self._attr_suggested_object_id = suggested_object_id

    @property
    def native_value(self) -> float | None:
        """Return the current min SOC on grid."""
        val = self._device.control.min_soc_on_grid
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the min SOC on grid."""
        await self._device.async_set_min_soc_on_grid(int(value))
        await self.coordinator.async_request_refresh()


class FoxessMaxChargeCurrentNumber(FoxessBaseNumberEntity):
    """Number entity for setting Max Charge Current."""

    _attr_native_min_value = 0.0
    _attr_native_max_value = 50.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        device: Any,
        serial: str,
        target_entity_id: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_max_charge_current"
        self._attr_name = "Max Charge Current"
        self._attr_device_info = coordinator.device_info
        raw_id = target_entity_id or suggested_object_id
        if raw_id:
            if not raw_id.startswith("number."):
                raw_id = f"number.{raw_id}"
            self.entity_id = raw_id
            self._attr_suggested_object_id = raw_id.split(".", 1)[-1]
        elif suggested_object_id:
            self._attr_suggested_object_id = suggested_object_id

    @property
    def native_value(self) -> float | None:
        """Return the max charge current."""
        val = self._device.control.max_charge_current
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the max charge current."""
        await self._device.async_set_max_charge_current(value)
        await self.coordinator.async_request_refresh()


class FoxessMaxDischargeCurrentNumber(FoxessBaseNumberEntity):
    """Number entity for setting Max Discharge Current."""

    _attr_native_min_value = 0.0
    _attr_native_max_value = 50.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        device: Any,
        serial: str,
        target_entity_id: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_max_discharge_current"
        self._attr_name = "Max Discharge Current"
        self._attr_device_info = coordinator.device_info
        raw_id = target_entity_id or suggested_object_id
        if raw_id:
            if not raw_id.startswith("number."):
                raw_id = f"number.{raw_id}"
            self.entity_id = raw_id
            self._attr_suggested_object_id = raw_id.split(".", 1)[-1]
        elif suggested_object_id:
            self._attr_suggested_object_id = suggested_object_id

    @property
    def native_value(self) -> float | None:
        """Return the max discharge current."""
        val = self._device.control.max_discharge_current
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the max discharge current."""
        await self._device.async_set_max_discharge_current(value)
        await self.coordinator.async_request_refresh()


class FoxessExportPowerLimitNumber(FoxessBaseNumberEntity):
    """Number entity for setting Export Power Limit."""

    _attr_native_min_value = 0.0
    _attr_native_max_value = 99999.0
    _attr_native_step = 100.0
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = NumberDeviceClass.POWER
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        device: Any,
        serial: str,
        target_entity_id: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_export_power_limit"
        self._attr_name = "Export Power Limit"
        self._attr_device_info = coordinator.device_info
        raw_id = target_entity_id or suggested_object_id
        if raw_id:
            if not raw_id.startswith("number."):
                raw_id = f"number.{raw_id}"
            self.entity_id = raw_id
            self._attr_suggested_object_id = raw_id.split(".", 1)[-1]
        elif suggested_object_id:
            self._attr_suggested_object_id = suggested_object_id

    @property
    def native_value(self) -> float | None:
        """Return the export power limit."""
        val = self._device.control.export_power_limit
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the export power limit."""
        await self._device.async_set_export_power_limit(int(value))
        await self.coordinator.async_request_refresh()


class FoxessImportPowerLimitNumber(FoxessBaseNumberEntity):
    """Number entity for setting Import Power Limit."""

    _attr_native_min_value = 0.0
    _attr_native_max_value = 99999.0
    _attr_native_step = 100.0
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = NumberDeviceClass.POWER
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        device: Any,
        serial: str,
        target_entity_id: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_import_power_limit"
        self._attr_name = "Import Power Limit"
        self._attr_device_info = coordinator.device_info
        raw_id = target_entity_id or suggested_object_id
        if raw_id:
            if not raw_id.startswith("number."):
                raw_id = f"number.{raw_id}"
            self.entity_id = raw_id
            self._attr_suggested_object_id = raw_id.split(".", 1)[-1]
        elif suggested_object_id:
            self._attr_suggested_object_id = suggested_object_id

    @property
    def native_value(self) -> float | None:
        """Return the import power limit."""
        val = self._device.control.import_power_limit
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the import power limit."""
        await self._device.async_set_import_power_limit(int(value))
        await self.coordinator.async_request_refresh()


def get_max_inverter_power(device: Any) -> float:
    """Determine maximum charge/discharge power limit based on inverter model."""
    name = (
        str(getattr(device, "model", "") or getattr(device, "series", ""))
        or type(device).__name__
    ).upper()
    if "PRO" in name or "H3-PRO" in name or "30" in name:
        return 30000.0
    if "H3" in name or "AC3" in name:
        return 12000.0
    if "KH" in name:
        return 10500.0
    if "H1" in name or "AC1" in name:
        return 6000.0
    return 30000.0


class FoxessForceChargePowerNumber(FoxessBaseNumberEntity):
    """Number entity for setting Force Charge Power."""

    _attr_native_min_value = 0.0
    _attr_native_step = 100.0
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = NumberDeviceClass.POWER
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        device: Any,
        serial: str,
        target_entity_id: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_force_charge_power"
        self._attr_name = "Force Charge Power"
        self._attr_device_info = coordinator.device_info
        self._attr_native_max_value = get_max_inverter_power(device)
        self._target_power: float = 5000.0
        raw_id = target_entity_id or suggested_object_id
        if raw_id:
            if not raw_id.startswith("number."):
                raw_id = f"number.{raw_id}"
            self.entity_id = raw_id
            self._attr_suggested_object_id = raw_id.split(".", 1)[-1]
        elif suggested_object_id:
            self._attr_suggested_object_id = suggested_object_id

    @property
    def native_value(self) -> float:
        """Return target force charge power."""
        return self._target_power

    async def async_set_native_value(self, value: float) -> None:
        """Set the force charge power."""
        self._target_power = value


class FoxessForceDischargePowerNumber(FoxessBaseNumberEntity):
    """Number entity for setting Force Discharge Power."""

    _attr_native_min_value = 0.0
    _attr_native_step = 100.0
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = NumberDeviceClass.POWER
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        device: Any,
        serial: str,
        target_entity_id: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{serial}_force_discharge_power"
        self._attr_name = "Force Discharge Power"
        self._attr_device_info = coordinator.device_info
        self._attr_native_max_value = get_max_inverter_power(device)
        self._target_power: float = 5000.0
        raw_id = target_entity_id or suggested_object_id
        if raw_id:
            if not raw_id.startswith("number."):
                raw_id = f"number.{raw_id}"
            self.entity_id = raw_id
            self._attr_suggested_object_id = raw_id.split(".", 1)[-1]
        elif suggested_object_id:
            self._attr_suggested_object_id = suggested_object_id

    @property
    def native_value(self) -> float:
        """Return target force discharge power."""
        return self._target_power

    async def async_set_native_value(self, value: float) -> None:
        """Set the force discharge power."""
        self._target_power = value
