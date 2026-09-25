"""DataUpdateCoordinator for FoxESS Modern."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError, ModbusTimeoutError
from .device.model import UpdateReport

from .const import DOMAIN

if TYPE_CHECKING:
    from .device.kh10.device import FoxessKH10Inverter

_LOGGER = logging.getLogger(__name__)


class FoxessDataUpdateCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Coordinates polling of FoxESS inverter telemetry using UpdateReport."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device: FoxessKH10Inverter | Any,
        update_method: Callable[[], Any],
        update_interval: timedelta,
        is_fast_poll: bool = False,
        bus_lock: asyncio.Lock | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.unique_id}",
            update_interval=update_interval,
        )
        self.entry = entry
        self.device = device
        self._update_method = update_method
        self._is_fast_poll = is_fast_poll
        self._bus_lock = bus_lock
        self._timeouts = 0
        self._failed_subsystems: frozenset[str] = frozenset()

    @property
    def timeouts(self) -> int:
        """Return consecutive timeout count."""
        return self._timeouts

    @property
    def is_available(self) -> bool:
        """Return True if coordinator successfully updated data or within transient tolerance."""
        if self._timeouts < 2 and self.data is not None:
            # Tolerate transient poll timeouts on Wi-Fi without flapping entity availability
            return True
        return self.last_update_success

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for device registry."""
        model_name = getattr(self.device, "model", "Inverter")
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.entry.unique_id))},
            manufacturer="FoxESS",
            model=model_name,
            name=f"FoxESS {model_name}",
        )

    async def _async_update_data(self) -> UpdateReport:
        """Fetch the latest data from the inverter, serialized via bus_lock."""
        bus_lock = self._bus_lock or getattr(getattr(self.device, "modbus_unit", None), "bus_lock", None)
        if bus_lock is not None:
            async with bus_lock:
                return await self._do_update_data()
        return await self._do_update_data()

    async def _do_update_data(self) -> UpdateReport:
        """Execute update method and handle errors."""
        try:
            report: UpdateReport = await self._update_method()
        except ModbusTimeoutError as err:
            self._timeouts += 1
            unit = getattr(self.device, "modbus_unit", None)
            if unit and hasattr(unit, "set_message_spacing"):
                # Back off pacing to 400ms to allow saturated transceiver buffers to clear
                unit.set_message_spacing(0.40)
            if self._timeouts >= 3:
                # Serial-to-network bridge wedged, recycle link
                if unit and hasattr(unit, "disconnect"):
                    _LOGGER.warning(
                        "Link unresponsive after %d consecutive timeouts: recycling Modbus connection",
                        self._timeouts,
                    )
                    await unit.disconnect()
            raise UpdateFailed(str(err)) from err
        except ModbusError as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error communicating with FoxESS: {err}") from err

        if self._timeouts > 0:
            unit = getattr(self.device, "modbus_unit", None)
            if unit and hasattr(unit, "set_message_spacing"):
                # Restore nominal 250ms pacing upon successful communication
                unit.set_message_spacing(0.25)
        self._timeouts = 0

        if not report.updated:
            errors = list(report.failed.values())
            raise UpdateFailed(
                f"no sub-system answered: {errors[0] if errors else 'unknown'}"
            )

        # Log newly failing sub-systems
        newly_failed = sorted(report.failed.keys() - self._failed_subsystems)
        if newly_failed:
            _LOGGER.warning(
                "Sub-systems temporarily unavailable on this cycle: %s",
                newly_failed,
            )
        self._failed_subsystems = frozenset(report.failed)

        return report
