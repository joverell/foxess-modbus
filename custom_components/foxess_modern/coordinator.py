"""DataUpdateCoordinator for FoxESS Modern."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection.model import UpdateReport

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
        device: FoxessKH10Inverter,
        update_method: Callable[[], Any],
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.unique_id}",
            update_interval=update_interval,
        )
        self.entry = entry
        self.device = device
        self._update_method = update_method
        self._consecutive_failures = 0
        self._failed_subsystems: frozenset[str] = frozenset()

    @property
    def is_available(self) -> bool:
        """Return True if inverter communication has not suffered extended outage."""
        return self._consecutive_failures < 8

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for device registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.entry.unique_id))},
            manufacturer="FoxESS",
            model=self.device.model,
            name=f"FoxESS {self.device.model}",
        )

    async def _async_update_data(self) -> UpdateReport:
        """Fetch the latest data from the inverter."""
        try:
            report: UpdateReport = await self._update_method()
        except Exception as err:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 3:
                # Recycle the bridge connection if wedged
                unit = getattr(self.device, "_unit", None)
                if unit and hasattr(unit, "disconnect"):
                    try:
                        res = unit.disconnect()
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception:
                        pass

            if self._consecutive_failures < 8:
                _LOGGER.warning(
                    "Transient communication error with FoxESS (attempt %d/8): %s",
                    self._consecutive_failures,
                    err,
                )
                if hasattr(self, "data") and self.data is not None:
                    return self.data
                return UpdateReport()

            raise UpdateFailed(f"Sustained error communicating with FoxESS: {err}") from err

        if not report.updated and report.failed:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 3:
                unit = getattr(self.device, "_unit", None)
                if unit and hasattr(unit, "disconnect"):
                    try:
                        res = unit.disconnect()
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception:
                        pass

            if self._consecutive_failures < 8:
                _LOGGER.warning(
                    "FoxESS telemetry cycle dropped (attempt %d/8, holding prior states): %s",
                    self._consecutive_failures,
                    list(report.failed.keys()),
                )
                if hasattr(self, "data") and self.data is not None:
                    return self.data
                return report

            errors = list(report.failed.values())
            raise UpdateFailed(f"No sub-system answered: {errors[0] if errors else 'unknown'}")

        self._consecutive_failures = 0

        # Log newly failing sub-systems
        newly_failed = sorted(report.failed.keys() - self._failed_subsystems)
        if newly_failed:
            _LOGGER.debug(
                "Notice: Sub-systems temporarily unavailable on this cycle: %s",
                newly_failed,
            )
        self._failed_subsystems = frozenset(report.failed)

        return report
