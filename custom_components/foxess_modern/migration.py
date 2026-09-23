"""Migration helpers for seamless adoption of legacy foxess_modbus entities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_HOST, CONF_MAPPINGS, CONF_PORT, CONF_UNIT_ID, DOMAIN, LEGACY_DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

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
    "battery_charge_power": ["battery_charge", "battery_charge_2"],
    "battery_discharge_power": ["battery_discharge", "battery_discharge_2"],
    "grid_ct_meter_power": ["feed_in_power", "feed_in", "feed_in_2", "grid_ct", "grid_power", "meter_power", "ct_power"],
    "grid_import_power": ["grid_consumption", "grid_consumption_2"],
    "grid_export_power": ["feed_in_power", "feed_in", "feed_in_2"],
    "house_load_power": ["load_power", "load_power_2", "house_load", "consumption_power"],
    "pv_power_total": ["pv_power_now", "pv_power"],
    "grid_import_energy_total": [
        "grid_consumption_energy_total",
        "grid_consumption_energy_total_2",
        "grid_consumption_energy",
        "import_energy_total",
        "import_energy",
    ],
    "grid_import_energy_today": ["grid_consumption_energy_today"],
    "grid_export_energy_total": [
        "feed_in_energy_total",
        "feed_in_energy_total_2",
        "feed_in_energy",
        "export_energy_total",
        "export_energy",
    ],
    "grid_export_energy_today": ["feed_in_energy_today"],
    "battery_charge_energy_total": [
        "battery_charge_total",
        "battery_charge_total_2",
        "charge_energy_total",
        "charge_energy",
        "battery_charge",
    ],
    "battery_charge_energy_today": ["battery_charge_today"],
    "battery_discharge_energy_total": [
        "battery_discharge_total",
        "battery_discharge_total_2",
        "discharge_energy_total",
        "discharge_energy",
        "battery_discharge",
    ],
    "battery_discharge_energy_today": ["battery_discharge_today"],
    "house_load_energy_total": ["load_power_total", "load_energy_total"],
    "load_energy_total": ["load_power_total", "load_energy_total"],
    "house_load_energy_today": ["load_energy_today"],
    "load_energy_today": ["load_energy_today"],
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
    "inverter_state": ["inverter_state", "inverter_state_2"],
    "work_mode": ["work_mode", "work_mode_2"],
    "min_soc": ["min_soc"],
    "max_soc": ["max_soc"],
    "min_soc_on_grid": ["min_soc_on_grid"],
    "max_charge_current": ["max_charge_current"],
    "max_discharge_current": ["max_discharge_current"],
    "export_power_limit": ["export_power_limit"],
    "import_power_limit": ["import_power_limit"],
    "master_version": ["master_version"],
    "slave_version": ["slave_version"],
    "manager_version": ["manager_version"],
    "pv_energy_total": ["solar_energy_total", "solar_energy_total_2"],
    "force_charge_power": ["force_charge_power"],
    "force_discharge_power": ["force_discharge_power"],
}


def resolve_clean_entity_id(
    entity_reg: er.EntityRegistry,
    key: str,
    domain: str,
    explicit_mapped_id: str | None = None,
    fallback: bool = True,
) -> str | None:
    """Resolve the clean legacy or default entity ID for a given key."""
    if explicit_mapped_id and explicit_mapped_id != "(Default - Create New)":
        return explicit_mapped_id

    candidate_keys = [key] + LEGACY_KEY_ALIASES.get(key, [])
    candidate_uids = {f"foxess_modbus_{k}" for k in candidate_keys}

    # 1. Check active entities in entity registry
    for entity in entity_reg.entities.values():
        if getattr(entity, "platform", None) == LEGACY_DOMAIN and getattr(entity, "domain", None) == domain:
            uid = getattr(entity, "unique_id", None)
            eid = getattr(entity, "entity_id", "")
            if (uid and uid in candidate_uids) or any(
                eid.endswith(f"_{k}") or eid.endswith(f".{k}") or f"_{k}" in eid or k in eid for k in candidate_keys
            ):
                return eid

    # 2. Check deleted entities in entity registry
    if hasattr(entity_reg, "deleted_entities") and entity_reg.deleted_entities:
        for deleted_entity in entity_reg.deleted_entities.values():
            if getattr(deleted_entity, "platform", None) == LEGACY_DOMAIN:
                uid = getattr(deleted_entity, "unique_id", None)
                eid = getattr(deleted_entity, "entity_id", "")
                if (uid and uid in candidate_uids) or any(
                    eid.endswith(f"_{k}") or eid.endswith(f".{k}") or f"_{k}" in eid or k in eid for k in candidate_keys
                ):
                    return eid

    # Fallback to standard clean entity ID if fallback is True, else None
    return f"{domain}.{key}" if fallback else None


def adopt_legacy_entity_id(
    entity_reg: er.EntityRegistry,
    key: str,
    domain: str,
    serial: str | None = None,
    explicit_mapped_id: str | None = None,
) -> str:
    """Find and adopt an extant legacy entity ID for the given key."""
    target_entity_id = resolve_clean_entity_id(
        entity_reg,
        key=key,
        domain=domain,
        explicit_mapped_id=explicit_mapped_id,
    )

    # If the target entity ID is held by legacy foxess_modbus in active entities, release it
    if old_entry := entity_reg.async_get(target_entity_id):
        if old_entry.platform == LEGACY_DOMAIN:
            _LOGGER.info(
                "Releasing legacy entity %s (%s) from foxess_modbus",
                target_entity_id,
                key,
            )
            entity_reg.async_remove(target_entity_id)

    # If the target entity ID is in deleted_entities, purge it so Home Assistant allows adoption
    if hasattr(entity_reg, "deleted_entities") and entity_reg.deleted_entities:
        for del_key, del_entry in list(entity_reg.deleted_entities.items()):
            if getattr(del_entry, "entity_id", None) == target_entity_id:
                entity_reg.deleted_entities.pop(del_key, None)

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


async def async_migrate_entity_registry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate all modern entities in the registry to clean 1:1 legacy entity IDs."""
    entity_reg = er.async_get(hass)
    serial = str(
        entry.unique_id
        or f"{entry.data.get(CONF_HOST)}_{entry.data.get(CONF_PORT)}_{entry.data.get(CONF_UNIT_ID)}"
    )
    mappings: dict[str, str] = entry.options.get(
        CONF_MAPPINGS, entry.data.get(CONF_MAPPINGS, {})
    )

    modern_entries = er.async_entries_for_config_entry(entity_reg, entry.entry_id)
    for ent in modern_entries:
        key = ent.unique_id.replace(f"{serial}_", "")
        target_id = resolve_clean_entity_id(
            entity_reg,
            key=key,
            domain=ent.domain,
            explicit_mapped_id=mappings.get(key),
        )

        if ent.entity_id != target_id:
            # Release any active conflicting entity from foxess_modbus
            if old_active := entity_reg.async_get(target_id):
                if old_active.platform == LEGACY_DOMAIN or old_active.config_entry_id != entry.entry_id:
                    _LOGGER.info("Removing conflicting active entity %s", target_id)
                    entity_reg.async_remove(target_id)

            # Purge from deleted_entities so HA allows rename without collisions
            if hasattr(entity_reg, "deleted_entities") and entity_reg.deleted_entities:
                for del_key, del_entry in list(entity_reg.deleted_entities.items()):
                    if getattr(del_entry, "entity_id", None) == target_id:
                        _LOGGER.info("Purging %s from deleted_entities to allow adoption", target_id)
                        entity_reg.deleted_entities.pop(del_key, None)

            _LOGGER.info("Migrating entity %s -> %s", ent.entity_id, target_id)
            try:
                entity_reg.async_update_entity(ent.entity_id, new_entity_id=target_id)
            except Exception as err:
                _LOGGER.warning("Could not rename %s to %s: %s", ent.entity_id, target_id, err)
