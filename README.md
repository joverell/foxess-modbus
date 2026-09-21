<p align="center">
  <img src="https://raw.githubusercontent.com/joverell/foxess-modbus/main/icon.png" width="120" height="120" alt="FoxESS Modbus Logo" style="border-radius: 26px;">
</p>

<h1 align="center">foxess-modbus</h1>

<p align="center">
  <a href="https://github.com/joverell/foxess-modbus/releases/latest"><img src="https://img.shields.io/github/v/release/joverell/foxess-modbus" alt="GitHub Release"></a>
  <a href="https://github.com/joverell/foxess-modbus/blob/main/LICENSE"><img src="https://img.shields.io/github/license/joverell/foxess-modbus" alt="GitHub License"></a>
  <a href="https://github.com/hacs/default"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS: Custom"></a>
  <a href="https://github.com/joverell/foxess-modbus/actions/workflows/hassfest.yaml"><img src="https://github.com/joverell/foxess-modbus/actions/workflows/hassfest.yaml/badge.svg" alt="Hassfest"></a>
  <a href="https://github.com/joverell/foxess-modbus/actions/workflows/hacs.yaml"><img src="https://github.com/joverell/foxess-modbus/actions/workflows/hacs.yaml/badge.svg" alt="Validate HACS"></a>
  <a href="https://github.com/joverell/foxess-modbus/actions/workflows/pytest.yaml"><img src="https://github.com/joverell/foxess-modbus/actions/workflows/pytest.yaml/badge.svg" alt="pytest"></a>
  <a href="https://www.buymeacoffee.com/joverell"><img src="https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-yellow?logo=buymeacoffee" alt="Buy Me A Coffee"></a>
</p>

A modern, standalone Python device library and Home Assistant custom integration for communicating with **FoxESS hybrid solar inverters** over Modbus.

Built specifically against [`modbus-connection`](https://home-assistant-libs.github.io/modbus-connection/), following the architectural pattern introduced in [Modernizing Modbus in Home Assistant](https://developers.home-assistant.io/blog/2026/07/05/modernizing-modbus/) (Home Assistant Core 2026.7+).

### Like this integration?

<a href="https://www.buymeacoffee.com/joverell" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" style="height: 60px !important;width: 217px !important;"/></a>

---

## Key Features

- **Backend-Neutral**: Operates on `modbus-connection`, supporting both `tmodbus` and `pymodbus` seamlessly.
- **Inverter Microcontroller Protection**: Automatically groups and limits register reads (`max_span = 32`) to prevent the FoxESS AUX microcontroller UART FIFO buffer from overflowing and stalling.
- **Shared Gateway Friendly**: Designed to operate with Home Assistant's `async_get_unit` connection broker. Multiple integrations and meters (e.g. Eastron, heat pumps) can share the same physical RS-485 bridge without bus collisions.
- **Strongly Typed**: Registers and coils map to typed Python properties with automatic endianness and scale factor decoding.
- **Unit Tested**: Fully tested with mock in-memory Modbus backends.

---

## Supported Inverter Models

| Series | Models | Strings / Trackers | Interface | Modbus Type | Register Set |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **H3-Pro Series** | H3-Pro-15.0 to H3-Pro-30.0 | **6 Strings** (PV1–PV6 across 3 MPPTs) | RS485 / LAN | Modbus TCP / RTU | Holding Registers (Commercial) |
| **KH Series** | KH7, KH8, KH9, KH10, KH10.5 | **4 Strings** (PV1–PV4 across 4 MPPTs) | AUX / LAN | Modbus TCP / RTU | Holding Registers (1.33+) |
| **H3 / AC3 Series** | H3-5.0 to H3-12.0, AC3, AIO-H3 | **2 Strings** (PV1–PV2 across 2 MPPTs) | RS485 / LAN | Modbus TCP / RTU | Holding Registers (Three-Phase) |
| **H1 / AC1 Series** | H1-3.0 to H1-6.0, AC1, AIO-H1 | **2 Strings** (PV1–PV2 across 2 MPPTs) | AUX / LAN | Modbus TCP / RTU | Holding Registers |

---

## Home Assistant Installation

### Option 1: 1-Click via HACS

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=joverell&repository=foxess-modbus&category=integration)

1. Click the **Open in HACS** badge above.
2. In the modal dialog, click **Add**.
3. Download the integration and restart Home Assistant.
4. Click the button below to add your inverter:

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=foxess_modern)

### Option 2: Manual Installation

Copy `custom_components/foxess_modern` into your Home Assistant `<config>/custom_components/` directory and restart.

---

## Home Assistant Energy Dashboard Setup

`foxess_modern` automatically creates native cumulative energy entities (measured in **kWh** with `device_class: energy` and `state_class: total_increasing`). These sensors persist across Home Assistant restarts and are directly selectable in Home Assistant's built-in **Energy Dashboard** without needing to manually configure Riemann sum integral helpers.

Navigate to **Settings → Dashboards → Energy** and configure the fields as follows:

| Energy Dashboard Category | Recommended Entity | Description |
| :--- | :--- | :--- |
| **Electricity Grid: Grid Consumption** | `sensor.<serial>_grid_import_energy_total` | Total energy imported from the grid (kWh) |
| **Electricity Grid: Return to Grid** | `sensor.<serial>_grid_export_energy_total` | Total solar energy exported to the grid (kWh) |
| **Solar Panels: Solar Production** | `sensor.<serial>_pv_energy_total` | Total solar power harvested across all MPPTs (kWh) |
| **Battery Systems: Energy going into battery** | `sensor.<serial>_battery_charge_energy_total` | Total energy stored into the battery (kWh) |
| **Battery Systems: Energy coming out of battery** | `sensor.<serial>_battery_discharge_energy_total` | Total energy discharged from the battery (kWh) |
| **Individual Devices (Optional)** | `sensor.<serial>_load_energy_total` | Total house consumption / load energy (kWh) |

> [!TIP]
> Energy statistics in Home Assistant update periodically. After adding these entities to the Energy Dashboard, charts will begin rendering within 1 to 2 hours as hourly data accumulates.

---

## Hardware Wiring & Setup Guide

FoxESS inverters communicate over standard half-duplex RS-485 Modbus. To connect the inverter to Home Assistant, an RS-485 to Ethernet/WiFi bridge (e.g. Waveshare, Elfin EW11/EE11, USR-TCP232) or a direct USB RS-485 dongle is required.

### 1. Inverter RJ45 Port Pinouts

Connect twisted-pair wiring (such as standard Cat5e/Cat6) from your RS-485 bridge to the inverter's communication port:

| Inverter Series | Port Label | Pin 1 | Pin 2 | Pin 3 / 7 | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **KH Series** (Single-Phase Hybrid) | **AUX** or **METER** | **RS-485 A** (Data+) | **RS-485 B** (Data-) | **GND** | *Some hardware batches use Pin 4 (A) / Pin 5 (B)* |
| **H1 / AC1 Series** (Single-Phase) | **COM** | **RS-485 A** (Data+) | **RS-485 B** (Data-) | **GND** | Standard T-568B pair |
| **H3 / AC3 Series** (Three-Phase) | **RS485** / **METER** | **RS-485 A** (Data+) | **RS-485 B** (Data-) | **GND** | Standard T-568B pair |

```text
RJ45 Connector (Pin 1 on far left, locking tab facing downwards/away):
 _________________________________________
|  1  |  2  |  3  |  4  |  5  |  6  |  7  |  8  |
|  A  |  B  | GND |  -  |  -  |  -  | GND |  -  |
|_____|_____|_____|_____|_____|_____|_____|_____|
```

> [!IMPORTANT]
> Always use a dedicated twisted pair for Data+ (A) and Data- (B) to minimize electrical interference from high-frequency inverter switching. If your cable run exceeds 15 meters, enable the 120Ω termination resistor on your RS-485 bridge.

### 2. RS-485 to Ethernet Bridge Settings

When using adapters like the **Waveshare RS485 to RJ45 Ethernet Converter**, **Elfin EW11/EE11**, or **USR-TCP232-410s**, configure the serial interface with the following parameters:

* **Protocol / Mode:** `Modbus TCP to RTU` (or `TCP Server` / `Transparent transfer`)
* **Local Port:** `502`
* **Baud Rate:** `9600` *(standard for AUX/COM; certain LAN firmware builds use `115200`)*
* **Data Bits:** `8`
* **Parity:** `None`
* **Stop Bits:** `1`
* **Flow Control:** `None`
* **Inverter Slave / Unit ID:** `247` *(FoxESS factory default; inspectable via inverter LCD screen)*

### 3. Shared Gateway Friendly (`modbus-connection`)

Unlike legacy integrations that lock the TCP socket exclusively, `foxess_modern` uses Home Assistant's `async_get_unit` connection broker. Multiple integrations (e.g. an Eastron SDM630 meter on Unit 1 and the FoxESS inverter on Unit 247) can share the same physical RS-485 bridge without port contention or packet collisions.

---

## Python Library Installation

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
        print(f"PV3:               {inverter.pv.pv3_voltage} V, {inverter.pv.pv3_power} W")
        print(f"PV4:               {inverter.pv.pv4_voltage} V, {inverter.pv.pv4_power} W")
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
| | `39074` | 16-bit uint | 0.1 | V | PV3 Voltage |
| | `39075` | 16-bit uint | 0.01 | A | PV3 Current |
| | `39283-39284` | 32-bit uint | 1.0 | W | PV3 Power |
| | `39076` | 16-bit uint | 0.1 | V | PV4 Voltage |
| | `39077` | 16-bit uint | 0.01 | A | PV4 Current |
| | `39285-39286` | 32-bit uint | 1.0 | W | PV4 Power |
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

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup instructions, guidelines for adding new FoxESS inverter models, and testing procedures.

## License

This project is licensed under the Apache 2.0 License.
