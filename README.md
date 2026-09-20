# foxess-modbus

[![PyPI](https://img.shields.io/pypi/v/foxess-modbus.svg)](https://pypi.org/project/foxess-modbus/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A modern, standalone Python device library for communicating with **FoxESS hybrid solar inverters** over Modbus.

Built specifically against [`modbus-connection`](https://home-assistant-libs.github.io/modbus-connection/), following the architectural pattern introduced in [Modernizing Modbus in Home Assistant](https://developers.home-assistant.io/blog/2026/07/05/modernizing-modbus/) (Home Assistant Core 2026.7+).

---

## Key Features

- **Backend-Neutral**: Operates on `modbus-connection`, supporting both `tmodbus` and `pymodbus` seamlessly.
- **Inverter Microcontroller Protection**: Automatically groups and limits register reads (`max_span = 32`) to prevent the FoxESS AUX microcontroller UART FIFO buffer from overflowing and stalling.
- **Shared Gateway Friendly**: Designed to operate with Home Assistant's `async_get_unit` connection broker. Multiple integrations and meters (e.g. Eastron, heat pumps) can share the same physical RS-485 bridge without bus collisions.
- **Strongly Typed**: Registers and coils map to typed Python properties with automatic endianness and scale factor decoding.
- **Unit Tested**: Fully tested with mock in-memory Modbus backends.

---

## Supported Inverter Models

| Series | Models | Interface | Modbus Type | Register Set |
| :--- | :--- | :--- | :--- | :--- |
| **KH Series** | KH7, KH8, KH9, KH10, KH10.5 | AUX (RS-485) | Modbus TCP / RTU | Holding Registers (1.33+) |

*Community contributions for H1, H3, AIO, and EVO series are welcome!*

---

## Installation

```bash
pip install "foxess-modbus"
```

To include the high-performance async `tmodbus` backend:

```bash
pip install "foxess-modbus[tmodbus]"
```

---

## Quick Start Example

```python
import asyncio
from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection
from foxess_modbus import FoxessKH10Inverter, WorkMode

async def main():
    # Configure your RS-485 to Ethernet adapter (e.g., Waveshare, Elfin EW11)
    params = ModbusTcpParams(host="192.168.86.162", port=502)
    connection = ModbusConnection(params, timeout=5.0, message_spacing=0.08)

    try:
        # Request unit handle for slave address 247
        unit = connection.for_unit(247)
        inverter = FoxessKH10Inverter(unit)

        # Refresh all telemetry in minimal batched Modbus calls
        report = await inverter.async_update_readings()
        print(f"Updated components: {report.updated}")

        # Access decoded metrics
        print(f"PV Total Power:    {inverter.pv.pv_power_total} W")
        print(f"PV1:               {inverter.pv.pv1_voltage} V, {inverter.pv.pv1_power} W")
        print(f"PV2:               {inverter.pv.pv2_voltage} V, {inverter.pv.pv2_power} W")
        print(f"Battery SoC:       {inverter.battery.soc} %")
        print(f"Battery Power:     {inverter.battery.power} W")
        print(f"Battery Voltage:   {inverter.battery.voltage} V")
        print(f"Grid Voltage:      {inverter.grid.voltage} V")
        print(f"CT Meter Power:    {inverter.grid.ct_meter_power} W")
        print(f"Inverter State:    {inverter.inverter.state}")

        # Control commands
        await inverter.async_set_work_mode(WorkMode.SELF_USE)
        await inverter.async_set_min_soc(15)

    finally:
        await connection.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Register Map Reference (KH10 Holding Registers)

| Subsystem | Register | Size / Type | Scale | Unit | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PV** | `39070` | 16-bit uint | 0.1 | V | PV1 Voltage |
| | `39071` | 16-bit uint | 0.01 | A | PV1 Current |
| | `39279-39280` | 32-bit uint | 1.0 | W | PV1 Power |
| | `39072` | 16-bit uint | 0.1 | V | PV2 Voltage |
| | `39073` | 16-bit uint | 0.01 | A | PV2 Current |
| | `39281-39282` | 32-bit uint | 1.0 | W | PV2 Power |
| **Grid** | `31006` | 16-bit uint | 0.1 | V | Grid Voltage |
| | `31007` | 16-bit uint | 0.1 | A | Inverter Current |
| | `31008` | 16-bit int | 1.0 | W | Inverter Power |
| | `31009` | 16-bit uint | 0.01 | Hz | Grid Frequency |
| | `31016` | 16-bit int | 1.0 | W | House Load Power |
| | `39168-39169` | 32-bit int | 1.0 | W | Grid CT Active Power (+export, -import) |
| **Battery** | `31020` | 16-bit uint | 0.1 | V | Battery Voltage |
| | `31021` | 16-bit int | 0.1 | A | Battery Current |
| | `31022` | 16-bit int | 1.0 | W | Battery Power (+discharge, -charge) |
| | `31024` | 16-bit uint | 1.0 | % | Battery State of Charge (SoC) |
| | `31023` | 16-bit int | 0.1 | °C | Battery Temperature |
| | `31025` | 16-bit uint | 0.1 | A | BMS Max Charge Rate |
| | `31026` | 16-bit uint | 0.1 | A | BMS Max Discharge Rate |
| **Inverter** | `31018` | 16-bit int | 0.1 | °C | Inverter Heatsink Temperature |
| | `31019` | 16-bit int | 0.1 | °C | Ambient Temperature |
| | `31027` | 16-bit uint | 1.0 | enum | Inverter State (2=On-Grid) |
| **Control** | `41000` | 16-bit uint | 1.0 | enum | Work Mode (0=Self Use, 1=Feed-in, 2=Backup) |
| | `41009` | 16-bit uint | 1.0 | % | Min SoC |
| | `41010` | 16-bit uint | 1.0 | % | Max SoC |
| | `44000` | 16-bit uint | 1.0 | bool | Remote Active Power Override Enable |
| | `44001` | 16-bit uint | 1.0 | s | Remote Timeout (watchdog) |
| | `44002` | 16-bit int | 1.0 | W | Remote Active Power (-charge, +discharge) |

---

## Contributing

1. Fork this repository.
2. Install in editable mode with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run tests before submitting a PR:
   ```bash
   pytest
   ```

## License

This project is licensed under the Apache 2.0 License.
