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
from typing import TYPE_CHECKING, Any

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

_LOGGER = logging.getLogger(__name__)


class ResilientModbusUnit:
    """Manages connection and unit operations via modbus_connection.tmodbus."""

    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 247,
        timeout: float = 2.5,
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
            message_spacing=0.1,  # 100ms RS-485 bus pacing for FoxESS AUX UART
            connect_delay=0.05,   # 50ms transceiver line stabilization
        )
        self._unit: ModbusUnit = self._connection.for_unit(unit_id)

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

    async def disconnect(self) -> None:
        """Recycle the connection when the serial bridge stops answering."""
        _LOGGER.info("Recycling Modbus connection to %s:%s", self.host, self.port)
        await self._unit.disconnect()

    async def close(self) -> None:
        """Permanently close the underlying connection."""
        await self._connection.close()

    def set_message_spacing(self, seconds: float) -> None:
        """Set minimum pacing interval between requests."""
        if hasattr(self._unit, "set_message_spacing"):
            self._unit.set_message_spacing(seconds)

    def require_timeout(self, seconds: float | None) -> None:
        """Set link request timeout."""
        if hasattr(self._unit, "require_timeout"):
            self._unit.require_timeout(seconds)

    def require_connect_delay(self, seconds: float | None) -> None:
        """Set connect settle delay."""
        if hasattr(self._unit, "require_connect_delay"):
            self._unit.require_connect_delay(seconds)
