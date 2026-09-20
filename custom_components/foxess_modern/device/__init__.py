"""FoxESS Modbus device library."""

from .const import InverterState, WorkMode
from .h1.device import FoxessH1Inverter
from .h3.device import FoxessH3Inverter
from .identify import create_inverter, identify_model
from .kh10.device import FoxessKH10Inverter

FoxessKHInverter = FoxessKH10Inverter

__all__ = [
    "FoxessH1Inverter",
    "FoxessH3Inverter",
    "FoxessKH10Inverter",
    "FoxessKHInverter",
    "InverterState",
    "WorkMode",
    "create_inverter",
    "identify_model",
]
