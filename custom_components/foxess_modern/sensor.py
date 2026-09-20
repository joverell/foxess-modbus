"""Sensor platform for FoxESS Modern."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FoxessConfigEntry
from .coordinator import FoxessDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class FoxessSensorDescription(SensorEntityDescription):
    """Describes a FoxESS sensor entity."""

    value_fn: Callable[[Any], Any]


SENSOR_DESCRIPTIONS: tuple[FoxessSensorDescription, ...] = (
    # PV sensors
    FoxessSensorDescription(
        key="pv_power_total",
        name="PV Power Total",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: dev.pv.pv_power_total,
    ),
    FoxessSensorDescription(
        key="pv1_power",
        name="PV1 Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: dev.pv.pv1_power,
    ),
    FoxessSensorDescription(
        key="pv1_voltage",
        name="PV1 Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: dev.pv.pv1_voltage,
    ),
    FoxessSensorDescription(
        key="pv2_power",
        name="PV2 Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: dev.pv.pv2_power,
    ),
    FoxessSensorDescription(
        key="pv2_voltage",
        name="PV2 Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: dev.pv.pv2_voltage,
    ),
    # Battery sensors
    FoxessSensorDescription(
        key="battery_soc",
        name="Battery SoC",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        value_fn=lambda dev: dev.battery.soc,
    ),
    FoxessSensorDescription(
        key="battery_power",
        name="Battery Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: dev.battery.power,
    ),
    FoxessSensorDescription(
        key="battery_voltage",
        name="Battery Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: dev.battery.voltage,
    ),
    FoxessSensorDescription(
        key="battery_current",
        name="Battery Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda dev: dev.battery.current,
    ),
    FoxessSensorDescription(
        key="battery_temperature",
        name="Battery Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda dev: dev.battery.temperature,
    ),
    # Grid sensors
    FoxessSensorDescription(
        key="grid_voltage",
        name="Grid Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: dev.grid.voltage,
    ),
    FoxessSensorDescription(
        key="grid_frequency",
        name="Grid Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        value_fn=lambda dev: dev.grid.frequency,
    ),
    FoxessSensorDescription(
        key="house_load_power",
        name="House Load Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: dev.grid.load_power,
    ),
    FoxessSensorDescription(
        key="grid_ct_meter_power",
        name="Grid CT Meter Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: dev.grid.ct_meter_power,
    ),
    # Inverter health
    FoxessSensorDescription(
        key="inverter_temperature",
        name="Inverter Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda dev: dev.inverter.inverter_temp,
    ),
    FoxessSensorDescription(
        key="inverter_state",
        name="Inverter State",
        device_class=SensorDeviceClass.ENUM,
        value_fn=lambda dev: str(dev.inverter.state) if dev.inverter.state is not None else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FoxessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FoxESS sensors from a config entry."""
    coordinator = entry.runtime_data.readings_coordinator
    device = entry.runtime_data.device

    async_add_entities(
        FoxessSensorEntity(coordinator, description, device, str(entry.unique_id))
        for description in SENSOR_DESCRIPTIONS
    )


class FoxessSensorEntity(CoordinatorEntity[FoxessDataUpdateCoordinator], SensorEntity):
    """Representation of a FoxESS Modern sensor."""

    entity_description: FoxessSensorDescription

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        description: FoxessSensorDescription,
        device: Any,
        serial: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device = device
        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self._device)
