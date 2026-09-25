"""FoxESS H1 Inverter Device."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from modbus_connection.model import Raw
from ..const import WorkMode
from ..model import FoxessDevice, UpdateReport
from .battery import FoxessH1Battery
from .control import FoxessH1Control
from .grid import FoxessH1Grid
from .inverter import FoxessH1InverterState
from .pv import FoxessH1PV

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit


class FoxessH1Inverter(FoxessDevice):
    """FoxESS H1 / AC1 Hybrid Inverter reached through a ModbusUnit.

    Provides high-level async methods for telemetry polling and inverter control.
    """

    def __init__(
        self,
        unit: ModbusUnit,
        *,
        serial_number: str | None = None,
        model: str = "H1",
    ) -> None:
        """Initialize inverter components."""
        super().__init__(unit)
        self.serial_number = serial_number
        self.model = model

        # Sub-system components
        self.pv = FoxessH1PV(unit)
        self.battery = FoxessH1Battery(unit)
        self.grid = FoxessH1Grid(unit)
        self.inverter = FoxessH1InverterState(unit)
        self.control = FoxessH1Control(unit)

        self._readings: tuple[str, ...] = ("pv", "battery", "grid", "inverter")
        self._settings: tuple[str, ...] = ("control",)

    async def _async_setup(self) -> None:
        """Perform initial setup or validation if needed."""
        pass

    async def async_update_readings(self) -> UpdateReport:
        """Poll fast telemetry: PV generation, battery status, grid flow, and inverter state."""
        await self.async_ensure_setup()
        return await self.async_poll(self._readings)

    async def async_update_settings(self) -> UpdateReport:
        """Poll slower configuration registers: work modes, SOC limits, and power parameters."""
        await self.async_ensure_setup()
        return await self.async_poll(self._settings)

    async def async_update(self) -> UpdateReport:
        """Refresh all readings and settings in a single poll."""
        await self.async_ensure_setup()
        return await self.async_poll([*self._readings, *self._settings])

    async def async_read_raw(self, names: Iterable[str] | None = None) -> Raw:
        """Read sub-system registers undecoded for diagnostics."""
        target = [*self._readings, *self._settings] if names is None else names
        return await super().async_read_raw(target)

    async def async_set_work_mode(self, mode: WorkMode | int) -> None:
        """Set the inverter work mode (Self Use, Feed-in First, Back-up)."""
        val = int(mode)
        await self.control.write("raw_work_mode", val)

    async def async_set_min_soc(self, min_soc: int) -> None:
        """Set the minimum battery state-of-charge percentage."""
        if not 10 <= min_soc <= 100:
            raise ValueError(f"Min SOC must be between 10 and 100, got {min_soc}")
        await self.control.write("min_soc", min_soc)

    async def async_set_force_charge(
        self,
        power_w: int,
        max_soc: int = 100,
        timeout_sec: int = 3600,
    ) -> None:
        """Command the inverter to force charge the battery at a target power (W)."""
        power_w = abs(power_w)
        await self.control.write("max_soc", max_soc)
        await self.control.write("remote_timeout", timeout_sec)
        await self.control.write("remote_active_power", -power_w)
        await self.control.write("remote_enable", 1)

    async def async_set_force_discharge(
        self,
        power_w: int,
        min_soc: int = 10,
        timeout_sec: int = 3600,
    ) -> None:
        """Command the inverter to force export from the battery at a target power (W)."""
        power_w = abs(power_w)
        await self.control.write("min_soc", min_soc)
        await self.control.write("remote_timeout", timeout_sec)
        await self.control.write("remote_active_power", power_w)
        await self.control.write("remote_enable", 1)

    async def async_clear_overrides(self) -> None:
        """Cancel remote active power override and revert to standard Self-Use operation."""
        await self.control.write("remote_enable", 0)
        await self.control.write("raw_work_mode", int(WorkMode.SELF_USE))
