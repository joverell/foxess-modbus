"""Config flow for FoxESS Modern integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import (
    ALLOWED_SCAN_INTERVALS,
    CONF_HOST,
    CONF_MAPPINGS,
    CONF_MIGRATE,
    CONF_MODEL,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_CREATE_NEW,
    DEFAULT_MODEL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DOMAIN,
    LEGACY_DOMAIN,
    MIGRATABLE_KEYS,
    MODEL_AUTO_DETECT,
    get_migratable_keys_for_model,
)
from .connection import ResilientModbusUnit
from .device import create_inverter
from .device.identify import async_detect_inverter

_LOGGER = logging.getLogger(__name__)

SUPPORTED_MODELS: list[str] = [
    MODEL_AUTO_DETECT,
    "KH Series (KH7 - KH10.5)",
    "H3 Series (H3 / H3 Smart / AC3)",
    "H3-Pro Series (15kW - 30kW)",
    "H1 / AC1 Series",
]


def find_smart_matches(
    entity_reg: er.EntityRegistry,
    keys: tuple[tuple[str, str, str], ...] | None = None,
) -> dict[str, tuple[list[str], str]]:
    """Find candidate entities and smart matches for migratable keys."""
    from .migration import resolve_clean_entity_id

    results: dict[str, tuple[list[str], str]] = {}
    target_keys = keys if keys is not None else MIGRATABLE_KEYS

    # Collect legacy entities from both active entities and deleted_entities
    legacy_entities: list[Any] = [
        entity
        for entity in entity_reg.entities.values()
        if entity.platform == LEGACY_DOMAIN
    ]
    if hasattr(entity_reg, "deleted_entities") and entity_reg.deleted_entities:
        legacy_entities.extend([
            del_ent
            for del_ent in entity_reg.deleted_entities.values()
            if getattr(del_ent, "platform", None) == LEGACY_DOMAIN
        ])

    for key, _label, platform in target_keys:
        candidates = [
            entity.entity_id
            for entity in legacy_entities
            if getattr(entity, "domain", None) == platform
            and not any(x in entity.entity_id for x in ["foxess_kh_", "192_168_86_162"])
        ]
        if not candidates:
            candidates = [
                entity.entity_id
                for entity in entity_reg.entities.values()
                if entity.domain == platform
                and entity.platform not in (DOMAIN, "foxess_modern")
                and not any(x in entity.entity_id for x in ["foxess_kh_", "192_168_86_162"])
                and (
                    "foxess" in entity.entity_id.lower()
                    or key in entity.entity_id.lower()
                )
            ]
        candidates = sorted(set(candidates))

        smart_match = resolve_clean_entity_id(entity_reg, key, platform, fallback=False)

        options_list = [DEFAULT_CREATE_NEW]
        if smart_match:
            options_list.append(smart_match)

        for c in candidates:
            if c not in options_list:
                options_list.append(c)

        default_val = smart_match if smart_match else DEFAULT_CREATE_NEW
        results[key] = (options_list, default_val)

    return results


def _clean_host_and_port(data: dict[str, Any]) -> tuple[str, int]:
    """Clean host and port values from user input."""
    host = str(data[CONF_HOST]).strip()
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.rstrip("/")
    port = data.get(CONF_PORT, DEFAULT_PORT)
    if ":" in host:
        parts = host.split(":", 1)
        host = parts[0]
        if parts[1].isdigit():
            port = int(parts[1])
    return host, int(port)


async def validate_input(hass: Any, data: dict[str, Any]) -> dict[str, Any]:
    """Validate that the user input can connect to the inverter."""
    host, port = _clean_host_and_port(data)
    unit_id = data[CONF_UNIT_ID]
    model = data.get(CONF_MODEL, MODEL_AUTO_DETECT)

    unit = ResilientModbusUnit(host=host, port=port, unit_id=unit_id)
    try:
        # Detect inverter model and serial number over Modbus
        detected_model, detected_serial = await async_detect_inverter(unit)
        if model == MODEL_AUTO_DETECT or not model:
            model = detected_model
            data[CONF_MODEL] = detected_model
        if detected_serial:
            data["serial_number"] = detected_serial

        inverter = create_inverter(unit, serial_number=detected_serial, model=model)
        report = await inverter.async_update_readings()
        if not report.updated:
            raise CannotConnect("No registers answered on probe")
    except Exception as err:
        _LOGGER.error(
            "Cannot connect to FoxESS inverter at %s:%s (unit %s, model %s): %s",
            host,
            port,
            unit_id,
            model,
            err,
        )
        raise CannotConnect from err
    finally:
        await unit.close()

    serial_display = data.get("serial_number") or host
    return {"title": f"FoxESS {model} ({serial_display})"}


class FoxessModernConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FoxESS Modern."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_input: dict[str, Any] = {}
        self._title: str = ""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return FoxessModernOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            clean_host, clean_port = _clean_host_and_port(user_input)
            user_input[CONF_HOST] = clean_host
            user_input[CONF_PORT] = clean_port

            unique_id = f"{user_input[CONF_HOST]}_{user_input[CONF_PORT]}_{user_input[CONF_UNIT_ID]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        has_legacy = bool(self.hass.config_entries.async_entries(LEGACY_DOMAIN))
        user_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): int,
                vol.Required(CONF_MODEL, default=MODEL_AUTO_DETECT): vol.In(SUPPORTED_MODELS),
                vol.Optional(CONF_MIGRATE, default=has_legacy): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=user_schema,
            errors=errors,
        )

    async def async_step_migration_mapping(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle legacy sensor mapping step."""
        if user_input is not None:
            mappings = {
                k: v for k, v in user_input.items()
                if v and v != DEFAULT_CREATE_NEW
            }
            self._user_input[CONF_MAPPINGS] = mappings
            return self.async_create_entry(
                title=self._title,
                data=self._user_input,
            )

        model = self._user_input.get(CONF_MODEL, DEFAULT_MODEL)
        keys = get_migratable_keys_for_model(model)
        entity_reg = er.async_get(self.hass)
        matches = find_smart_matches(entity_reg, keys)

        schema_dict: dict[Any, Any] = {}
        for key, _label, _platform in keys:
            options, default_val = matches[key]
            schema_dict[vol.Optional(key, default=default_val)] = vol.In(options)

        return self.async_show_form(
            step_id="migration_mapping",
            data_schema=vol.Schema(schema_dict),
        )


class FoxessModernOptionsFlow(OptionsFlow):
    """Handle options flow for FoxESS Modern."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage FoxESS Modern options."""
        current_scan_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        if user_input is not None:
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, current_scan_interval)
            mappings = {
                k: v for k, v in user_input.items()
                if k != CONF_SCAN_INTERVAL and v and v != DEFAULT_CREATE_NEW
            }
            return self.async_create_entry(
                title="",
                data={CONF_MAPPINGS: mappings, CONF_SCAN_INTERVAL: scan_interval},
            )

        model = self._config_entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        keys = get_migratable_keys_for_model(model)
        entity_reg = er.async_get(self.hass)
        matches = find_smart_matches(entity_reg, keys)
        current_mappings = self._config_entry.options.get(
            CONF_MAPPINGS, self._config_entry.data.get(CONF_MAPPINGS, {})
        )

        schema_dict: dict[Any, Any] = {
            vol.Optional(CONF_SCAN_INTERVAL, default=current_scan_interval): vol.In(
                ALLOWED_SCAN_INTERVALS
            )
        }
        for key, _label, _platform in keys:
            options, smart_default = matches[key]
            current_val = current_mappings.get(key, smart_default)
            if current_val not in options:
                options = [current_val] + options
            schema_dict[vol.Optional(key, default=current_val)] = vol.In(options)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
