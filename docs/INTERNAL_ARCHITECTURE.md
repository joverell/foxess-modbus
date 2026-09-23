# Internal Architecture & Anti-Drift Reference

This internal document defines the core architectural invariants for `foxess-modbus` and `foxess_modern`. It exists to prevent code drift and ensure that future modifications do not reintroduce socket desynchronization, UART buffer overruns, or Home Assistant coordinator blackouts.

---

## 1. Architectural Foundations

The integration and device library are built strictly on top of [`modbus-connection`](https://home-assistant-libs.github.io/modbus-connection/), following the modern Home Assistant Modbus architecture (Core 2026.7+).

```text
+-------------------------------------------------------------------------+
|                  Home Assistant Custom Integration                      |
|                     (custom_components/foxess_modern)                   |
|   - Config flow & options flow                                          |
|   - DataUpdateCoordinator[UpdateReport]                                 |
|   - CoordinatorEntity instances (sensor, number, select)                |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                      Python Device Library                              |
|                       (src/foxess_modbus)                               |
|   - Typed Inverter classes (FoxessKH10Inverter, FoxessH1Inverter, etc.) |
|   - Typed Component definitions (PV, Battery, Grid, BMS, Control)       |
|   - Declarative register layouts with register_ranges & max_span        |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                       modbus-connection (PyPI)                          |
|   - Abstract ModbusConnection & ModbusUnit Protocol                     |
|   - Asynchronous tmodbus backend                                        |
|   - Automatic MBAP Transaction ID (TID) tracking and frame validation   |
|   - Inter-packet pacing (message_spacing) and settle delays             |
+-------------------------------------------------------------------------+
```

---

## 2. Invariant 1: No Custom Raw Sockets

### The Rule
Never implement raw Python `socket.socket` wrappers or ad-hoc TCP connections in `connection.py` or elsewhere.

### Why This Rule Exists
Industrial serial-to-Ethernet gateways (such as Waveshare, USR-W610, and Elfin EW11) translate Modbus TCP packets from the network into half-duplex RS-485 Modbus RTU signals. When an ad-hoc TCP socket encounters a transient timeout or frame hiccup:
1. Retaining an unpurged raw socket leaves trailing response bytes in the TCP receive buffer.
2. Subsequent requests immediately read those stale bytes as their own MBAP headers.
3. Every subsequent read fails with frame desynchronization, triggering a cascade failure across all sub-systems.

### The Standard Implementation
Always use `modbus_connection.tmodbus.ModbusConnection`:
```python
from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

params = ModbusTcpParams(host=host, port=port)
connection = ModbusConnection(
    params,
    timeout=2.5,
    message_spacing=0.1,  # 100ms RS-485 bus pacing for FoxESS AUX UART
    connect_delay=0.05,   # 50ms transceiver line stabilization
)
unit = connection.for_unit(unit_id)
```
`tmodbus` provides native MBAP transaction tracking, identifies corrupt replies, raises `ModbusDesyncError` for out-of-order replies, and allows clean bridge recycling via `await unit.disconnect()`.

---

## 3. Invariant 2: Hardware Microcontroller Protection (`max_span <= 8`)

### The Rule
Never allow a single Modbus read frame to exceed 8 contiguous registers (`count <= 8`). Always enforce `max_span = 8` and explicit `register_ranges` where registers cluster.

### Why This Rule Exists
FoxESS hybrid inverters (particularly the KH and H1 series) route AUX port communication through a dedicated microcontroller with a bounded UART FIFO buffer:
* Reading up to 8 contiguous registers executes reliably and responds within 40ms.
* Requesting 10 or more contiguous registers in a single frame (such as `addr=31006 count=11`) overflows the microcontroller FIFO buffer, stalling the serial interface and resulting in dropped packets or corrupted bytes.

### The Standard Implementation
In sub-system components, bound contiguous ranges explicitly:
```python
class FoxessKH10Grid(FoxessComponent):
    register_space = "holding"
    register_ranges = ((31006, 31013), (31014, 31016), (39168, 39169))
    max_span = 8
```
This guarantees that `modbus-connection`'s read planner will never merge requests into frames wider than 8 registers.

---

## 4. Invariant 3: UpdateReport-Driven Coordinator Lifecycle

### The Rule
Never raise `UpdateFailed` on individual sub-system read failures. Only sustained, complete communication loss should ever raise `UpdateFailed`.

### Why This Rule Exists
Home Assistant Core's `DataUpdateCoordinator` has a built-in behavior:
1. When `UpdateFailed` is raised, `coordinator.last_update_success` becomes `False`.
2. Any `CoordinatorEntity` checking `super().available` immediately transitions to `unavailable`.
3. Home Assistant Core imposes a mandatory 60-second retry backoff timer.
4. If an integration raises `UpdateFailed` because 1 non-critical sub-system (such as BMS) dropped a frame, all 45 entities stay marked `unavailable` for a full 60 seconds even though the inverter was healthy.

### The Standard Implementation
1. The coordinator stores `DataUpdateCoordinator[UpdateReport]`.
2. Partial reads return the report so active sub-systems update cleanly.
3. Entities bind availability to their specific sub-system report name:
   ```python
   @property
   def available(self) -> bool:
       return self.coordinator.is_available
   ```
4. If a serial bridge wedges, call `await unit.disconnect()` after 3 consecutive failures to reset the TCP socket cleanly.
5. Only raise `UpdateFailed` after sustained failure (e.g. 8 consecutive failed cycles = 80 to 120 seconds of continuous carrier loss).

---

## 5. Invariant 4: Verified KH Register Definitions

### The Rule
Only declare registers physically implemented by the inverter firmware.

### Verified KH Hybrid Register Boundaries
* **Grid Telemetry**: 31006 to 31016 (Holdings, Function Code 3)
* **Battery & Operating State**: 31020 to 31027 (Holdings, Function Code 3)
  * Note: Operating state (31027) MUST be read alongside 31020..31026 as an 8-register block; reading 31027 in isolation times out on KH firmware.
* **Inverter Temperatures**: 31018 to 31019 (Holdings, Function Code 3)
* **PV Strings**: 39070 to 39077 (Voltages/Currents), 39279 to 39286 (Powers)
* **BMS Telemetry**: 37617 to 37624, and 37632 (Function Code 3)
* **Energy Counters**: 32000 to 32023 (Function Code 3)
* **Firmware Versions**: 36001 to 36003 (Function Code 3)
* **Control Registers**:
  * Work Mode: 41000
  * Max Charge Current: 41007
  * Min SoC: 41009
  * Max SoC: 41010
  * Min SoC on Grid: 41011
  * Import Power Limit: 46501 (int32)
  * Export Power Limit: 46616 (int32)
  * Remote Power Control: 44000 to 44002

*Do not poll register 41008 on KH models (it does not exist and causes read failures).*

---

## 6. Summary Checklist for Code Reviews

Before merging changes to `src/` or `custom_components/foxess_modern/`:
* [ ] Does the change use `modbus_connection.tmodbus.ModbusConnection`?
* [ ] Are all block read counts strictly `<= 8`?
* [ ] Is `message_spacing` kept at `>= 0.08` (recommended: 0.1s)?
* [ ] Does `_async_update_data()` return prior telemetry across transient glitches rather than throwing `UpdateFailed`?
* [ ] Do all 35 tests in `pytest tests/` pass?
