"""Migration helpers for seamless adoption of legacy foxess_modbus entities."""

from __future__ import annotations

import logging

from homeassistant.helpers import entity_registry as er

from .const import LEGACY_DOMAIN

_LOGGER = logging.getLogger(__name__)

LEGACY_KEY_ALIASES: dict[str, list[str]] = {
    "ambient_temperature": ["ambtemp"],
    "inverter_temperature": ["invtemp"],
    "grid_voltage": ["rvolt"],
    "grid_current": ["rcurrent"],
    "grid_power": ["rpower"],
    "grid_frequency": ["rfreq"],
    "battery_temperature": ["battery_temp"],
    "bms_cell_voltage_high": ["bms_cell_mv_high"],
    "bms_cell_voltage_low": ["bms_cell_mv_low"],
    "bms_cell_temp_high": ["bms_cell_temp_high"],
    "bms_cell_temp_low": ["bms_cell_temp_low"],
    "bms_charge_rate": ["bms_charge_rate"],
    "bms_discharge_rate": ["bms_discharge_rate"],
    "bms_kwh_remaining": ["bms_kwh_remaining"],
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
    "grid_ct_meter_power": ["feed_in", "grid_ct"],
    "grid_import_power": ["grid_consumption"],
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
    "pv1_energy_total": ["pv1_energy_total"],
    "pv2_energy_total": ["pv2_energy_total"],
    "pv3_energy_total": ["pv3_energy_total"],
    "pv4_energy_total": ["pv4_energy_total"],
    "inverter_fault_code": ["inverter_fault_code"],
    "inverter_state": ["inverter_state"],
    "work_mode": ["work_mode"],
    "min_soc": ["min_soc"],
}


def adopt_legacy_entity_id(
    entity_reg: er.EntityRegistry,
    key: str,
    domain: str,
    explicit_mapped_id: str | None = None,
) -> str | None:
    """Find and adopt an extant legacy entity ID for the given key.

    If found and owned by foxess_modbus, releases the legacy entity from the registry
    so the modern entity can adopt the exact entity_id without any '_2' suffix.
    Returns the suggested object_id (e.g. 'ambtemp' for 'sensor.ambtemp'), or None.
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
        return target_entity_id.split(".", 1)[-1]

    return None
