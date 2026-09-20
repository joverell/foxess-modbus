"""Base component models for FoxESS."""

from __future__ import annotations

from modbus_connection.model import Component


class FoxessComponent(Component):
    """Base class for FoxESS Modbus components.

    max_span controls the maximum contiguous register count requested
    in a single frame. FoxESS AUX UART microcontrollers have limited
    FIFO buffers, so keeping this bounded (e.g. 32 registers) prevents stalls.
    """

    max_span = 32
