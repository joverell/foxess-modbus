"""Config flow for FoxESS Modern integration."""

from __future__ import annotations

import logging
from typing import Any

from modbus_connection import ModbusTcpParams
import voluptuous as vol

from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_UNIT_ID,
    DEFAULT_MODEL,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
)
from .device import create_inverter

_LOGGER = logging.getLogger(__name__)

SUPPORTED_MODELS: list[str] = ["KH10", "H3-Pro", "H3", "H1"]

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): int,
        vol.Required(CONF_MODEL, default=DEFAULT_MODEL): vol.In(SUPPORTED_MODELS),
    }
)


async def validate_input(hass: Any, data: dict[str, Any]) -> dict[str, Any]:
    """Validate that the user input can connect to the inverter."""
    host = data[CONF_HOST]
    port = data[CONF_PORT]
    unit_id = data[CONF_UNIT_ID]
    model = data[CONF_MODEL]
    params = ModbusTcpParams(host=host, port=port)

    try:
        # Use Home Assistant's temporary connection broker to probe the device
        async with async_get_temporary_unit(hass, params, unit_id) as unit:
            inverter = create_inverter(unit, model=model)
            report = await inverter.async_update_readings()
            if not report.updated:
                raise CannotConnect("No registers answered on probe")
    except Exception as err:
        _LOGGER.error("Cannot connect to FoxESS inverter at %s:%s (unit %s, model %s): %s", host, port, unit_id, model, err)
        raise CannotConnect from err

    return {"title": f"FoxESS {model} ({host})"}


class FoxessModernConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FoxESS Modern."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check unique ID based on host + port + unit_id
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

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
