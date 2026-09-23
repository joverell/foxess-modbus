"""Constants for the FoxESS Modern integration."""

from typing import Final

DOMAIN: Final = "foxess_modern"

CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_UNIT_ID: Final = "unit_id"
CONF_MODEL: Final = "model"

DEFAULT_PORT: Final = 502
DEFAULT_UNIT_ID: Final = 247
DEFAULT_MODEL: Final = "KH Series (KH7 - KH10.5)"

CONF_MIGRATE: Final = "migrate_legacy"
CONF_MAPPINGS: Final = "sensor_mappings"
LEGACY_DOMAIN: Final = "foxess_modbus"

DEFAULT_CREATE_NEW: Final = "(Default - Create New)"

MIGRATABLE_KEYS: Final = (
    ("battery_soc", "Battery SoC", "sensor"),
    ("pv_power_total", "PV Power Total", "sensor"),
    ("pv1_power", "PV1 Power", "sensor"),
    ("pv2_power", "PV2 Power", "sensor"),
    ("grid_ct_meter_power", "Grid CT Meter Power", "sensor"),
    ("house_load_power", "House Load Power", "sensor"),
    ("grid_import_energy_total", "Grid Import Energy Total", "sensor"),
    ("grid_export_energy_total", "Grid Export Energy Total", "sensor"),
    ("battery_charge_energy_total", "Battery Charge Energy Total", "sensor"),
    ("battery_discharge_energy_total", "Battery Discharge Energy Total", "sensor"),
    ("work_mode", "Work Mode", "select"),
    ("min_soc", "Min SoC", "number"),
)

SCAN_INTERVAL: Final = 15
SETTINGS_SCAN_INTERVAL: Final = 60
