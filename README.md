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
- **Inverter Microcontroller Protection**: Automatically groups and limits register reads (`max_span = 8`) to prevent the FoxESS AUX microcontroller UART FIFO buffer from overflowing and stalling.
- **Resilient Bus Timing & Debouncing**: Enforces 300ms RS-485 inter-frame pacing with adaptive backoff to 450ms during transient timeouts. Telemetry and connection status sensors are debounced to absorb isolated packet loss without flapping in the Home Assistant logbook.
- **Shared Gateway Friendly**: Designed to operate with Home Assistant's `async_get_unit` connection broker. Multiple integrations and meters (e.g. Eastron, heat pumps) can share the same physical RS-485 bridge without bus collisions.
- **Configurable Polling Interval**: User-selectable scan rate (5s, 10s, 15s, 30s, 60s; default is **15s**) configured directly in Options.
- **First-Class Predbat Automation**: Native signed net grid power sensor (+export, -import) and dedicated services for force charging, force discharging, clearing overrides, and setting work modes using remote active power registers to avoid solar curtailment.
- **Dynamic Power Scaling**: Scales power limits dynamically up to 30,000 W for commercial H3-Pro systems.
- **Multi-Model EPS Telemetry**: Real-time backup power, voltage, current, and frequency monitoring across single-phase and three-phase inverters.
- **Strongly Typed**: Registers and coils map to typed Python properties with automatic endianness and scale factor decoding.
- **Standalone PyPI Distribution**: Published as `foxess-modern` on PyPI via GitHub Actions Trusted Publishing, maintaining 100% synchronization with the vendored Home Assistant custom integration.
- **Fully Tested**: Tested with mock in-memory Modbus backends and automated zero-drift compliance tests.

---

## Supported Inverter Models

| Series | Models | Strings / Trackers | Interface | Modbus Type | Register Set |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **H3-Pro Series** | H3-Pro-15.0 to H3-Pro-30.0 | **6 Strings** (PV1-PV6 across 3 MPPTs) | RS485 / LAN | Modbus TCP / RTU | Holding Registers (Commercial) |
| **KH Series** | KH7, KH8, KH9, KH10, KH10.5 | **4 Strings** (PV1-PV4 across 4 MPPTs) | AUX / LAN | Modbus TCP / RTU | Holding Registers (1.33+) |
| **H3 / AC3 Series** | H3-5.0 to H3-12.0, AC3, AIO-H3 | **2 Strings** (PV1-PV2 across 2 MPPTs) | RS485 / LAN | Modbus TCP / RTU | Holding Registers (Three-Phase) |
| **H1 / AC1 Series** | H1-3.0 to H1-6.0, AC1, AIO-H1 | **2 Strings** (PV1-PV2 across 2 MPPTs) | AUX / LAN | Modbus TCP / RTU | Holding Registers |

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

Navigate to **Settings > Dashboards > Energy** and configure the fields as follows:

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

## Documentation & Detailed Guides

To maintain a clean, user-focused overview on the front page, technical implementation details and wiring references have been organized into dedicated documentation files:

* **[Hardware Setup & Field Observations Guide](docs/HARDWARE_SETUP.md)**: Detailed RJ45 and 16-pin connector pinouts, RS-485 bridge configuration (Waveshare, USR, Elfin), Wi-Fi Faraday cage mitigations, UDP fallback, and the complete two-tier power-cycle recovery protocol.
* **[Internal Architecture & Anti-Drift Reference](docs/INTERNAL_ARCHITECTURE.md)**: Architectural invariants, bounded frame rules (`max_span = 8`), coordinator lifecycle standards, units and statistics integrity, and zero-drift spec enforcement.
* **[Predbat Integration Guide](docs/PREDBAT_INTEGRATION.md)**: Drop-in `apps.yaml` configuration, signed native net grid power explanation, service automation triggers, and details on preventing solar curtailment via remote active power control.
* **[Modbus Register Map Reference](docs/MODBUS_REGISTERS.md)**: Comprehensive multi-family register reference across KH, H1/AC1, and H3/H3-Pro models, including telemetry, EPS, and holding registers.
* **[Migration Guide from Legacy foxess_modbus](docs/MIGRATION_GUIDE.md)**: Step-by-step instructions for transitioning from Nathan Marlor's integration with zero data loss, automated entity mapping, and statistics validation.

---

## Python Library Installation

```bash
pip install "foxess-modern"
```

To include the high-performance async `tmodbus` backend:

```bash
pip install "foxess-modern[tmodbus]"
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
    connection = ModbusConnection(params, timeout=5.0, message_spacing=0.30)

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

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup instructions, guidelines for adding new FoxESS inverter models, and testing procedures.

## License

This project is licensed under the Apache 2.0 License.
