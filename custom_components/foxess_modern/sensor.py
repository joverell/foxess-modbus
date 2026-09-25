"""Sensor platform for FoxESS Modern."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FoxessConfigEntry
from .const import CONF_MAPPINGS, LEGACY_DOMAIN
from .coordinator import FoxessDataUpdateCoordinator
from .migration import adopt_legacy_entity_id


def format_version(val: Any, is_hex: bool = False) -> str | None:
    """Format numeric firmware version into version string (e.g. 0x0164 -> 1.64 or 133 -> 1.33)."""
    if val is None:
        return None
    if isinstance(val, int):
        if is_hex:
            major = val >> 8
            minor = val & 0xFF
            return f"{major:X}.{minor:02X}"
        return f"{val // 100}.{val % 100:02d}"
    return str(val)


@dataclass(frozen=True, kw_only=True)
class FoxessSensorDescription(SensorEntityDescription):
    """Describes a FoxESS sensor entity."""

    value_fn: Callable[[Any], Any]


INVERTER_STATE_OPTIONS: list[str] = [
    "Self Test",
    "Waiting",
    "Checking",
    "On Grid",
    "Off Grid / EPS",
    "Recoverable Fault",
    "Unrecoverable Fault",
    "Standby",
    "Fault",
    "Unknown",
]


# Base sensors present across all supported FoxESS hybrid inverters
BASE_SENSOR_DESCRIPTIONS: tuple[FoxessSensorDescription, ...] = (
    # PV common
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
        key="pv1_current",
        name="PV1 Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda dev: dev.pv.pv1_current,
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
    FoxessSensorDescription(
        key="pv2_current",
        name="PV2 Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda dev: dev.pv.pv2_current,
    ),
    # Battery common
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
        key="battery_charge_power",
        name="Battery Charge Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: dev.battery.charge_power,
    ),
    FoxessSensorDescription(
        key="battery_discharge_power",
        name="Battery Discharge Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: dev.battery.discharge_power,
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
    # Grid frequency (common to single and 3-phase)
    FoxessSensorDescription(
        key="grid_frequency",
        name="Grid Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        value_fn=lambda dev: dev.grid.frequency,
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
        key="ambient_temperature",
        name="Ambient Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda dev: getattr(dev.inverter, "ambient_temp", None),
    ),
    FoxessSensorDescription(
        key="inverter_state",
        name="Inverter State",
        device_class=SensorDeviceClass.ENUM,
        options=INVERTER_STATE_OPTIONS,
        value_fn=lambda dev: str(dev.inverter.state) if getattr(dev.inverter, "state", None) is not None else None,
    ),
    FoxessSensorDescription(
        key="connection_status",
        name="Connection Status",
        icon="mdi:check-network-outline",
        value_fn=lambda dev: "Connected" if getattr(getattr(dev, "modbus_unit", None), "connected", True) else "Disconnected",
    ),
    FoxessSensorDescription(
        key="master_version",
        name="Master Firmware Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda dev: format_version(
            getattr(dev.inverter, "master_version", None),
            is_hex=getattr(dev.inverter, "version_is_hex", False),
        ),
    ),
    FoxessSensorDescription(
        key="slave_version",
        name="Slave Firmware Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda dev: format_version(
            getattr(dev.inverter, "slave_version", None),
            is_hex=getattr(dev.inverter, "version_is_hex", False),
        ),
    ),
    FoxessSensorDescription(
        key="manager_version",
        name="Manager Firmware Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda dev: format_version(
            getattr(dev.inverter, "manager_version", None),
            is_hex=getattr(dev.inverter, "version_is_hex", False),
        ),
    ),
)

# Extended MPPT sensors (PV3 and PV4 on 4-string inverters like KH)
PV3_PV4_DESCRIPTIONS: tuple[FoxessSensorDescription, ...] = (
    FoxessSensorDescription(
        key="pv3_power",
        name="PV3 Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.pv, "pv3_power", None),
    ),
    FoxessSensorDescription(
        key="pv3_voltage",
        name="PV3 Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: getattr(dev.pv, "pv3_voltage", None),
    ),
    FoxessSensorDescription(
        key="pv3_current",
        name="PV3 Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda dev: getattr(dev.pv, "pv3_current", None),
    ),
    FoxessSensorDescription(
        key="pv4_power",
        name="PV4 Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.pv, "pv4_power", None),
    ),
    FoxessSensorDescription(
        key="pv4_voltage",
        name="PV4 Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: getattr(dev.pv, "pv4_voltage", None),
    ),
    FoxessSensorDescription(
        key="pv4_current",
        name="PV4 Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda dev: getattr(dev.pv, "pv4_current", None),
    ),
)

# Multi-string PV sensors (H3-Pro: 6 PV strings)
PV5_PV6_DESCRIPTIONS: tuple[FoxessSensorDescription, ...] = (
    # PV5
    FoxessSensorDescription(
        key="pv5_power",
        name="PV5 Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.pv, "pv5_power", None),
    ),
    FoxessSensorDescription(
        key="pv5_voltage",
        name="PV5 Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: getattr(dev.pv, "pv5_voltage", None),
    ),
    FoxessSensorDescription(
        key="pv5_current",
        name="PV5 Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda dev: getattr(dev.pv, "pv5_current", None),
    ),
    # PV6
    FoxessSensorDescription(
        key="pv6_power",
        name="PV6 Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.pv, "pv6_power", None),
    ),
    FoxessSensorDescription(
        key="pv6_voltage",
        name="PV6 Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: getattr(dev.pv, "pv6_voltage", None),
    ),
    FoxessSensorDescription(
        key="pv6_current",
        name="PV6 Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda dev: getattr(dev.pv, "pv6_current", None),
    ),
)

# Single-phase grid sensors (KH, H1, AC1)
SINGLE_PHASE_GRID_DESCRIPTIONS: tuple[FoxessSensorDescription, ...] = (
    FoxessSensorDescription(
        key="grid_voltage",
        name="Grid Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: getattr(dev.grid, "voltage", None),
    ),
    FoxessSensorDescription(
        key="grid_current",
        name="Grid Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda dev: getattr(dev.grid, "current", None),
    ),
    FoxessSensorDescription(
        key="house_load_power",
        name="House Load Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "load_power", None),
    ),
    FoxessSensorDescription(
        key="grid_ct_meter_power",
        name="Grid CT Meter Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "ct_meter_power", None),
    ),
    FoxessSensorDescription(
        key="net_grid_power",
        name="Net Grid Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "ct_meter_power", None),
    ),
    FoxessSensorDescription(
        key="grid_import_power",
        name="Grid Import Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "grid_import_power", 0.0),
    ),
    FoxessSensorDescription(
        key="grid_export_power",
        name="Grid Export Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "grid_export_power", 0.0),
    ),
)

# Three-phase grid sensors (H3, AC3)
THREE_PHASE_GRID_DESCRIPTIONS: tuple[FoxessSensorDescription, ...] = (
    FoxessSensorDescription(
        key="grid_voltage_r",
        name="Grid Voltage Phase R",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: getattr(dev.grid, "voltage_r", None),
    ),
    FoxessSensorDescription(
        key="grid_current_r",
        name="Grid Current Phase R",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda dev: getattr(dev.grid, "current_r", None),
    ),
    FoxessSensorDescription(
        key="grid_power_r",
        name="Grid Power Phase R",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "power_r", None),
    ),
    FoxessSensorDescription(
        key="grid_voltage_s",
        name="Grid Voltage Phase S",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: getattr(dev.grid, "voltage_s", None),
    ),
    FoxessSensorDescription(
        key="grid_current_s",
        name="Grid Current Phase S",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda dev: getattr(dev.grid, "current_s", None),
    ),
    FoxessSensorDescription(
        key="grid_power_s",
        name="Grid Power Phase S",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "power_s", None),
    ),
    FoxessSensorDescription(
        key="grid_voltage_t",
        name="Grid Voltage Phase T",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: getattr(dev.grid, "voltage_t", None),
    ),
    FoxessSensorDescription(
        key="grid_current_t",
        name="Grid Current Phase T",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda dev: getattr(dev.grid, "current_t", None),
    ),
    FoxessSensorDescription(
        key="grid_power_t",
        name="Grid Power Phase T",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "power_t", None),
    ),
    FoxessSensorDescription(
        key="grid_power_total",
        name="Grid Power Total",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "grid_power_total", None),
    ),
    FoxessSensorDescription(
        key="net_grid_power",
        name="Net Grid Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "grid_power_total", None),
    ),
)

# Single-phase EPS sensors (KH, H1)
SINGLE_PHASE_EPS_DESCRIPTIONS: tuple[FoxessSensorDescription, ...] = (
    FoxessSensorDescription(
        key="eps_voltage",
        name="EPS Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda dev: getattr(dev.grid, "eps_voltage", None),
    ),
    FoxessSensorDescription(
        key="eps_current",
        name="EPS Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda dev: getattr(dev.grid, "eps_current", None),
    ),
    FoxessSensorDescription(
        key="eps_power",
        name="EPS Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "eps_power", None),
    ),
    FoxessSensorDescription(
        key="eps_frequency",
        name="EPS Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        value_fn=lambda dev: getattr(dev.grid, "eps_frequency", None),
    ),
)

# Three-phase EPS sensors (H3)
THREE_PHASE_EPS_DESCRIPTIONS: tuple[FoxessSensorDescription, ...] = (
    FoxessSensorDescription(
        key="eps_power_r",
        name="EPS Power Phase R",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "eps_power_r", None),
    ),
    FoxessSensorDescription(
        key="eps_power_s",
        name="EPS Power Phase S",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "eps_power_s", None),
    ),
    FoxessSensorDescription(
        key="eps_power_t",
        name="EPS Power Phase T",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "eps_power_t", None),
    ),
    FoxessSensorDescription(
        key="eps_power_total",
        name="EPS Power Total",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda dev: getattr(dev.grid, "eps_power_total", None),
    ),
    FoxessSensorDescription(
        key="eps_frequency",
        name="EPS Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        value_fn=lambda dev: getattr(dev.grid, "eps_frequency", None),
    ),
)

CT2_SENSOR_DESCRIPTION = FoxessSensorDescription(
    key="ct2_power",
    name="CT2 Meter Power",
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=UnitOfPower.WATT,
    value_fn=lambda dev: getattr(dev.grid, "ct2_power", None),
)

EPS_REACTIVE_POWER_DESCRIPTION = FoxessSensorDescription(
    key="eps_reactive_power",
    name="EPS Reactive Power",
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement="var",
    value_fn=lambda dev: getattr(dev.grid, "eps_reactive_power", None),
)


BMS_SENSOR_DESCRIPTIONS: tuple[FoxessSensorDescription, ...] = (
    FoxessSensorDescription(
        key="bms_cell_temp_high",
        name="BMS Cell Temp High",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda dev: getattr(getattr(dev, "bms", None), "bms_cell_temp_high", None),
    ),
    FoxessSensorDescription(
        key="bms_cell_temp_low",
        name="BMS Cell Temp Low",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda dev: getattr(getattr(dev, "bms", None), "bms_cell_temp_low", None),
    ),
    FoxessSensorDescription(
        key="bms_cell_mv_high",
        name="BMS Cell mV High",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="mV",
        value_fn=lambda dev: getattr(getattr(dev, "bms", None), "bms_cell_mv_high", None),
    ),
    FoxessSensorDescription(
        key="bms_cell_mv_low",
        name="BMS Cell mV Low",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="mV",
        value_fn=lambda dev: getattr(getattr(dev, "bms", None), "bms_cell_mv_low", None),
    ),
    FoxessSensorDescription(
        key="battery_soh",
        name="Battery SoH",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        value_fn=lambda dev: getattr(getattr(dev, "bms", None), "battery_soh", None),
    ),
    FoxessSensorDescription(
        key="bms_kwh_remaining",
        name="BMS kWh Remaining",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "bms", None), "bms_kwh_remaining", None),
    ),
)

HARDWARE_ENERGY_DESCRIPTIONS: tuple[FoxessSensorDescription, ...] = (
    FoxessSensorDescription(
        key="solar_energy_total",
        name="Solar Energy Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "solar_energy_total", None),
    ),
    FoxessSensorDescription(
        key="solar_energy_today",
        name="Solar Energy Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "solar_energy_today", None),
    ),
    FoxessSensorDescription(
        key="battery_charge_energy_total",
        name="Battery Charge Energy Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "battery_charge_energy_total", None),
    ),
    FoxessSensorDescription(
        key="battery_charge_energy_today",
        name="Battery Charge Energy Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "battery_charge_energy_today", None),
    ),
    FoxessSensorDescription(
        key="battery_discharge_energy_total",
        name="Battery Discharge Energy Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "battery_discharge_energy_total", None),
    ),
    FoxessSensorDescription(
        key="battery_discharge_energy_today",
        name="Battery Discharge Energy Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "battery_discharge_energy_today", None),
    ),
    FoxessSensorDescription(
        key="grid_export_energy_total",
        name="Grid Export Energy Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "grid_export_energy_total", None),
    ),
    FoxessSensorDescription(
        key="grid_export_energy_today",
        name="Grid Export Energy Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "grid_export_energy_today", None),
    ),
    FoxessSensorDescription(
        key="grid_import_energy_total",
        name="Grid Import Energy Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "grid_import_energy_total", None),
    ),
    FoxessSensorDescription(
        key="grid_import_energy_today",
        name="Grid Import Energy Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "grid_import_energy_today", None),
    ),
    FoxessSensorDescription(
        key="total_yield_total",
        name="Total Yield Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "total_yield_total", None),
    ),
    FoxessSensorDescription(
        key="total_yield_today",
        name="Total Yield Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "total_yield_today", None),
    ),
    FoxessSensorDescription(
        key="load_energy_total",
        name="Load Energy Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "load_energy_total", None),
    ),
    FoxessSensorDescription(
        key="load_energy_today",
        name="Load Energy Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda dev: getattr(getattr(dev, "energy", None), "load_energy_today", None),
    ),
)


ENERGY_SENSOR_DESCRIPTIONS: tuple[tuple[str, str, Callable[[Any], float | None]], ...] = (
    (
        "pv_energy_total",
        "Solar Energy Total",
        lambda dev: getattr(dev.pv, "pv_power_total", None),
    ),
    (
        "grid_import_energy_total",
        "Grid Import Energy Total",
        lambda dev: getattr(dev.grid, "grid_import_power", None),
    ),
    (
        "grid_export_energy_total",
        "Grid Export Energy Total",
        lambda dev: getattr(dev.grid, "grid_export_power", None),
    ),
    (
        "battery_charge_energy_total",
        "Battery Charge Energy Total",
        lambda dev: getattr(dev.battery, "charge_power", None),
    ),
    (
        "battery_discharge_energy_total",
        "Battery Discharge Energy Total",
        lambda dev: getattr(dev.battery, "discharge_power", None),
    ),
    (
        "load_energy_total",
        "Load Energy Total",
        lambda dev: getattr(dev.grid, "load_power", None),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FoxessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FoxESS sensors from a config entry dynamically according to model capabilities."""
    coordinator = entry.runtime_data.readings_coordinator
    device = entry.runtime_data.device
    serial = str(entry.unique_id)
    mappings: dict[str, str] = entry.options.get(
        CONF_MAPPINGS, entry.data.get(CONF_MAPPINGS, {})
    )

    descriptions: list[FoxessSensorDescription] = list(BASE_SENSOR_DESCRIPTIONS)

    # 1. Check for BMS detailed telemetry (e.g. KH series)
    if hasattr(device, "bms"):
        descriptions.extend(BMS_SENSOR_DESCRIPTIONS)

    # 2. Check for 4-string MPPT support (e.g. KH series)
    if hasattr(device.pv, "pv3_power"):
        descriptions.extend(PV3_PV4_DESCRIPTIONS)

    # 3. Check for 6-string MPPT support (e.g. H3-Pro series)
    if hasattr(device.pv, "pv5_power"):
        descriptions.extend(PV5_PV6_DESCRIPTIONS)

    # 4. Check for three-phase vs single-phase grid metering and EPS capabilities
    if hasattr(device.grid, "voltage_r"):
        descriptions.extend(THREE_PHASE_GRID_DESCRIPTIONS)
        if hasattr(device.grid, "eps_power_total"):
            descriptions.extend(THREE_PHASE_EPS_DESCRIPTIONS)
    elif hasattr(device.grid, "voltage"):
        descriptions.extend(SINGLE_PHASE_GRID_DESCRIPTIONS)
        if hasattr(device.grid, "eps_power"):
            descriptions.extend(SINGLE_PHASE_EPS_DESCRIPTIONS)
        if hasattr(device.grid, "eps_reactive_power"):
            descriptions.append(EPS_REACTIVE_POWER_DESCRIPTION)
        if hasattr(device.grid, "ct2_power"):
            descriptions.append(CT2_SENSOR_DESCRIPTION)

    # 5. Check for hardware cumulative energy counters (e.g. KH series)
    has_hardware_energy = hasattr(device, "energy")
    if has_hardware_energy:
        descriptions.extend(HARDWARE_ENERGY_DESCRIPTIONS)

    entity_reg = er.async_get(hass)
    entities: list[SensorEntity] = []
    for description in descriptions:
        mapped_id = mappings.get(description.key)
        target_id = adopt_legacy_entity_id(
            entity_reg,
            key=description.key,
            domain="sensor",
            serial=serial,
            explicit_mapped_id=mapped_id,
        )
        entities.append(
            FoxessSensorEntity(
                coordinator,
                description,
                device,
                serial,
                target_entity_id=target_id,
            )
        )

    # 6. Add software Riemann sum energy sensors only for devices lacking hardware energy registers
    if not has_hardware_energy:
        for key, name, power_fn in ENERGY_SENSOR_DESCRIPTIONS:
            mapped_id = mappings.get(key)
            target_id = adopt_legacy_entity_id(
                entity_reg,
                key=key,
                domain="sensor",
                serial=serial,
                explicit_mapped_id=mapped_id,
            )
            entities.append(
                FoxessEnergySensor(
                    coordinator=coordinator,
                    key=key,
                    name=name,
                    power_fn=power_fn,
                    device=device,
                    serial=serial,
                    target_entity_id=target_id,
                )
            )

    async_add_entities(entities)


class FoxessSensorEntity(CoordinatorEntity[FoxessDataUpdateCoordinator], SensorEntity):
    """Representation of a FoxESS Modern sensor."""

    entity_description: FoxessSensorDescription
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        description: FoxessSensorDescription,
        device: Any,
        serial: str,
        target_entity_id: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device = device
        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_device_info = coordinator.device_info
        raw_id = target_entity_id or suggested_object_id
        if raw_id:
            self.entity_id = raw_id if "." in raw_id else f"sensor.{raw_id}"
            self._attr_suggested_object_id = raw_id.split(".", 1)[-1]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self.entity_description.key == "connection_status":
            return True
        if self.entity_description.key in (
            "master_version",
            "slave_version",
            "manager_version",
            "inverter_state",
        ):
            if self.native_value is not None:
                return True
        return self.coordinator.is_available

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.entity_description.key == "connection_status":
            if self.coordinator.timeouts >= 3 or not self.coordinator.is_available:
                return "Disconnected"
            unit = getattr(self._device, "modbus_unit", None)
            is_connected = bool(getattr(unit, "connected", False)) if unit else False
            if not is_connected and (self.coordinator.data is None or self.coordinator.timeouts >= 2):
                return "Disconnected"
            return "Connected"
        return self.entity_description.value_fn(self._device)


class FoxessEnergySensor(CoordinatorEntity[FoxessDataUpdateCoordinator], RestoreSensor):
    """Cumulative energy sensor (kWh) calculated via Riemann integration for HA Energy Dashboard."""

    _attr_has_entity_name = False
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: FoxessDataUpdateCoordinator,
        key: str,
        name: str,
        power_fn: Callable[[Any], float | None],
        device: Any,
        serial: str,
        target_entity_id: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        """Initialize the energy accumulator sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._power_fn = power_fn
        self._device = device
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_device_info = coordinator.device_info
        raw_id = target_entity_id or suggested_object_id
        if raw_id:
            self.entity_id = raw_id if "." in raw_id else f"sensor.{raw_id}"
            self._attr_suggested_object_id = raw_id.split(".", 1)[-1]
        self._total_kwh: float = 0.0
        self._last_time: float | None = None

    async def async_added_to_hass(self) -> None:
        """Handle entity restore and registration."""
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            if last_data.native_value is not None:
                try:
                    self._total_kwh = float(last_data.native_value)
                except (ValueError, TypeError):
                    self._total_kwh = 0.0
        self._last_time = time.monotonic()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Calculate and accumulate energy on each coordinator update."""
        now = time.monotonic()
        power = self._power_fn(self._device)

        if self._last_time is not None and power is not None and power > 0:
            dt = now - self._last_time
            # Ignore polling gaps > 15 minutes (e.g. system restarts or long outages)
            if 0 < dt < 900:
                kwh = (float(power) / 1000.0) * (dt / 3600.0)
                self._total_kwh += kwh

        self._last_time = now
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True so long-term energy statistics persist across night power-downs."""
        return True

    @property
    def native_value(self) -> float:
        """Return the total accumulated energy in kWh."""
        return round(self._total_kwh, 2)
