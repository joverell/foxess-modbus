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
MODEL_AUTO_DETECT: Final = "Auto-detect (Recommended)"

CONF_MIGRATE: Final = "migrate_legacy"
CONF_MAPPINGS: Final = "sensor_mappings"
LEGACY_DOMAIN: Final = "foxess_modbus"

DEFAULT_CREATE_NEW: Final = "(Default - Create New)"


def get_migratable_keys_for_model(
    model: str | None = None,
) -> tuple[tuple[str, str, str], ...]:
    """Return the tuple of migratable keys dynamic to the inverter model."""
    keys: list[tuple[str, str, str]] = [
        ("battery_soc", "Battery SoC", "sensor"),
        ("pv_power_total", "PV Power Total", "sensor"),
        ("pv1_power", "PV1 Power", "sensor"),
        ("pv2_power", "PV2 Power", "sensor"),
    ]

    model_upper = (model or "").upper()
    if "KH" in model_upper:
        # KH Series has 4 MPPT strings
        keys.extend(
            [
                ("pv3_power", "PV3 Power", "sensor"),
                ("pv4_power", "PV4 Power", "sensor"),
            ]
        )
    elif "H3-PRO" in model_upper or "H3_PRO" in model_upper or "15KW" in model_upper or "30KW" in model_upper:
        # H3-Pro Series has 6 MPPT strings
        keys.extend(
            [
                ("pv3_power", "PV3 Power", "sensor"),
                ("pv4_power", "PV4 Power", "sensor"),
                ("pv5_power", "PV5 Power", "sensor"),
                ("pv6_power", "PV6 Power", "sensor"),
            ]
        )

    keys.extend(
        [
            ("grid_ct_meter_power", "Grid CT Meter Power", "sensor"),
            ("house_load_power", "House Load Power", "sensor"),
            ("grid_import_energy_total", "Grid Import Energy Total", "sensor"),
            ("grid_export_energy_total", "Grid Export Energy Total", "sensor"),
            ("battery_charge_energy_total", "Battery Charge Energy Total", "sensor"),
            ("battery_discharge_energy_total", "Battery Discharge Energy Total", "sensor"),
            ("work_mode", "Work Mode", "select"),
            ("min_soc", "Min SoC", "number"),
        ]
    )

    return tuple(keys)


MIGRATABLE_KEYS: Final = get_migratable_keys_for_model("KH")

SCAN_INTERVAL: Final = 15
DEFAULT_SCAN_INTERVAL: Final = 15
CONF_SCAN_INTERVAL: Final = "scan_interval"
ALLOWED_SCAN_INTERVALS: Final = (5, 10, 15, 30, 60)
SETTINGS_SCAN_INTERVAL: Final = 60
