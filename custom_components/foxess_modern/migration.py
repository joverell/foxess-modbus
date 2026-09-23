"""Migration helpers for seamless adoption of legacy foxess_modbus entities."""

from __future__ import annotations

import logging

from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, LEGACY_DOMAIN

_LOGGER = logging.getLogger(__name__)

LEGACY_KEY_ALIASES: dict[str, list[str]] = {
    "ambient_temperature": ["ambtemp"],
    "inverter_temperature": ["invtemp"],
    "grid_voltage": ["rvolt"],
    "grid_current": ["rcurrent"],
    "grid_power": ["rpower"],
    "grid_frequency": ["rfreq"],
    "battery_temperature": ["battery_temp"],
    "battery_soh": ["battery_soh"],
    "bms_cell_mv_high": ["bms_cell_mv_high"],
    "bms_cell_mv_low": ["bms_cell_mv_low"],
    "bms_cell_temp_high": ["bms_cell_temp_high"],
    "bms_cell_temp_low": ["bms_cell_temp_low"],
    "bms_charge_rate": ["bms_charge_rate"],
    "bms_discharge_rate": ["bms_discharge_rate"],
    "bms_kwh_remaining": ["bms_kwh_remaining"],
    "connection_status": ["connection_status"],
    "ct2_power": ["ct2_meter"],
    "eps_voltage": ["eps_rvolt"],
    "eps_current": ["eps_rcurrent"],
    "eps_power": ["eps_rpower"],
    "eps_frequency": ["eps_frequency"],
    "battery_power": ["invbatpower"],
    "battery_voltage": ["invbatvolt"],
    "battery_current": ["invbatcurrent"],
    "battery_charge_power": ["battery_charge"],
    "battery_discharge_power": ["battery_discharge"],
    "grid_ct_meter_power": ["feed_in", "feed_in_2", "grid_ct"],
    "grid_import_power": ["grid_consumption"],
    "grid_export_power": ["feed_in", "feed_in_2"],
    "house_load_power": ["load_power"],
    "pv_power_total": ["pv_power_now", "pv_power"],
    "grid_import_energy_total": ["grid_consumption_energy_total"],
    "grid_import_energy_today": ["grid_consumption_energy_today"],
    "grid_export_energy_total": ["feed_in_energy_total"],
    "grid_export_energy_today": ["feed_in_energy_today"],
    "battery_charge_energy_total": ["battery_charge_total"],
    "battery_charge_energy_today": ["battery_charge_today"],
    "battery_discharge_energy_total": ["battery_discharge_total"],
    "battery_discharge_energy_today": ["battery_discharge_today"],
    "house_load_energy_total": ["load_power_total"],
    "house_load_energy_today": ["load_energy_today"],
    "solar_energy_total": ["solar_energy_total"],
    "solar_energy_today": ["solar_energy_today"],
    "total_yield_total": ["total_yield_total"],
    "total_yield_today": ["total_yield_today"],
    "input_energy_total": ["input_energy_total", "input_energy_total_2"],
    "input_energy_today": ["input_energy_today"],
    "pv1_energy_total": ["pv1_energy_total", "pv1_energy_total_2"],
    "pv2_energy_total": ["pv2_energy_total", "pv2_energy_total_2"],
    "pv3_energy_total": ["pv3_energy_total"],
    "pv4_energy_total": ["pv4_energy_total"],
    "inverter_fault_code": ["inverter_fault_code"],
    "inverter_state": ["inverter_state"],
    "work_mode": ["work_mode"],
    "min_soc": ["min_soc"],
    "max_soc": ["max_soc"],
    "min_soc_on_grid": ["min_soc_on_grid"],
    "max_charge_current": ["max_charge_current"],
    "max_discharge_current": ["max_discharge_current"],
    "export_power_limit": ["export_power_limit"],
    "import_power_limit": ["import_power_limit"],
}


def adopt_legacy_entity_id(
    entity_reg: er.EntityRegistry,
    key: str,
    domain: str,
    serial: str | None = None,
    explicit_mapped_id: str | None = None,
) -> str:
    """Find and adopt an extant legacy entity ID for the given key.

    1. Checks if explicit_mapped_id is supplied.
    2. If not, checks candidate unique_ids in entity_registry for foxess_modbus.
    3. If found and owned by foxess_modbus, releases the legacy entity from the registry.
    4. If an old verbose modern entry exists for this unique_id, releases it so the clean ID is used.
    5. Returns the full target entity_id (e.g. 'sensor.feed_in_2' or 'sensor.solar_energy_total').
    """
    target_entity_id = explicit_mapped_id

    if not target_entity_id:
        candidate_keys = [key] + LEGACY_KEY_ALIASES.get(key, [])
        candidate_uids = [f"foxess_modbus_{k}" for k in candidate_keys]

        for entity in entity_reg.entities.values():
            if entity.platform == LEGACY_DOMAIN and entity.domain == domain:
                if entity.unique_id in candidate_uids:
                    target_entity_id = entity.entity_id
                    break

    if target_entity_id:
        if old_entry := entity_reg.async_get(target_entity_id):
            if old_entry.platform == LEGACY_DOMAIN:
                _LOGGER.info(
                    "Migrating legacy entity %s (%s) to modern integration",
                    target_entity_id,
                    key,
                )
                entity_reg.async_remove(target_entity_id)

    # Fallback for fresh installs or unmapped keys: clean standard entity_id
    if not target_entity_id:
        target_entity_id = f"{domain}.{key}"

    # Clean up any prior verbose entity entry registered by previous test runs of foxess_modern
    if serial:
        modern_uid = f"{serial}_{key}"
        for entity in list(entity_reg.entities.values()):
            if entity.platform == DOMAIN and entity.unique_id == modern_uid:
                if entity.entity_id != target_entity_id:
                    _LOGGER.info(
                        "Cleaning up verbose entity %s for clean %s",
                        entity.entity_id,
                        target_entity_id,
                    )
                    entity_reg.async_remove(entity.entity_id)
                break

    return target_entity_id
