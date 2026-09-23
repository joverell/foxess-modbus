from collections.abc import Iterable
from modbus_connection.exceptions import ModbusConnectionError, ModbusError, ModbusTimeoutError
from modbus_connection.model import Component, Device, UpdateReport


class FoxessComponent(Component):
    """Base class for FoxESS Modbus components.

    max_span controls the maximum contiguous register count requested
    in a single frame. FoxESS AUX UART microcontrollers have limited
    FIFO buffers, so keeping this bounded (e.g. 32 registers) prevents stalls.
    """

    max_span = 8


class FoxessDevice(Device):
    """Base class for FoxESS inverters reached through a ModbusUnit.

    Robustly handles half-duplex RS-485 communication by recording individual
    sub-system read timeouts in report.failed without aborting the entire poll
    or abandoning remaining sub-systems.
    """

    async def async_poll(
        self, names: Iterable[str], report: UpdateReport | None = None
    ) -> UpdateReport:
        """Poll each named sub-system and record outcome."""
        await self.async_ensure_setup()
        if report is None:
            report = UpdateReport()
        updated: list[str] = []
        for name in names:
            component = getattr(self, name)
            if component is None:
                continue
            try:
                await component.async_update(notify=False)
            except ModbusConnectionError:
                raise
            except (ModbusTimeoutError, ModbusError) as err:
                report.failed[name] = err
            else:
                report.updated.add(name)
                updated.append(name)
        for name in updated:
            getattr(self, name).notify()
        return report

