# Internal Architecture & Anti-Drift Reference

This internal document defines the core architectural invariants for `foxess-modbus` and `foxess_modern`. It exists to prevent code drift and ensure that future modifications do not reintroduce socket desynchronization, UART buffer overruns, or Home Assistant coordinator blackouts.

---

## 1. Architectural Foundations

The integration and device library are built strictly on top of [`modbus-connection`](https://home-assistant-libs.github.io/modbus-connection/), following the modern Home Assistant Modbus architecture (Core 2026.7+).

```text
+-------------------------------------------------------------------------+
|                  Home Assistant Custom Integration                      |
|                     (custom_components/foxess_modern)                   |
|   - Config flow & streamlined options flow                              |
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

## 4. Invariant 3: Official modbus-connection Coordinator Lifecycle

### The Rule
Manage `DataUpdateCoordinator[UpdateReport]`. Count timeouts on the fast poll coordinator and call `await self.device.modbus_unit.disconnect()` after 3 consecutive dead timeouts. Only raise `UpdateFailed` when no sub-system answered or when the link is lost.

### Why This Rule Exists
The official Home Assistant Modbus architecture requires:
1. When `report.updated` contains refreshed sub-systems, those entities update live. Any sub-system that temporarily dropped a frame lands in `report.failed` without failing the overall poll.
2. If the bridge wedges and keeps the socket open while the inverter stops answering, `Device.async_poll` propagates `ModbusTimeoutError` when nothing has answered yet. Counting 3 consecutive timeouts in the fast coordinator and calling `await self.device.modbus_unit.disconnect()` recycles the bridge connection cleanly.
3. Cumulative statistics (`RestoreSensor` with `state_class=TOTAL_INCREASING`) must remain `available = True` so long-term energy history and the Home Assistant Energy Dashboard never have gaps during nightly inverter power-downs.

### The Standard Implementation
```python
async def _async_update_data(self) -> UpdateReport:
    try:
        report: UpdateReport = await self._update_method()
    except ModbusTimeoutError as err:
        if self._is_fast_poll:
            self._timeouts += 1
            if self._timeouts >= 3:
                unit = getattr(self.device, "modbus_unit", None)
                if unit and hasattr(unit, "disconnect"):
                    await unit.disconnect()
        raise UpdateFailed(str(err)) from err
    except ModbusError as err:
        raise UpdateFailed(str(err)) from err

    if self._is_fast_poll:
        self._timeouts = 0

    if not report.updated:
        errors = list(report.failed.values())
        raise UpdateFailed(f"no sub-system answered: {errors[0] if errors else 'unknown'}")

    return report
```

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
* [ ] Does `FoxessDevice` inherit `Device.async_poll` directly without overriding?
* [ ] Does the coordinator recycle the bridge via `self.device.modbus_unit.disconnect()` after 3 consecutive dead timeouts?
* [ ] Do cumulative energy sensors (`RestoreSensor`) maintain `available = True`?
* [ ] Do all 35 tests in `pytest tests/` pass?
