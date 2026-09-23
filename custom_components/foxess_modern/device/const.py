"""Constants and Enums for FoxESS Modbus."""

from enum import IntEnum, StrEnum


class WorkMode(IntEnum):
    """FoxESS standard inverter work modes."""

    SELF_USE = 0
    FEED_IN_FIRST = 1
    BACK_UP = 2


class InverterState(StrEnum):
    """FoxESS inverter operational states."""

    SELF_TEST = "Self Test"
    WAITING = "Waiting"
    CHECKING = "Checking"
    ON_GRID = "On Grid"
    OFF_GRID = "Off Grid / EPS"
    RECOVERABLE_FAULT = "Recoverable Fault"
    UNRECOVERABLE_FAULT = "Unrecoverable Fault"
    STANDBY = "Standby"
    FAULT = "Fault"
    UNKNOWN = "Unknown"
