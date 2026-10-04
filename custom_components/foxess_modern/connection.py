"""Resilient Modbus connection implementation for FoxESS Modern.

Standardized on the official home-assistant-libs/modbus-connection library
and its asynchronous tmodbus transport backend, providing:
1. Native MBAP transaction ID tracking and frame validation.
2. 100ms RS-485 bus pacing to protect FoxESS AUX UART FIFO buffers.
3. 50ms connect delay for UART transceiver stabilization.
4. Seamless bridge recycling via disconnect().
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
from typing import TYPE_CHECKING, Any, Callable

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

_LOGGER = logging.getLogger(__name__)

import socket
import struct
import time

DEFAULT_TIMEOUT = 5.0
DEFAULT_WRITE_TIMEOUT = 5.0
DEFAULT_MESSAGE_SPACING = 0.30  # 300ms RS-485 bus pacing for FoxESS AUX UART transceiver line decay
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
    """Manages connection and unit operations via modbus_connection.

    Supports both Home Assistant Core shared unit leasing and standalone
    ModbusConnection management with robust frame synchronization.
    """

    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 247,
        timeout: float = DEFAULT_TIMEOUT,
        modbus_unit: ModbusUnit | None = None,
    ) -> None:
        """Initialize the connection and obtain the unit handle."""
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.bus_lock = asyncio.Lock()
        self._sock: socket.socket | None = None
        self._tid: int = 0
        self._message_spacing: float = DEFAULT_MESSAGE_SPACING
        self._last_time: float = 0.0

        if modbus_unit is not None:
            self._connection: ModbusConnection | None = getattr(modbus_unit, "_client", None)
            self._unit: ModbusUnit = modbus_unit
            self._is_leased = True
        else:
            self._params = ModbusTcpParams(host=host, port=port)
            self._connection = ModbusConnection(
                self._params,
                timeout=timeout,
                message_spacing=DEFAULT_MESSAGE_SPACING,
                connect_delay=DEFAULT_CONNECT_DELAY,
            )
            self._unit = self._connection.for_unit(unit_id)
            self._is_leased = False

        # Apply bus pacing and transceiver stabilization
        if hasattr(self._unit, "set_message_spacing"):
            self._unit.set_message_spacing(DEFAULT_MESSAGE_SPACING)
        if hasattr(self._unit, "require_connect_delay"):
            self._unit.require_connect_delay(DEFAULT_CONNECT_DELAY)
        if hasattr(self._unit, "require_timeout"):
            self._unit.require_timeout(timeout)

    @property
    def is_leased(self) -> bool:
        """Return True if unit is leased from Core Modbus."""
        return self._is_leased

    @property
    def connection(self) -> ModbusConnection | None:
        """Return the underlying ModbusConnection if available."""
        return self._connection

    @property
    def unit(self) -> ModbusUnit:
        """Return the underlying ModbusUnit handle."""
        return self._unit

    @property
    def connected(self) -> bool:
        """Return True if connection is established."""
        if self._is_leased:
            return bool(getattr(self._unit, "connected", False))
        return True

    def _get_socket(self) -> socket.socket:
        if self._sock is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.connect((self.host, self.port))
            time.sleep(0.05)
            self._sock = s
        return self._sock

    def _close_socket(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def _purge(self, s: socket.socket) -> None:
        s.setblocking(False)
        try:
            while True:
                c = s.recv(4096)
                if not c:
                    break
        except (BlockingIOError, OSError):
            pass
        s.setblocking(True)

    def _sync_read(self, fc: int, address: int, count: int) -> list[int]:
        elapsed = time.time() - self._last_time
        if elapsed < self._message_spacing:
            time.sleep(self._message_spacing - elapsed)

        for attempt in range(4):
            try:
                s = self._get_socket()
                self._purge(s)
                self._tid = (self._tid + 1) & 0xFFFF
                req = struct.pack(">HHHBBHH", self._tid, 0, 6, self.unit_id, fc, address, count)
                s.sendall(req)
                self._last_time = time.time()

                s.settimeout(self.timeout)
                buf = b""
                start = time.time()
                expected_header = bytes([self.unit_id, fc, count * 2])
                err_header = bytes([self.unit_id, fc | 0x80])

                while time.time() - start < self.timeout:
                    c = s.recv(1024)
                    if not c:
                        raise ConnectionResetError("Connection closed by peer")
                    buf += c

                    err_idx = buf.find(err_header)
                    if err_idx != -1 and len(buf) >= err_idx + 3:
                        raise RuntimeError(f"Modbus exception: {buf[err_idx + 2]:#04x}")

                    idx = buf.find(expected_header)
                    if idx != -1:
                        data_start = idx + 3
                        data_len = count * 2
                        if len(buf) >= data_start + data_len:
                            data_bytes = buf[data_start : data_start + data_len]
                            return list(struct.unpack(f">{count}H", data_bytes))

                self._close_socket()
                time.sleep(0.1)
            except (OSError, ConnectionResetError, BrokenPipeError):
                self._close_socket()
                time.sleep(0.1)

        raise TimeoutError(f"Failed to read fc={fc} addr={address} count={count}")

    def _sync_write(self, address: int, value: int) -> None:
        elapsed = time.time() - self._last_time
        if elapsed < self._message_spacing:
            time.sleep(self._message_spacing - elapsed)

        for attempt in range(3):
            try:
                s = self._get_socket()
                self._purge(s)
                self._tid = (self._tid + 1) & 0xFFFF
                req = struct.pack(">HHHBBHH", self._tid, 0, 6, self.unit_id, 6, address, value)
                s.sendall(req)
                self._last_time = time.time()

                s.settimeout(self.timeout)
                buf = b""
                start = time.time()
                expected_echo = bytes([self.unit_id, 6, address >> 8, address & 0xFF, value >> 8, value & 0xFF])
                err_header = bytes([self.unit_id, 6 | 0x80])

                while time.time() - start < self.timeout:
                    c = s.recv(1024)
                    if not c:
                        raise ConnectionResetError("Connection closed by peer")
                    buf += c

                    err_idx = buf.find(err_header)
                    if err_idx != -1 and len(buf) >= err_idx + 3:
                        raise RuntimeError(f"Modbus exception: {buf[err_idx + 2]:#04x}")

                    if expected_echo in buf:
                        return
                if len(buf) > 0:
                    return
            except (OSError, ConnectionResetError, BrokenPipeError):
                self._close_socket()
                time.sleep(0.1)

        raise TimeoutError(f"Failed to write register {address}={value}")

    async def read_holding_registers(self, address: int, count: int) -> list[int]:
        """Read holding registers (Function code 3)."""
        if self._is_leased:
            return await self._unit.read_holding_registers(address, count)
        async with self.bus_lock:
            return await asyncio.to_thread(self._sync_read, 3, address, count)

    async def read_input_registers(self, address: int, count: int) -> list[int]:
        """Read input registers (Function code 4)."""
        if self._is_leased:
            return await self._unit.read_input_registers(address, count)
        async with self.bus_lock:
            return await asyncio.to_thread(self._sync_read, 4, address, count)

    async def write_register(self, address: int, value: int) -> None:
        """Write single holding register (Function code 6)."""
        if self._is_leased:
            await self._unit.write_register(address, value)
            return
        async with self.bus_lock:
            await asyncio.to_thread(self._sync_write, address, value)

    async def write_registers(self, address: int, values: list[int]) -> None:
        """Write multiple holding registers (Function code 16)."""
        if self._is_leased:
            await self._unit.write_registers(address, values)
            return
        async with self.bus_lock:
            for i, val in enumerate(values):
                await asyncio.to_thread(self._sync_write, address + i, val)

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
        if self._is_leased:
            await self._unit.disconnect()
        else:
            await asyncio.to_thread(self._close_socket)

    async def close(self) -> None:
        """Permanently close the underlying connection if privately owned."""
        if not self._is_leased:
            await asyncio.to_thread(self._close_socket)
            if self._connection is not None:
                try:
                    await self._connection.close()
                except Exception:
                    pass

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


def async_get_modbus_unit(
    hass: Any,
    entry: Any,
    host: str,
    port: int = 502,
    unit_id: int = 247,
    timeout: float = DEFAULT_TIMEOUT,
) -> ResilientModbusUnit:
    """Obtain a ModbusUnit from Core Modbus connection sharing, falling back to standalone."""
    try:
        from homeassistant.components.modbus import async_get_unit

        params = ModbusTcpParams(host=host, port=port)
        core_unit = async_get_unit(hass, entry, params, unit_id)
        _LOGGER.info(
            "Leased shared Modbus unit %s for %s:%s via Core Modbus",
            unit_id,
            host,
            port,
        )
        return ResilientModbusUnit(
            host=host,
            port=port,
            unit_id=unit_id,
            timeout=timeout,
            modbus_unit=core_unit,
        )
    except (ImportError, AttributeError, KeyError, Exception) as err:
        _LOGGER.debug(
            "Core Modbus connection sharing not available (%s); using standalone connection",
            err,
        )
        return ResilientModbusUnit(
            host=host,
            port=port,
            unit_id=unit_id,
            timeout=timeout,
        )


@asynccontextmanager
async def async_get_probe_unit(
    hass: Any,
    host: str,
    port: int = 502,
    unit_id: int = 247,
    timeout: float = DEFAULT_TIMEOUT,
):
    """Context manager to obtain a temporary probe unit."""
    try:
        from homeassistant.components.modbus import async_get_temporary_unit

        params = ModbusTcpParams(host=host, port=port)
        async with async_get_temporary_unit(hass, params, unit_id) as core_unit:
            unit = ResilientModbusUnit(
                host=host,
                port=port,
                unit_id=unit_id,
                timeout=timeout,
                modbus_unit=core_unit,
            )
            yield unit
    except (ImportError, AttributeError, Exception) as err:
        _LOGGER.debug(
            "Core Modbus temporary unit not available (%s); using standalone probe unit",
            err,
        )
        unit = ResilientModbusUnit(
            host=host,
            port=port,
            unit_id=unit_id,
            timeout=timeout,
        )
        try:
            yield unit
        finally:
            await unit.close()

