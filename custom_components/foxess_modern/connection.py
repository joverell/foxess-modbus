"""Resilient Modbus connection implementation for FoxESS Modern.

Standardized on the official home-assistant-libs/modbus-connection library
and its asynchronous tmodbus transport backend, providing:
1. Native MBAP transaction ID tracking and frame validation.
2. 100ms RS-485 bus pacing to protect FoxESS AUX UART FIFO buffers.
3. 50ms connect delay for UART transceiver stabilization.
4. Seamless bridge recycling via disconnect().
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 2.5
DEFAULT_MESSAGE_SPACING = 0.1  # 100ms RS-485 bus pacing for FoxESS AUX UART
DEFAULT_CONNECT_DELAY = 0.05   # 50ms transceiver line stabilization


def create_connection(
    host: str,
    port: int = 502,
    timeout: float = DEFAULT_TIMEOUT,
    message_spacing: float = DEFAULT_MESSAGE_SPACING,
    connect_delay: float = DEFAULT_CONNECT_DELAY,
) -> ModbusConnection:
    """Create a standardized ModbusConnection using tmodbus transport."""
    params = ModbusTcpParams(host=host, port=port)
    return ModbusConnection(
        params,
        timeout=timeout,
        message_spacing=message_spacing,
        connect_delay=connect_delay,
    )


class ResilientModbusUnit:
    """Manages connection and unit operations via modbus_connection.tmodbus.

    Conforms to the ModbusUnit protocol while providing lifecycle helpers.
    """

    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 247,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the connection and obtain the unit handle."""
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout

        self._params = ModbusTcpParams(host=host, port=port)
        self._connection = ModbusConnection(
            self._params,
            timeout=timeout,
            message_spacing=DEFAULT_MESSAGE_SPACING,
            connect_delay=DEFAULT_CONNECT_DELAY,
        )
        self._unit: ModbusUnit = self._connection.for_unit(unit_id)

    @property
    def connection(self) -> ModbusConnection:
        """Return the underlying ModbusConnection."""
        return self._connection

    @property
    def unit(self) -> ModbusUnit:
        """Return the underlying ModbusUnit handle."""
        return self._unit

    @property
    def connected(self) -> bool:
        """Return True if connection is established."""
        return bool(getattr(self._unit, "connected", False))

    async def read_holding_registers(self, address: int, count: int) -> list[int]:
        """Read holding registers (Function code 3)."""
        return await self._unit.read_holding_registers(address, count)

    async def read_input_registers(self, address: int, count: int) -> list[int]:
        """Read input registers (Function code 4)."""
        return await self._unit.read_input_registers(address, count)

    async def write_register(self, address: int, value: int) -> None:
        """Write single holding register (Function code 6)."""
        await self._unit.write_register(address, value)

    async def write_registers(self, address: int, values: list[int]) -> None:
        """Write multiple holding registers (Function code 16)."""
        await self._unit.write_registers(address, values)

    async def read_coils(self, address: int, count: int) -> list[bool]:
        """Read coils (Function code 1)."""
        return await self._unit.read_coils(address, count)

    async def read_discrete_inputs(self, address: int, count: int) -> list[bool]:
        """Read discrete inputs (Function code 2)."""
        return await self._unit.read_discrete_inputs(address, count)

    async def write_coil(self, address: int, value: bool) -> None:
        """Write single coil (Function code 5)."""
        await self._unit.write_coil(address, value)

    async def write_coils(self, address: int, values: list[bool]) -> None:
        """Write multiple coils (Function code 15)."""
        await self._unit.write_coils(address, values)

    async def read_exception_status(self) -> int:
        """Read exception status (Function code 7)."""
        return await self._unit.read_exception_status()

    async def diagnostics(self, sub_function: int, data: int = 0) -> int:
        """Send diagnostic function (Function code 8)."""
        return await self._unit.diagnostics(sub_function, data)

    async def get_comm_event_counter(self) -> tuple[bool, int]:
        """Get comm event counter (Function code 11)."""
        return await self._unit.get_comm_event_counter()

    async def get_comm_event_log(self) -> bytes:
        """Get comm event log (Function code 12)."""
        return await self._unit.get_comm_event_log()

    async def report_server_id(self) -> bytes:
        """Report server ID (Function code 17)."""
        return await self._unit.report_server_id()

    async def read_file_record(self, file: int, record: int, length: int) -> list[int]:
        """Read file record (Function code 20)."""
        return await self._unit.read_file_record(file, record, length)

    async def write_file_record(self, file: int, record: int, values: list[int]) -> None:
        """Write file record (Function code 21)."""
        await self._unit.write_file_record(file, record, values)

    async def mask_write_register(self, address: int, and_mask: int, or_mask: int) -> None:
        """Mask write register (Function code 22)."""
        await self._unit.mask_write_register(address, and_mask, or_mask)

    async def read_write_registers(
        self, read_address: int, read_count: int, write_address: int, write_values: list[int]
    ) -> list[int]:
        """Read write registers (Function code 23)."""
        return await self._unit.read_write_registers(read_address, read_count, write_address, write_values)

    async def read_fifo_queue(self, address: int) -> list[int]:
        """Read FIFO queue (Function code 24)."""
        return await self._unit.read_fifo_queue(address)

    async def read_device_identification(self) -> dict[int, bytes]:
        """Read device identification (Function code 43 / 14)."""
        return await self._unit.read_device_identification()

    async def disconnect(self) -> None:
        """Recycle the connection when the serial bridge stops answering."""
        _LOGGER.info("Recycling Modbus connection to %s:%s", self.host, self.port)
        await self._unit.disconnect()

    async def close(self) -> None:
        """Permanently close the underlying connection."""
        await self._connection.close()

    def set_message_spacing(self, seconds: float) -> None:
        """Set minimum pacing interval between requests."""
        self._unit.set_message_spacing(seconds)

    def require_timeout(self, seconds: float | None) -> None:
        """Set link request timeout."""
        self._unit.require_timeout(seconds)

    def require_connect_delay(self, seconds: float | None) -> None:
        """Set connect settle delay."""
        self._unit.require_connect_delay(seconds)

    def on_connection_lost(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a callback for when connection is lost."""
        return self._unit.on_connection_lost(callback)

    def __getattr__(self, name: str) -> Any:
        """Forward any other attributes to the underlying ModbusUnit."""
        return getattr(self._unit, name)
