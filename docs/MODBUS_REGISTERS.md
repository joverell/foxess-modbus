# FoxESS Modbus Register Reference

This document provides a comprehensive technical register map for FoxESS Hybrid Inverters supported by FoxESS Modern, covering the **KH Series**, **H1 / AC1 Series**, and **H3 / H3-Pro Series**.

---

## 1. Overview & Protocol Notes

* Communication Parameters: 9600 Baud, 8 Data Bits, 1 Stop Bit, No Parity (8N1).
* Default Slave Unit ID: 247 (0xF7).
* Register Types:
  * Input Registers (Read-Only, Function Code 0x04): Typically mapped in the 30000 range.
  * Holding Registers (Read/Write, Function Codes 0x03, 0x06, 0x10): Typically mapped in the 40000 range. On FoxESS hardware, many telemetry metrics in the 31000 range are accessible via holding register calls.
* Big-Endian Word Order: 32-bit values are transferred as two sequential 16-bit registers (High word first, Low word second).
* Two's Complement Signed Values: Power flows, temperatures, and battery currents are encoded as signed 16-bit or 32-bit integers.

---

## 2. Telemetry Registers: Single-Phase Inverters (KH Series & H1 / AC1)

### 2.1 PV Array Telemetry

| Register | Name | KH Series | H1 / AC1 | Scale | Signed | Unit | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **31000** | PV1 Voltage | Yes | Yes | 0.1 | No | V | PV String 1 DC voltage |
| **31001** | PV1 Current | Yes | Yes | 0.1 | Yes | A | PV String 1 DC current |
| **31002** | PV1 Power | Yes | Yes | 1.0 | Yes | W | Calculated or instantaneous String 1 power |
| **31003** | PV2 Voltage | Yes | Yes | 0.1 | No | V | PV String 2 DC voltage |
| **31004** | PV2 Current | Yes | Yes | 0.1 | Yes | A | PV String 2 DC current |
| **31005** | PV2 Power | Yes | Yes | 1.0 | Yes | W | Calculated or instantaneous String 2 power |
| **31039** | PV3 Voltage | Yes (4-MPPT) | No | 0.1 | No | V | PV String 3 DC voltage (KH models) |
| **31040** | PV3 Current | Yes (4-MPPT) | No | 0.1 | Yes | A | PV String 3 DC current (KH models) |
| **31041** | PV3 Power | Yes (4-MPPT) | No | 1.0 | Yes | W | PV String 3 power |
| **31042** | PV4 Voltage | Yes (4-MPPT) | No | 0.1 | No | V | PV String 4 DC voltage (KH models) |
| **31043** | PV4 Current | Yes (4-MPPT) | No | 0.1 | Yes | A | PV String 4 DC current (KH models) |
| **31044** | PV4 Power | Yes (4-MPPT) | No | 1.0 | Yes | W | PV String 4 power |

### 2.2 Grid & Load Telemetry

| Register | Name | KH Series | H1 / AC1 | Scale | Signed | Unit | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **31006** | Grid Voltage | Yes | Yes | 0.1 | No | V | AC Grid line voltage |
| **31007** | Inverter Current | Yes | Yes | 0.1 | Yes | A | AC output current |
| **31008** | Inverter Power | Yes | Yes | 1.0 | Yes | W | Total AC output power |
| **31009** | Grid Frequency | Yes | Yes | 0.01 | No | Hz | AC grid frequency |
| **31014** | Grid CT Meter Power | No | Yes | 1.0 | Yes | W | Signed: +export to grid, -import from grid |
| **31015** | CT2 Meter Power | Yes | No | -1.0 | Yes | W | Secondary CT (external PV, generator) |
| **31016** | House Load Power | Yes | Yes | 1.0 | Yes | W | Domestic load power consumption |
| **39168 - 39169** | Grid CT Active Power | Yes (32-bit) | No | 1.0 | Yes | W | 32-bit signed: +export to grid, -import from grid |

### 2.3 Emergency Power Supply (EPS) Telemetry

| Register | Name | KH Series | H1 / AC1 | Scale | Signed | Unit | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **31010** | EPS Voltage | Yes | Yes | 0.1 | No | V | Off-grid backup output voltage |
| **31011** | EPS Current | Yes | Yes | 0.1 | Yes | A | Off-grid backup load current |
| **31012** | EPS Power | Yes | Yes | 1.0 | Yes | W | Active power delivered to EPS circuit |
| **31013** | EPS Frequency | Yes | Yes | 0.01 | No | Hz | Output frequency during backup operation |
| **31014** | EPS Reactive Power | Yes | No | 1.0 | Yes | var | Reactive power on EPS circuit |

### 2.4 Battery Management System (BMS) Telemetry

| Register | Name | KH Series | H1 / AC1 | Scale | Signed | Unit | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **31020** | Battery Voltage | Yes | Yes | 0.1 | No | V | Battery pack DC terminal voltage |
| **31021** | Battery Current | Yes | Yes | 0.1 | Yes | A | Pack current: +discharge, -charge |
| **31022** | Battery Power | Yes | Yes | 1.0 | Yes | W | Pack power: +discharge, -charge |
| **31023** | Battery Temperature | Yes | Yes | 0.1 | Yes | deg C | Internal BMS cell temperature |
| **31024** | Battery SoC | Yes | Yes | 1.0 | No | % | Current state of charge (0 to 100%) |
| **31025** | BMS Max Charge Current | Yes | No | 0.1 | No | A | Dynamic BMS charge current limit |
| **31026** | BMS Max Discharge Current | Yes | No | 0.1 | No | A | Dynamic BMS discharge current limit |

### 2.5 Inverter Health & Versions

| Register | Name | KH Series | H1 / AC1 | Scale | Signed | Unit | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **31018** | Inverter Temperature | Yes | Yes | 0.1 | Yes | deg C | Internal heatsink temperature |
| **31019** | Ambient Temperature | Yes | Yes | 0.1 | Yes | deg C | Internal ambient enclosure temperature |
| **31027** | Operating State | Yes | Yes | 1.0 | No | - | 0: Waiting, 1: Checking, 2: On-Grid, 3: Off-Grid/EPS, 4: Fault |
| **30016 / 36001** | Master Firmware Version | Yes | Yes | 1.0 | No | - | Master controller firmware (e.g. 133 = v1.33) |
| **30017 / 36002** | Slave Firmware Version | Yes | Yes | 1.0 | No | - | Slave controller firmware (e.g. 100 = v1.00) |
| **30018 / 36003** | Manager Firmware Version | Yes | Yes | 1.0 | No | - | Manager controller firmware (e.g. 115 = v1.15) |

---

## 3. Telemetry Registers: Three-Phase Inverters (H3 & H3-Pro Series)

### 3.1 AC Three-Phase Grid Telemetry

| Register | Name | Phase | Scale | Signed | Unit | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **31006** | Grid Voltage Phase R | R (Phase 1) | 0.1 | No | V | Line voltage Phase R |
| **31007** | Grid Voltage Phase S | S (Phase 2) | 0.1 | No | V | Line voltage Phase S |
| **31008** | Grid Voltage Phase T | T (Phase 3) | 0.1 | No | V | Line voltage Phase T |
| **31009** | Grid Current Phase R | R (Phase 1) | 0.1 | Yes | A | AC current Phase R |
| **31010** | Grid Current Phase S | S (Phase 2) | 0.1 | Yes | A | AC current Phase S |
| **31011** | Grid Current Phase T | T (Phase 3) | 0.1 | Yes | A | AC current Phase T |
| **31012** | Grid Power Phase R | R (Phase 1) | 1.0 | Yes | W | Active power Phase R |
| **31013** | Grid Power Phase S | S (Phase 2) | 1.0 | Yes | W | Active power Phase S |
| **31014** | Grid Power Phase T | T (Phase 3) | 1.0 | Yes | W | Active power Phase T |
| **31015** | Grid Frequency | All | 0.01 | No | Hz | AC grid frequency |

### 3.2 Three-Phase EPS Telemetry

| Register | Name | Phase | Scale | Signed | Unit | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **31022** | EPS Power Phase R | R (Phase 1) | 1.0 | Yes | W | Active backup power Phase R |
| **31023** | EPS Power Phase S | S (Phase 2) | 1.0 | Yes | W | Active backup power Phase S |
| **31024** | EPS Power Phase T | T (Phase 3) | 1.0 | Yes | W | Active backup power Phase T |
| **31025** | EPS Frequency | All | 0.01 | No | Hz | Backup output frequency |

---

## 4. Control & Configuration Registers (Holding Registers)

These registers are writable and manage operating modes, reserve limits, and active power overrides.

| Register | Name | Allowed Values | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| **41000** | Work Mode | 0, 1, 2, 4 | 0 | 0: Self Use, 1: Feed-in First, 2: Back-up, 4: Peak Shaving |
| **41007** | Max Charge Current | Model dependent | Max | Maximum charging current in Amperes (scale 0.1) |
| **41008** | Max Discharge Current | Model dependent | Max | Maximum discharging current in Amperes (scale 0.1; supported on H1/H3, not implemented on KH series) |
| **41009** | Min SoC | 10 to 100 | 10 | Minimum battery reserve percentage on grid (%) |
| **41010** | Max SoC | 10 to 100 | 100 | Maximum battery charge cutoff percentage (%) |
| **41011** | Min SoC (On Grid) | 10 to 100 | 10 | Minimum reserve limit while on grid |
| **44000** | Remote Enable | 0, 1 | 0 | 0: Normal autonomous control, 1: Enable remote active power override |
| **44001** | Remote Timeout | 1 to 86400 | 3600 | Override watchdog timeout in seconds |
| **44002** | Remote Active Power | -30000 to +30000 | 0 | Target power in Watts. Negative = Force Charge from grid, Positive = Force Discharge |

---

## 5. Acknowledgements & Community References

This register reference is compiled from official FoxESS Modbus Protocol Guides and informed by extensive community research from open source projects:

* **Nathan Marlor's foxess_modbus**: [nathanmarlor/foxess_modbus on GitHub](https://github.com/nathanmarlor/foxess_modbus)
  Original multi-generation FoxESS integration for Home Assistant, providing pioneering work in reverse engineering register boundaries across H1, H3, and KH models.
* **Robert Saemann's HA-FoxESS-H3-Modbus**: [rsaemann/HA-FoxESS-H3-Modbus on GitHub](https://github.com/rsaemann/HA-FoxESS-H3-Modbus)
  Dedicated three-phase H3 Modbus integration, offering deep insights into Phase R/S/T meter power balancing and three-phase EPS telemetry.
* **Official FoxESS Modbus Protocol Specifications**: V1.02, V1.05, and V1.80 protocol documentation from FoxESS Co., Ltd.
