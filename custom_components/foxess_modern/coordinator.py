"""DataUpdateCoordinator for FoxESS Modern."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

if TYPE_CHECKING:
    from .device.kh10.device import FoxessKH10Inverter

_LOGGER = logging.getLogger(__name__)


class FoxessDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """Coordinates polling of FoxESS inverter telemetry."""

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
        self._is_available = True

    @property
    def is_available(self) -> bool:
        """Return True if inverter communication has not suffered extended outage."""
        return self._is_available

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for device registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.entry.unique_id))},
            manufacturer="FoxESS",
            model=self.device.model,
            name=f"FoxESS {self.device.model}",
        )

    async def _async_update_data(self) -> None:
        """Fetch the latest data from the inverter."""
        try:
            report = await self._update_method()
            if hasattr(report, "updated") and not report.updated and hasattr(report, "failed") and report.failed:
                raise RuntimeError(
                    f"All requested sub-systems failed to respond: {list(report.failed.keys())}"
                )
            self._consecutive_failures = 0
            self._is_available = True
            if hasattr(report, "failed") and report.failed:
                _LOGGER.debug(
                    "Partial read notice from FoxESS (transient sub-system retry scheduled): %s",
                    report.failed,
                )
        except Exception as err:
            self._consecutive_failures += 1
            if self._consecutive_failures < 5:
                _LOGGER.warning(
                    "Transient communication error with FoxESS (attempt %d/5): %s",
                    self._consecutive_failures,
                    err,
                )
                return
            self._is_available = False
            raise UpdateFailed(f"Error communicating with FoxESS: {err}") from err
