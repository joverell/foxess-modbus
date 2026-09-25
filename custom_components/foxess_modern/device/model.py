"""Base model classes for FoxESS Modbus components and devices."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from modbus_connection import (
    ModbusConnectionError,
    ModbusError,
    ModbusTimeoutError,
    ModbusUnit,
)
from modbus_connection.model import Component

try:
    from modbus_connection.model import Raw
except ImportError:
    try:
        from modbus_connection.model._const import Raw
    except ImportError:
        Raw = dict[str, dict[int, int | bool]]

try:
    from modbus_connection.model import UpdateReport
except ImportError:
    try:
        from modbus_connection.model.device import UpdateReport
    except ImportError:

        @dataclass
        class UpdateReport:
            """What one poll managed to refresh."""

            updated: set[str] = field(default_factory=set)
            failed: dict[str, ModbusError] = field(default_factory=dict)

            @property
            def complete(self) -> bool:
                """Whether every sub-system the poll covered refreshed."""
                return not self.failed

try:
    from modbus_connection.model import Device
except ImportError:
    try:
        from modbus_connection.model.device import Device
    except ImportError:

        class Device:
            """Device protocol fallback."""

            def __init__(self, unit: ModbusUnit) -> None:
                self.modbus_unit = unit
                self._setup_done = False

            async def _async_setup(self) -> None:
                """Read what never changes and settle which optional sub-systems exist."""

            async def async_ensure_setup(self) -> None:
                """Run _async_setup() once; a failed run is retried on the next call."""
                if self._setup_done:
                    return
                await self._async_setup()
                self._setup_done = True

            async def async_poll(
                self, names: Iterable[str], report: UpdateReport | None = None
            ) -> UpdateReport:
                """Read each named sub-system on its own and record what happened."""
                await self.async_ensure_setup()
                if report is None:
                    report = UpdateReport()
                updated: list[str] = []
                for name in names:
                    component = getattr(self, name, None)
                    if component is None:
                        continue
                    try:
                        await component.async_update(notify=False)
                    except ModbusConnectionError:
                        raise
                    except ModbusTimeoutError as err:
                        if not report.updated and not report.failed:
                            raise
                        report.failed[name] = err
                    except ModbusError as err:
                        report.failed[name] = err
                    else:
                        report.updated.add(name)
                        updated.append(name)
                for name in updated:
                    getattr(self, name).notify()
                return report

            async def async_read_raw(self, names: Iterable[str]) -> Raw:
                """Read the named sub-systems and return their raw maps merged into one."""
                await self.async_ensure_setup()
                raw: Raw = {}
                for name in names:
                    component = getattr(self, name, None)
                    if component is None:
                        continue
                    comp_raw = await component.async_read_raw(notify=False)
                    for space, addrs in comp_raw.items():
                        raw.setdefault(space, {}).update(addrs)
                return {space: dict(sorted(addrs.items())) for space, addrs in sorted(raw.items())}


class FoxessComponent(Component):
    """Base class for FoxESS Modbus components.

    max_span controls the maximum contiguous register count requested
    in a single frame. FoxESS AUX UART microcontrollers have limited
    FIFO buffers, so keeping this bounded (max_span = 8) prevents stalls.
    """

    max_span = 8


class FoxessDevice(Device):
    """Base class for FoxESS inverters reached through a ModbusUnit.

    Inherits upstream modbus_connection.model.Device with zero deviation:
    - Fast propagation of ModbusConnectionError on connection loss.
    - Propagation of ModbusTimeoutError when link is dead for coordinator recycling.
    - Recording of individual sub-system errors in report.failed during normal polls.
    """
