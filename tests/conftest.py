"""Pytest configuration and Home Assistant test fixtures."""

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
    mock_vol.Coerce = lambda t: t
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
    "homeassistant.helpers.config_validation",
    "homeassistant.components",
    "homeassistant.components.modbus",
    "homeassistant.components.sensor",
    "homeassistant.components.select",
    "homeassistant.components.number",
    "homeassistant.components.diagnostics",
]

for name in ha_modules:
    if name not in sys.modules:
        mod = types.ModuleType(name)
        mod.__path__ = []
        sys.modules[name] = mod

# Mock config_validation
cv_mod = sys.modules["homeassistant.helpers.config_validation"]
cv_mod.config_entry_only_config_schema = lambda domain: lambda config: config
cv_mod.empty_config_schema = lambda domain: lambda config: config
sys.modules["homeassistant.helpers"].config_validation = cv_mod


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


class MockRestoreNumber(MockNumberEntity):
    pass


class MockCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def __class_getitem__(cls, item):
        return cls


class MockDataUpdateCoordinator:
    def __init__(self, *args, **kwargs):
        self.last_update_success = True

    def __class_getitem__(cls, item):
        return cls


def mock_callback(fn):
    return fn


class MockServiceCall:
    def __init__(self, domain, service, data=None):
        self.domain = domain
        self.service = service
        self.data = data or {}


class MockEntityCategory:
    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


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


class MockNumberDeviceClass:
    BATTERY = "battery"
    POWER = "power"
    CURRENT = "current"


class MockSensorDeviceClass:
    POWER = "power"
    VOLTAGE = "voltage"
    CURRENT = "current"
    ENERGY = "energy"
    BATTERY = "battery"
    TEMPERATURE = "temperature"
    FREQUENCY = "frequency"
    ENUM = "enum"
    REACTIVE_POWER = "reactive_power"


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
    entity_category: Any = None
    icon: str | None = None


sys.modules["homeassistant.exceptions"].HomeAssistantError = MockHomeAssistantError
sys.modules["homeassistant.exceptions"].ConfigEntryNotReady = MockConfigEntryNotReady
sys.modules["homeassistant.config_entries"].ConfigFlow = MockConfigFlow
sys.modules["homeassistant.config_entries"].OptionsFlow = MockOptionsFlow
sys.modules["homeassistant.config_entries"].ConfigEntry = MagicMock
sys.modules["homeassistant.config_entries"].ConfigFlowResult = MagicMock

sys.modules["homeassistant.components.sensor"].SensorEntity = MockSensorEntity
sys.modules["homeassistant.components.sensor"].RestoreSensor = MockRestoreSensor
sys.modules["homeassistant.components.sensor"].SensorEntityDescription = MockSensorEntityDescription
sys.modules["homeassistant.components.sensor"].SensorDeviceClass = MockSensorDeviceClass
sys.modules["homeassistant.components.sensor"].SensorStateClass = MockSensorStateClass
sys.modules["homeassistant.components.select"].SelectEntity = MockSelectEntity
sys.modules["homeassistant.components.number"].NumberEntity = MockNumberEntity
sys.modules["homeassistant.components.number"].RestoreNumber = MockRestoreNumber
sys.modules["homeassistant.components.number"].NumberDeviceClass = MockNumberDeviceClass
sys.modules["homeassistant.components.number"].NumberMode = MockNumberMode
sys.modules["homeassistant.components.modbus"].async_get_unit = MagicMock()
sys.modules["homeassistant.components.modbus"].async_get_temporary_unit = MagicMock()
sys.modules["homeassistant.components.diagnostics"].async_redact_data = lambda data, to_redact: data
sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = MockCoordinatorEntity
sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = MockDataUpdateCoordinator
sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = MockUpdateFailed
sys.modules["homeassistant.helpers.device_registry"].DeviceInfo = MagicMock
sys.modules["homeassistant.helpers.entity_platform"].AddConfigEntryEntitiesCallback = MagicMock

sys.modules["homeassistant.core"].callback = mock_callback
sys.modules["homeassistant.core"].HomeAssistant = MagicMock
sys.modules["homeassistant.core"].ServiceCall = MockServiceCall

sys.modules["homeassistant.const"].EntityCategory = MockEntityCategory
sys.modules["homeassistant.const"].Platform = MockPlatform
sys.modules["homeassistant.const"].UnitOfPower = MockUnitOfPower
sys.modules["homeassistant.const"].UnitOfEnergy = MockUnitOfEnergy
sys.modules["homeassistant.const"].UnitOfElectricCurrent = MockUnitOfElectricCurrent
sys.modules["homeassistant.const"].UnitOfElectricPotential = MockUnitOfElectricPotential
sys.modules["homeassistant.const"].UnitOfFrequency = MockUnitOfFrequency
sys.modules["homeassistant.const"].UnitOfTemperature = MockUnitOfTemperature
