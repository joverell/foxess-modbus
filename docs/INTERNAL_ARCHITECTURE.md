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
Always use `modbus-connection` and Home Assistant Core Modbus unit leasing:
```python
from homeassistant.components.modbus import async_get_unit
from modbus_connection import ModbusTcpParams

params = ModbusTcpParams(host=host, port=port)
unit = async_get_unit(hass, entry, params, unit_id)
unit.set_message_spacing(0.30)  # 300ms RS-485 bus pacing for FoxESS AUX UART line decay
unit.require_connect_delay(0.05)   # 50ms transceiver line stabilization
unit.require_timeout(5.0)
```

For standalone or test environments where Core Modbus is not present, `create_connection` instantiates a standalone `ModbusConnection`:
```python
from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

params = ModbusTcpParams(host=host, port=port)
connection = ModbusConnection(
    params,
    timeout=5.0,
    message_spacing=0.30,  # 300ms RS-485 bus pacing for FoxESS AUX UART
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

## 4. Invariant 3: Official modbus-connection Coordinator Lifecycle & Debouncing

### The Rule
Manage `DataUpdateCoordinator[UpdateReport]`. Track consecutive timeouts across both fast (`readings_coordinator`) and slow (`settings_coordinator`) polling loops. Debounce transient timeouts (`self._timeouts < 2 and self.data is not None`) so that entity availability does not flap. Recycle the bridge link via `await self.device.modbus_unit.disconnect()` after 3 consecutive dead timeouts. Only raise `UpdateFailed` when no sub-system answered or when the link is lost.

### Why This Rule Exists
1. **Sub-System Fault Isolation**: When `report.updated` contains refreshed sub-systems, those entities update live. Any sub-system that temporarily dropped a frame lands in `report.failed` without failing the overall poll.
2. **Slow Coordinator Availability Continuity**: `settings_coordinator` polls on a 60-second cycle (`SETTINGS_SCAN_INTERVAL = 60`). If debouncing is only applied to fast poll, a single dropped Wi-Fi packet on the 60-second settings poll causes all configuration entities (`number.export_power_limit`, `number.min_soc`, `select.work_mode`) to flap to `Unavailable` for a full 60 to 120 seconds. Applying `self._timeouts < 2 and self.data is not None` to all coordinators ensures configuration entities remain stable across transient link hiccups.
3. **Bridge Recycling**: If the serial bridge wedges and keeps the TCP socket open while the inverter stops responding, counting 3 consecutive timeouts and calling `await self.device.modbus_unit.disconnect()` forces the TCP socket to close and re-establish cleanly.
4. **Cumulative Statistics Continuity**: Cumulative energy sensors (`RestoreSensor` with `state_class=TOTAL_INCREASING`) must maintain `available = True` so long-term energy history and the Home Assistant Energy Dashboard never have gaps during nightly inverter power-downs.
5. **Connection Status Debouncing**: The diagnostic `sensor.connection_status` entity reports state based on `timeouts < 3`. Rather than flipping to `Disconnected` whenever a single read cycle times out or during a 20-second self-healing TCP socket reconnect, it maintains `Connected` until 3 consecutive failed cycles occur. This shields the Home Assistant logbook from transient disconnect noise while accurately reflecting true link outages.

### The Standard Implementation
```python
@property
def is_available(self) -> bool:
    """Return True if coordinator successfully updated data or within transient tolerance."""
    if self._timeouts < 2 and self.data is not None:
        # Tolerate transient poll timeouts on Wi-Fi without flapping entity availability
        return True
    return self.last_update_success

async def _do_update_data(self) -> UpdateReport:
    """Execute update method and handle errors."""
    try:
        report: UpdateReport = await self._update_method()
    except ModbusTimeoutError as err:
        self._timeouts += 1
        if self._timeouts >= 3:
            unit = getattr(self.device, "modbus_unit", None)
            if unit and hasattr(unit, "disconnect"):
                _LOGGER.warning(
                    "Link unresponsive after %d consecutive timeouts: recycling Modbus connection",
                    self._timeouts,
                )
                await unit.disconnect()
        raise UpdateFailed(str(err)) from err
    except ModbusError as err:
        raise UpdateFailed(str(err)) from err
    except Exception as err:
        raise UpdateFailed(f"Unexpected error communicating with FoxESS: {err}") from err

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

## 6. Invariant 5: Zero-Drift Specification Enforcement

### The Rule
The standalone PyPI library package (`src/foxess_modbus/`) and the vendored Home Assistant custom integration device layer (`custom_components/foxess_modern/device/`) must maintain 100% logical parity at all times.

### Why This Rule Exists
Custom integrations require vendored code so that HACS users can run without installing external binary wheels or waiting for upstream PyPI releases. However, maintaining two disconnected copies inevitably leads to subtle drift where bug fixes or register additions exist in one copy but not the other.

### How It Is Enforced
Zero drift is verified continuously:
1. `python scripts/vendor.py --check` runs in CI (`.github/workflows/pytest.yaml`) and verifies byte-for-byte synchronization. `python scripts/vendor.py --sync` propagates modifications from `src/` to `custom_components/`.
2. The automated unit test `tests/test_modbus_connection_spec.py::test_zero_drift_library_and_integration_spec` asserts identical logic across all Python files.

All inverter classes (`FoxessKH10Inverter`, `FoxessH1Inverter`, `FoxessH3Inverter`, `FoxessH3ProInverter`) must inherit from `FoxessDevice` and implement the four standard lifecycle methods:
* `async_update_readings() -> UpdateReport`
* `async_update_settings() -> UpdateReport`
* `async_update() -> UpdateReport`
* `async_read_raw(names: Iterable[str] | None = None) -> Raw`

---

## 7. Invariant 6: Physical Units & Statistics Integrity

### The Rule
Strictly separate instantaneous power entities from cumulative energy entities in device models, entity descriptions, and migration alias mappings:
* **Power Entities**:
  * Unit: `W`
  * Device Class: `SensorDeviceClass.POWER`
  * State Class: `SensorStateClass.MEASUREMENT`
  * Statistics Calculation: Arithmetic mean (`has_mean: True`, `has_sum: False`)
* **Cumulative Energy Entities**:
  * Unit: `kWh`
  * Device Class: `SensorDeviceClass.ENERGY`
  * State Class: `SensorStateClass.TOTAL_INCREASING` (or `TOTAL`)
  * Statistics Calculation: Sum accumulation (`has_mean: False`, `has_sum: True`)

### Strict Migration Alias Separation
In `migration.py`, never mix power and energy aliases. For example:
* `battery_charge` and `battery_discharge` in legacy integrations tracked instantaneous power (kW).
* `battery_charge_total` and `battery_discharge_total` tracked cumulative energy (kWh).
Mapping `battery_charge` into `battery_charge_energy_total` creates inverted units in the recorder metadata and triggers Home Assistant `units_changed` and `mean_type_changed` repairs dialogs.

---

## 8. Invariant 7: Options Flow & Form Standards

### The Rule
Always use `homeassistant.helpers.selector.SelectSelector` with string values and human-readable option labels for dropdowns in config flows and options flows. Never use `vol.In` with raw integer lists.

### Why This Rule Exists
Home Assistant frontend web components compare radio and dropdown selections as strings (`item.value === this.value`). When a schema defines options as raw integers (`[5, 10, 15, 30, 60]`), JavaScript string-to-number type mismatches cause all options to render unselected, forcing the user to re-select a value manually on every save.

### The Standard Implementation
```python
interval_options = [
    selector.SelectOptionDict(value="5", label="5 seconds"),
    selector.SelectOptionDict(value="10", label="10 seconds"),
    selector.SelectOptionDict(value="15", label="15 seconds (Recommended)"),
    selector.SelectOptionDict(value="30", label="30 seconds"),
    selector.SelectOptionDict(value="60", label="60 seconds"),
]
curr_str = str(current_scan_interval)
if not any(opt["value"] == curr_str for opt in interval_options):
    interval_options.append(selector.SelectOptionDict(value=curr_str, label=f"{curr_str} seconds"))

schema_dict = {
    vol.Optional(CONF_SCAN_INTERVAL, default=curr_str): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=interval_options,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )
}
```
All optional fields, such as `reconfigure_legacy_mappings`, must have explicit labels in `strings.json` and `translations/en.json`.

---

## 9. Invariant 8: Half-Duplex Bus Locking and Frame Spacing

### The Rule
Enforce complete serialization of all Modbus transactions across all coordinators and UI write commands on the shared RS-485 bus. Maintain a minimum of 300 ms (`message_spacing = 0.30`) inter-frame spacing with adaptive scaling to 450 ms (`0.45s`) on transient timeouts, and configure a minimum 5.0 second timeout for all read blocks.

### Why This Rule Exists
1. **Half-Duplex Contention**: RS-485 serial communication is inherently half-duplex. If `readings_coordinator` (15s fast poll) and `settings_coordinator` (60s slow poll) attempt to communicate concurrently without locking, packets collide on the serial line, causing corrupted frames and timeout spikes.
2. **Inverter Calculation Latency & Microcontroller Buffer Overrun**: FoxESS KH10 inverters asynchronously compute readings across 4 MPPT strings, high-voltage battery modules, and grid telemetry. When polled faster than 300 ms, the inverter AUX microcontroller cannot service register requests before the next poll arrives, causing RS-485 bridges to return `Transaction ID: 0` error packets or drop responses. An inter-frame spacing of 300 ms (backed off to 450 ms during retries) prevents FIFO buffer overflow and hardware UART deadlocks.
3. **Multi-Block Timeout Budgeting**: Because register queries are segmented into blocks of at most 8 registers, a full poll cycle requires sequential block transactions. Sizing Modbus connection timeouts to at least 5.0 seconds provides sufficient margin for sequential multi-block responses over Wi-Fi bridge hops.

### How It Is Enforced
* Connection leasing via `async_get_unit` shares a single `modbus-connection` unit lease across coordinators.
* `ModbusConnection` parameters in `device/__init__.py` and fallback connection initializers specify `message_spacing = 0.30` and `timeout = 5.0`.
* In `coordinator.py`, coordinator updates sequence through `_do_update_data`, ensuring bus queries are dispatched sequentially, with adaptive spacing scaling to 450 ms during transient errors.

---

## 10. Invariant 9: PyPI Distribution Package Naming (foxess-modern)

### The Rule
The standalone PyPI library distribution package name is `foxess-modern`, while the internal Python import namespace remains `foxess_modbus`.

### Why This Rule Exists
1. **Namespace Collision Avoidance**: The package name `foxess-modbus` is already registered on the public PyPI index by legacy publishers.
2. **Trusted Publisher Alignment**: Automated deployment via GitHub Actions uses PyPI Trusted Publishing configured for project `foxess-modern`.
3. **Import Compatibility**: The internal module namespace `foxess_modbus` is retained in `src/foxess_modbus/` to maintain clean separation between the packaging distribution name and code imports.

### Configuration
In `pyproject.toml`:
```toml
[project]
name = "foxess-modern"
```
And package discovery:
```toml
[tool.setuptools.packages.find]
where = ["src"]
```

### Trusted Publishing Pipeline
Automated publishing is defined in `.github/workflows/publish.yml` using OpenID Connect (OIDC) Trusted Publishing:
1. Gated verification runs first: verifies byte-for-byte dual-tree synchronization (`python scripts/vendor.py --check`) and passes all 53 unit tests.
2. Build stage creates sdist and wheel packages, validated with `twine check`.
3. Release job publishes artifacts directly to PyPI with provenance attestations without requiring long-lived API tokens.

---

## 11. Invariant 10: Opportunistic Core Modbus Leasing with Standalone Autonomy

### The Rule
Never declare `"dependencies": ["modbus"]` in `manifest.json`. Always declare `"after_dependencies": ["modbus"]` and implement opportunistic connection leasing via `async_get_modbus_unit`. If Core Modbus is active, lease the shared unit; if absent or unconfigured, fall back seamlessly to standalone `modbus-connection` without generating false-alarm Repair issues.

### Why This Rule Exists
1. **The Manifest Hard Dependency Failure**: Declaring `"dependencies": ["modbus"]` forces Home Assistant's component loader to verify that Core `modbus` has successfully started before loading `foxess_modern`. In Home Assistant Core 2026.9, Core `modbus` requires a manual `modbus:` block in `configuration.yaml`. If unconfigured, Home Assistant halts integration setup (`(!) Not loaded`), breaking GUI installations.
2. **The `after_dependencies` Solution**: Declaring `"after_dependencies": ["modbus"]` guarantees that IF Core Modbus is configured in YAML, Home Assistant initializes it before `foxess_modern`. If Core Modbus is NOT configured, Home Assistant proceeds to load `foxess_modern` without blocking.
3. **Automated Transition & Zero-YAML Autonomy**: Standalone mode is the primary, zero-YAML mode for FoxESS installations with dedicated serial gateways. If a user later chooses to add `modbus:` to `configuration.yaml` for multi-integration RS-485 sharing, `async_setup_entry` automatically discovers the Core Modbus hub and leases Unit 247, while also programmatically cleaning up any legacy Repairs advisory issues (`ir.async_delete_issue`). All entity IDs, unique IDs, and historical energy statistics remain 100% continuous.

---

## 12. Invariant 11: Multi-Version Upstream Library Compatibility (`Device`, `Raw`, `UpdateReport`)

### The Rule
Never import `Device`, `Raw`, or `UpdateReport` directly from `modbus_connection.model`. Always route imports through `foxess_modbus.model`, which encapsulates multi-stage fallbacks across `modbus_connection.model`, submodules (`modbus_connection.model.device`, `modbus_connection.model._const`), and native fallbacks.

### Why This Rule Exists
Home Assistant Core containers pin specific minor versions of upstream libraries. In Core 2026.9.3, Core pins `modbus-connection==4.10.0`. In version 4.10.0, `Device`, `Raw`, and `UpdateReport` were located in submodules rather than re-exported from `modbus_connection.model.__init__.py` (which was introduced in version 4.11.0+). Because Home Assistant restricts custom integrations from mutating Core's pinned container packages, attempting an unqualified top-level import raises `ImportError: cannot import name 'Device' from 'modbus_connection.model'` during cold reboot, crashing integration setup.

---

## 13. Summary Checklist for Code Reviews

Before merging changes to `src/` or `custom_components/foxess_modern/`:
* [ ] Does the change use Core Modbus unit leasing (`async_get_unit`) with fallback to `modbus_connection.tmodbus.ModbusConnection`?
* [ ] Are all block read counts strictly `<= 8`?
* [ ] Is `message_spacing` kept at `0.30` (300ms RS-485 transceiver decay and KH10 calculation margin)?
* [ ] Does `FoxessDevice` inherit `Device.async_poll` directly without overriding?
* [ ] Does the coordinator recycle the bridge via `self.device.modbus_unit.disconnect()` after 3 consecutive dead timeouts?
* [ ] Is `is_available` debounced (`self._timeouts < 2 and self.data is not None`) across all coordinators?
* [ ] Is `sensor.connection_status` debounced (`self._coordinator._timeouts < 3`) to prevent logbook flapping?
* [ ] Do cumulative energy sensors (`RestoreSensor`) maintain `available = True`?
* [ ] Are power entities (`W`) and energy entities (`kWh`) strictly separated in migration aliases?
* [ ] Does the options flow use `SelectSelector` with string values and pre-selected defaults?
* [ ] Is the PyPI distribution package name configured as `foxess-modern`?
* [ ] Are manifest dependencies configured as `"after_dependencies": ["modbus"]` (never hard `"dependencies"`)?
* [ ] Are `UpdateReport` imports sourced via `foxess_modbus.model` for container compatibility?
* [ ] Are `src/foxess_modbus/` and `custom_components/foxess_modern/device/` 100% synchronized via `python scripts/vendor.py --check`?
* [ ] Do all tests in `pytest tests/` pass?


