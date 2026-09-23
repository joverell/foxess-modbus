"""Resilient Modbus connection implementation for FoxESS Modern.

Specifically engineered for RS-485 to Ethernet/Wi-Fi adapters (Waveshare, USR-W610,
Elfin, etc.) that experience RS-485 bus idle chatter and frame misalignment.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
import socket
import struct
import time
from typing import Any

from modbus_connection.exceptions import (
    ModbusConnectionError,
    ModbusExceptionError,
    ModbusTimeoutError,
)

_LOGGER = logging.getLogger(__name__)


class ResilientModbusUnit:
    """Resilient ModbusUnit implementation for network serial bridges.

    Robustly handles:
    1. Pre-send buffer draining (cleans floating RS-485 line chatter).
    2. Adaptive frame alignment (handles leading zero bytes from UART transceivers).
    3. Persistent socket retention (avoids socket churn on transient frame hiccups).
    4. Auto-reconnection with backoff on genuine network dropouts.
    """

    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 247,
        timeout: float = 1.5,
    ) -> None:
        """Initialize the resilient unit."""
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self._tid = 0
        self._lock = asyncio.Lock()
        self._sock: socket.socket | None = None
        self._connected = False
        self._spacing = 0.08
        self._last_request_time = 0.0
        self._conn_lost_callbacks: list[Callable[[], None]] = []

    @property
    def connected(self) -> bool:
        """Return true if socket is connected."""
        return self._connected

    def _get_socket(self) -> socket.socket:
        """Get or establish TCP socket."""
        if self._sock is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.connect((self.host, self.port))
            # Settle time after TCP connect to allow UART transceiver to stabilize
            time.sleep(0.05)
            self._sock = s
            self._connected = True
        return self._sock

    def _close_socket(self) -> None:
        """Close socket cleanly."""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self._connected = False

    def _purge(self, s: socket.socket) -> int:
        """Purge stale noise bytes from socket read buffer before sending."""
        s.setblocking(False)
        purged = 0
        try:
            while True:
                c = s.recv(4096)
                if not c:
                    break
                purged += len(c)
        except (BlockingIOError, socket.error):
            pass
        s.setblocking(True)
        return purged

    def _sync_read_registers(self, fc: int, address: int, count: int) -> list[int]:
        """Perform a synchronous register read with frame alignment."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._spacing:
            time.sleep(self._spacing - elapsed)

        last_err: Exception | None = None
        for attempt in range(2):
            try:
                s = self._get_socket()
                self._purge(s)
                self._tid = (self._tid + 1) & 0xFFFF
                req = struct.pack(
                    ">HHHBBHH", self._tid, 0, 6, self.unit_id, fc, address, count
                )
                s.sendall(req)
                self._last_request_time = time.time()

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

                    # Check exception response
                    err_idx = buf.find(err_header)
                    if err_idx != -1 and len(buf) >= err_idx + 3:
                        err_code = buf[err_idx + 2]
                        raise ModbusExceptionError(err_code)

                    # Check normal response
                    idx = buf.find(expected_header)
                    if idx != -1:
                        data_start = idx + 3
                        data_len = count * 2
                        if len(buf) >= data_start + data_len:
                            data_bytes = buf[data_start : data_start + data_len]
                            words = struct.unpack(f">{count}H", data_bytes)
                            return list(words)
            except ModbusExceptionError:
                raise
            except (socket.error, ConnectionResetError, BrokenPipeError) as e:
                last_err = e
                self._close_socket()
                time.sleep(0.1 * (attempt + 1))
            except Exception as e:
                last_err = e
                # Transient frame mismatch or read timeout: do not tear down the socket,
                # just sleep briefly and retry with a clean purged buffer on next attempt.
                time.sleep(0.08 * (attempt + 1))

        if isinstance(last_err, (socket.error, ConnectionResetError, BrokenPipeError)):
            raise ModbusConnectionError(
                f"Failed to read fc={fc} addr={address} count={count}: {last_err}"
            ) from last_err

        raise ModbusTimeoutError(
            f"Failed to read fc={fc} addr={address} count={count}: {last_err}"
        )

    def _sync_write_single_register(self, address: int, value: int) -> None:
        """Perform a synchronous single register write with verification."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._spacing:
            time.sleep(self._spacing - elapsed)

        last_err: Exception | None = None
        for attempt in range(2):
            try:
                s = self._get_socket()
                self._purge(s)
                self._tid = (self._tid + 1) & 0xFFFF
                req = struct.pack(
                    ">HHHBBHH", self._tid, 0, 6, self.unit_id, 6, address, value
                )
                s.sendall(req)
                self._last_request_time = time.time()

                s.settimeout(self.timeout)
                buf = b""
                start = time.time()
                expected_header = bytes([self.unit_id, 6])
                err_header = bytes([self.unit_id, 6 | 0x80])

                while time.time() - start < self.timeout:
                    c = s.recv(1024)
                    if not c:
                        raise ConnectionResetError("Connection closed by peer")
                    buf += c

                    err_idx = buf.find(err_header)
                    if err_idx != -1 and len(buf) >= err_idx + 3:
                        err_code = buf[err_idx + 2]
                        raise ModbusExceptionError(err_code)

                    idx = buf.find(expected_header)
                    if idx != -1 and len(buf) >= idx + 6:
                        resp_addr, resp_val = struct.unpack(">HH", buf[idx + 2 : idx + 6])
                        if resp_addr == address and resp_val == value:
                            return
            except ModbusExceptionError:
                raise
            except (socket.error, ConnectionResetError, BrokenPipeError) as e:
                last_err = e
                self._close_socket()
                time.sleep(0.1 * (attempt + 1))
            except Exception as e:
                last_err = e
                time.sleep(0.08 * (attempt + 1))

        if isinstance(last_err, (socket.error, ConnectionResetError, BrokenPipeError)):
            raise ModbusConnectionError(
                f"Failed to write single register addr={address} val={value}: {last_err}"
            ) from last_err

        raise ModbusTimeoutError(
            f"Failed to write single register addr={address} val={value}: {last_err}"
        )

    def _sync_write_multiple_registers(self, address: int, values: list[int]) -> None:
        """Perform a synchronous multiple registers write with verification."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._spacing:
            time.sleep(self._spacing - elapsed)

        count = len(values)
        byte_count = count * 2
        packed_vals = struct.pack(f">{count}H", *values)

        last_err: Exception | None = None
        for attempt in range(2):
            try:
                s = self._get_socket()
                self._purge(s)
                self._tid = (self._tid + 1) & 0xFFFF
                header = struct.pack(
                    ">HHHBBHHB",
                    self._tid,
                    0,
                    7 + byte_count,
                    self.unit_id,
                    16,
                    address,
                    count,
                    byte_count,
                )
                s.sendall(header + packed_vals)
                self._last_request_time = time.time()

                s.settimeout(self.timeout)
                buf = b""
                start = time.time()
                expected_header = bytes([self.unit_id, 16])
                err_header = bytes([self.unit_id, 16 | 0x80])

                while time.time() - start < self.timeout:
                    c = s.recv(1024)
                    if not c:
                        raise ConnectionResetError("Connection closed by peer")
                    buf += c

                    err_idx = buf.find(err_header)
                    if err_idx != -1 and len(buf) >= err_idx + 3:
                        err_code = buf[err_idx + 2]
                        raise ModbusExceptionError(err_code)

                    idx = buf.find(expected_header)
                    if idx != -1 and len(buf) >= idx + 6:
                        resp_addr, resp_count = struct.unpack(">HH", buf[idx + 2 : idx + 6])
                        if resp_addr == address and resp_count == count:
                            return
            except ModbusExceptionError:
                raise
            except (socket.error, ConnectionResetError, BrokenPipeError) as e:
                last_err = e
                self._close_socket()
                time.sleep(0.1 * (attempt + 1))
            except Exception as e:
                last_err = e
                time.sleep(0.08 * (attempt + 1))

        if isinstance(last_err, (socket.error, ConnectionResetError, BrokenPipeError)):
            raise ModbusConnectionError(
                f"Failed to write multiple registers addr={address} count={count}: {last_err}"
            ) from last_err

        raise ModbusTimeoutError(
            f"Failed to write multiple registers addr={address} count={count}: {last_err}"
        )

    async def read_holding_registers(self, address: int, count: int) -> list[int]:
        """Read holding registers (Function code 3)."""
        async with self._lock:
            return await asyncio.to_thread(self._sync_read_registers, 3, address, count)

    async def read_input_registers(self, address: int, count: int) -> list[int]:
        """Read input registers (Function code 4)."""
        async with self._lock:
            return await asyncio.to_thread(self._sync_read_registers, 4, address, count)

    async def write_register(self, address: int, value: int) -> None:
        """Write single holding register (Function code 6)."""
        async with self._lock:
            await asyncio.to_thread(self._sync_write_single_register, address, value)

    async def write_registers(self, address: int, values: list[int]) -> None:
        """Write multiple holding registers (Function code 16)."""
        async with self._lock:
            await asyncio.to_thread(self._sync_write_multiple_registers, address, values)

    async def read_coils(self, address: int, count: int) -> list[bool]:
        """Stub for coil reads."""
        return [False] * count

    async def read_discrete_inputs(self, address: int, count: int) -> list[bool]:
        """Stub for discrete input reads."""
        return [False] * count

    async def write_coil(self, address: int, value: bool) -> None:
        """Stub for single coil write."""
        pass

    async def write_coils(self, address: int, values: list[bool]) -> None:
        """Stub for multiple coil writes."""
        pass

    def set_message_spacing(self, seconds: float) -> None:
        """Set minimum pacing interval between requests."""
        self._spacing = max(0.01, seconds)

    def require_timeout(self, seconds: float | None) -> None:
        """Set link request timeout."""
        if seconds is not None:
            self.timeout = max(self.timeout, seconds)

    def require_connect_delay(self, seconds: float | None) -> None:
        """Stub for connect delay requirement."""
        pass

    def on_connection_lost(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register connection lost callback."""
        self._conn_lost_callbacks.append(callback)
        return lambda: (
            self._conn_lost_callbacks.remove(callback)
            if callback in self._conn_lost_callbacks
            else None
        )

    async def disconnect(self) -> None:
        """Disconnect underlying TCP socket."""
        async with self._lock:
            self._close_socket()

    async def close(self) -> None:
        """Close connection."""
        await self.disconnect()

    async def __aenter__(self) -> ResilientModbusUnit:
        """Enter async context."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context."""
        await self.close()
