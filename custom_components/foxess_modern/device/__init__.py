"""FoxESS Modbus device library."""

from .const import WorkMode
from .kh10.device import FoxessKH10Inverter

__all__ = [
    "FoxessKH10Inverter",
    "WorkMode",
]
