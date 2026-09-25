"""FoxESS H3-Pro Inverter Device."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from modbus_connection.model import Raw
from ..const import WorkMode
from ..model import FoxessDevice, UpdateReport
from ..h3.battery import FoxessH3Battery
from ..h3.control import FoxessH3Control
from ..h3.grid import FoxessH3Grid
from ..h3.inverter import FoxessH3InverterState
from .pv import FoxessH3ProPV

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit


class FoxessH3ProInverter(FoxessDevice):
    """FoxESS H3-Pro Commercial Three-Phase Hybrid Inverter (up to 6 PV strings)."""

    def __init__(
        self,
        unit: ModbusUnit,
        *,
        serial_number: str | None = None,
        model: str = "H3-Pro",
    ) -> None:
        """Initialize inverter components."""
        super().__init__(unit)
        self.serial_number = serial_number
        self.model = model

        # Sub-system components
        self.pv = FoxessH3ProPV(unit)
        self.battery = FoxessH3Battery(unit)
        self.grid = FoxessH3Grid(unit)
        self.inverter = FoxessH3InverterState(unit)
        self.control = FoxessH3Control(unit)

        self._readings: tuple[str, ...] = ("pv", "battery", "grid", "inverter")
        self._settings: tuple[str, ...] = ("control",)

    async def _async_setup(self) -> None:
        """Perform initial setup or validation if needed."""
        pass

    async def async_update_readings(self) -> UpdateReport:
        """Poll fast telemetry: PV generation (PV1-PV6), battery status, grid flow, and inverter state."""
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
        """Set the inverter operational work mode."""
        await self.async_ensure_setup()
        mode_val = int(mode)
        await self.control.async_write_value("work_mode", mode_val)

    async def async_set_min_soc(self, percent: int) -> None:
        """Set the minimum battery SoC target percentage (10-100%)."""
        await self.async_ensure_setup()
        if not (10 <= percent <= 100):
            raise ValueError(f"min_soc must be between 10 and 100%, got {percent}")
        await self.control.async_write_value("min_soc", percent)

    async def async_set_max_soc(self, percent: int) -> None:
        """Set the maximum battery SoC target percentage (10-100%)."""
        await self.async_ensure_setup()
        if not (10 <= percent <= 100):
            raise ValueError(f"max_soc must be between 10 and 100%, got {percent}")
        await self.control.async_write_value("max_soc", percent)
