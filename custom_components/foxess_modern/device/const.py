"""Constants and Enums for FoxESS Modbus."""

from enum import IntEnum


class WorkMode(IntEnum):
    """FoxESS standard inverter work modes."""

    SELF_USE = 0
    FEED_IN_FIRST = 1
    BACK_UP = 2


class InverterState(IntEnum):
    """FoxESS KH inverter operational state codes."""

    WAITING = 0
    CHECKING = 1
    ON_GRID = 2
    OFF_GRID = 3
    FAULT = 4
    PERMANENT_FAULT = 5
