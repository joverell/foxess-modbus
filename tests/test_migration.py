import sys
import types
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

if "voluptuous" not in sys.modules:
    mock_vol = MagicMock()
    mock_vol.Schema = lambda s: s
    mock_vol.Required = lambda k, **kw: k
    mock_vol.Optional = lambda k, **kw: k
    mock_vol.In = lambda opts: opts
    sys.modules["voluptuous"] = mock_vol

# Mock homeassistant package hierarchy for standalone testing
ha_modules = [
    "homeassistant",
    "homeassistant.core",
    "homeassistant.config_entries",
    "homeassistant.exceptions",
    "homeassistant.const",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.entity_registry",
    "homeassistant.components",
    "homeassistant.components.modbus",
    "homeassistant.components.sensor",
    "homeassistant.components.select",
    "homeassistant.components.number",
]

for name in ha_modules:
    if name not in sys.modules:
        mod = types.ModuleType(name)
        mod.__path__ = []
        sys.modules[name] = mod


class MockHomeAssistantError(Exception):
    pass


class MockConfigEntryNotReady(MockHomeAssistantError):
    pass


class MockUpdateFailed(MockHomeAssistantError):
    pass


class MockConfigFlow:
    def __init_subclass__(cls, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)


class MockOptionsFlow:
    pass


class MockSensorEntity:
    pass


class MockRestoreSensor(MockSensorEntity):
    pass


class MockSelectEntity:
    pass


class MockNumberEntity:
    pass


class MockCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def __class_getitem__(cls, item):
        return cls


class MockDataUpdateCoordinator:
    def __init__(self, *args, **kwargs):
        pass

    def __class_getitem__(cls, item):
        return cls


def mock_callback(fn):
    return fn


sys.modules["homeassistant.exceptions"].HomeAssistantError = MockHomeAssistantError
sys.modules["homeassistant.exceptions"].ConfigEntryNotReady = MockConfigEntryNotReady
sys.modules["homeassistant.config_entries"].ConfigFlow = MockConfigFlow
sys.modules["homeassistant.config_entries"].OptionsFlow = MockOptionsFlow
sys.modules["homeassistant.config_entries"].ConfigEntry = MagicMock
sys.modules["homeassistant.config_entries"].ConfigFlowResult = MagicMock
class MockNumberDeviceClass:
    BATTERY = "battery"
    POWER = "power"


class MockSensorDeviceClass:
    POWER = "power"
    VOLTAGE = "voltage"
    CURRENT = "current"
    ENERGY = "energy"
    BATTERY = "battery"
    TEMPERATURE = "temperature"
    FREQUENCY = "frequency"
    ENUM = "enum"


class MockSensorStateClass:
    MEASUREMENT = "measurement"
    TOTAL_INCREASING = "total_increasing"
    TOTAL = "total"


class MockNumberMode:
    BOX = "box"
    SLIDER = "slider"
    AUTO = "auto"


@dataclass(frozen=True, kw_only=True)
class MockSensorEntityDescription:
    key: str = ""
    device_class: Any = None
    state_class: Any = None
    native_unit_of_measurement: Any = None
    suggested_display_precision: Any = None
    name: str | None = None
    options: Any = None


sys.modules["homeassistant.components.sensor"].SensorEntity = MockSensorEntity
sys.modules["homeassistant.components.sensor"].RestoreSensor = MockRestoreSensor
sys.modules["homeassistant.components.sensor"].SensorEntityDescription = MockSensorEntityDescription
sys.modules["homeassistant.components.sensor"].SensorDeviceClass = MockSensorDeviceClass
sys.modules["homeassistant.components.sensor"].SensorStateClass = MockSensorStateClass
sys.modules["homeassistant.components.select"].SelectEntity = MockSelectEntity
sys.modules["homeassistant.components.number"].NumberEntity = MockNumberEntity
sys.modules["homeassistant.components.number"].NumberDeviceClass = MockNumberDeviceClass
sys.modules["homeassistant.components.number"].NumberMode = MockNumberMode
sys.modules["homeassistant.components.modbus"].async_get_unit = MagicMock()
sys.modules["homeassistant.components.modbus"].async_get_temporary_unit = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = MockCoordinatorEntity
sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = MockDataUpdateCoordinator
sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = MockUpdateFailed
sys.modules["homeassistant.helpers.device_registry"].DeviceInfo = MagicMock
sys.modules["homeassistant.helpers.entity_platform"].AddConfigEntryEntitiesCallback = MagicMock
sys.modules["homeassistant.core"].callback = mock_callback
sys.modules["homeassistant.core"].HomeAssistant = MagicMock
class MockPlatform:
    SENSOR = "sensor"
    SELECT = "select"
    NUMBER = "number"


class MockUnitOfPower:
    WATT = "W"
    KILO_WATT = "kW"


class MockUnitOfEnergy:
    KILO_WATT_HOUR = "kWh"
    WATT_HOUR = "Wh"


class MockUnitOfElectricCurrent:
    AMPERE = "A"


class MockUnitOfElectricPotential:
    VOLT = "V"


class MockUnitOfFrequency:
    HERTZ = "Hz"


class MockUnitOfTemperature:
    CELSIUS = "°C"


sys.modules["homeassistant.const"].Platform = MockPlatform
sys.modules["homeassistant.const"].UnitOfPower = MockUnitOfPower
sys.modules["homeassistant.const"].UnitOfEnergy = MockUnitOfEnergy
sys.modules["homeassistant.const"].UnitOfElectricCurrent = MockUnitOfElectricCurrent
sys.modules["homeassistant.const"].UnitOfElectricPotential = MockUnitOfElectricPotential
sys.modules["homeassistant.const"].UnitOfFrequency = MockUnitOfFrequency
sys.modules["homeassistant.const"].UnitOfTemperature = MockUnitOfTemperature

# Now import foxess_modern modules
from custom_components.foxess_modern.config_flow import find_smart_matches
from custom_components.foxess_modern.const import (
    DEFAULT_CREATE_NEW,
    MIGRATABLE_KEYS,
)
from custom_components.foxess_modern.number import FoxessMinSocNumber
from custom_components.foxess_modern.select import FoxessWorkModeSelect
from custom_components.foxess_modern.sensor import (
    BASE_SENSOR_DESCRIPTIONS,
    FoxessEnergySensor,
    FoxessSensorEntity,
)


@dataclass
class MockRegistryEntry:
    entity_id: str
    domain: str
    platform: str


class MockEntityRegistry:
    def __init__(self, entities: list[MockRegistryEntry]) -> None:
        self.entities = {e.entity_id: e for e in entities}


def test_find_smart_matches_empty():
    """Test smart matching with an empty registry defaults to create new."""
    reg = MockEntityRegistry([])
    matches = find_smart_matches(reg)

    for key, _label, _platform in MIGRATABLE_KEYS:
        assert key in matches
        options, default_val = matches[key]
        assert default_val == DEFAULT_CREATE_NEW
        assert options == [DEFAULT_CREATE_NEW]


def test_find_smart_matches_with_legacy_entities():
    """Test smart matching correctly pairs legacy entity IDs."""
    legacy_entities = [
        MockRegistryEntry("sensor.foxess_battery_soc", "sensor", "foxess_modbus"),
        MockRegistryEntry("sensor.foxess_pv_power", "sensor", "foxess_modbus"),
        MockRegistryEntry("sensor.foxess_pv1_power", "sensor", "foxess_modbus"),
        MockRegistryEntry("sensor.foxess_pv2_power", "sensor", "foxess_modbus"),
        MockRegistryEntry("sensor.foxess_feed_in_power", "sensor", "foxess_modbus"),
        MockRegistryEntry("sensor.foxess_load_power", "sensor", "foxess_modbus"),
        MockRegistryEntry("sensor.foxess_grid_consumption_energy", "sensor", "foxess_modbus"),
        MockRegistryEntry("sensor.foxess_feed_in_energy", "sensor", "foxess_modbus"),
        MockRegistryEntry("sensor.foxess_charge_energy", "sensor", "foxess_modbus"),
        MockRegistryEntry("sensor.foxess_discharge_energy", "sensor", "foxess_modbus"),
        MockRegistryEntry("select.foxess_work_mode", "select", "foxess_modbus"),
        MockRegistryEntry("number.foxess_min_soc", "number", "foxess_modbus"),
        MockRegistryEntry("sensor.unrelated_temp", "sensor", "other_domain"),
    ]
    reg = MockEntityRegistry(legacy_entities)
    matches = find_smart_matches(reg)

    assert matches["battery_soc"][1] == "sensor.foxess_battery_soc"
    assert matches["pv_power_total"][1] == "sensor.foxess_pv_power"
    assert matches["pv1_power"][1] == "sensor.foxess_pv1_power"
    assert matches["pv2_power"][1] == "sensor.foxess_pv2_power"
    assert matches["grid_ct_meter_power"][1] == "sensor.foxess_feed_in_power"
    assert matches["house_load_power"][1] == "sensor.foxess_load_power"
    assert matches["grid_import_energy_total"][1] == "sensor.foxess_grid_consumption_energy"
    assert matches["grid_export_energy_total"][1] == "sensor.foxess_feed_in_energy"
    assert matches["battery_charge_energy_total"][1] == "sensor.foxess_charge_energy"
    assert matches["battery_discharge_energy_total"][1] == "sensor.foxess_discharge_energy"
    assert matches["work_mode"][1] == "select.foxess_work_mode"
    assert matches["min_soc"][1] == "number.foxess_min_soc"


def test_entities_adopt_suggested_object_id():
    """Verify entities accept and set suggested_object_id."""
    coordinator = MagicMock()
    coordinator.device_info = {}
    device = MagicMock()
    serial = "KH10_TEST"

    # Sensor entity with mapping
    desc = BASE_SENSOR_DESCRIPTIONS[0]  # pv_power_total
    sensor_mapped = FoxessSensorEntity(
        coordinator,
        desc,
        device,
        serial,
        suggested_object_id="foxess_pv_power",
    )
    assert getattr(sensor_mapped, "_attr_suggested_object_id", None) == "foxess_pv_power"

    # Sensor entity without mapping
    sensor_unmapped = FoxessSensorEntity(
        coordinator,
        desc,
        device,
        serial,
        suggested_object_id=None,
    )
    assert getattr(sensor_unmapped, "_attr_suggested_object_id", None) is None

    # Energy sensor with mapping
    energy_sensor = FoxessEnergySensor(
        coordinator=coordinator,
        key="grid_import_energy_total",
        name="Grid Import Energy Total",
        power_fn=lambda dev: 100.0,
        device=device,
        serial=serial,
        suggested_object_id="foxess_grid_consumption_energy",
    )
    assert getattr(energy_sensor, "_attr_suggested_object_id", None) == "foxess_grid_consumption_energy"

    # Select entity with mapping
    select_entity = FoxessWorkModeSelect(
        coordinator,
        device,
        serial,
        suggested_object_id="foxess_work_mode",
    )
    assert getattr(select_entity, "_attr_suggested_object_id", None) == "foxess_work_mode"

    # Number entity with mapping
    number_entity = FoxessMinSocNumber(
        coordinator,
        device,
        serial,
        suggested_object_id="foxess_min_soc",
    )
    assert getattr(number_entity, "_attr_suggested_object_id", None) == "foxess_min_soc"
