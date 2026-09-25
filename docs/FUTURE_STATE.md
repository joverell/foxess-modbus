# FoxESS Modern Architecture: Expected Future State & Evolution Roadmap

A living technical reference tracking architectural targets, upstream Home Assistant alignment milestones, and the roadmap for reducing custom transport dependencies.

---

## 1. Architectural Vision & Objective

The primary architectural goal for `foxess_modern` is full alignment with Home Assistant's official modern Modbus standards (introduced in Core 2026.7+ via the `home-assistant-libs/modbus-connection` ecosystem):
1. **Zero Custom Connection Wrappers**: Completely eliminate custom wrappers (`ResilientModbusUnit`) so that all device models, coordinators, and entity platforms interact purely with native `modbus_connection.ModbusUnit` handles.
2. **Centralized Hardware Connection Sharing**: Transition connection pooling and socket lifecycle management entirely to Home Assistant Core's Modbus broker (`homeassistant.components.modbus.async_get_unit`).
3. **Shared Half-Duplex Bus Sequencing**: Coordinate bus locking and transaction pacing across multiple independent integrations (e.g. FoxESS Inverter on Unit 247 and an Eastron Grid Meter on Unit 1 sharing a single RS-485 bridge).
4. **Standalone PyPI Distribution**: Distribute the device specification library independently as `foxess-modern` on PyPI while maintaining 100% logical synchronization with the vendored Home Assistant custom component.

---

## 2. Current State vs. Target Architecture Comparison

| Architectural Dimension | Current Production State | Target Long-Term Architecture |
| :--- | :--- | :--- |
| **Connection Management** | Home Assistant Core Modbus leases shared `ModbusUnit` via `async_get_unit` with standalone fallback | 100% Core Modbus shared unit leasing |
| **Half-Duplex Bus Locking** | Mutex (`asyncio.Lock`) decoupled into `FoxessRuntimeData` and coordinator layer | Central bus serialization managed by Core Modbus broker |
| **Manifest Dependencies** | `"after_dependencies": ["modbus"]` for zero-YAML connection pooling | Standardized load ordering across all Modbus integrations |
| **Diagnostics Platform** | Native `diagnostics.py` exposing lease status, bus timings, and coordinator health | Standard Home Assistant diagnostic export |
| **Transceiver Bus Pacing** | Adaptive pacing (nominal `300ms`, scaling to `450ms` during transient timeouts) | Centralized bus timing negotiated with serial bridge |
| **Coordinator Resilience** | Universal timeout debouncing (`self._timeouts < 2`) across all coordinators | Core DataUpdateCoordinator resilience standard |
| **PyPI Package Name** | Standalone library packaging configured as `foxess-modern` | Automated PyPI Trusted Publishing via GitHub Actions on release tags |

---

## 3. Phased Implementation Roadmap Status

### Phase 1: Decoupling and Encapsulating `ResilientModbusUnit`
* **Objective**: Remove external dependencies on `ResilientModbusUnit` so coordinators and entity platforms interact cleanly with standard `ModbusUnit` handles.
* **Status**: **Complete & Verified**.
* **Key Achievements**:
  1. Relocated half-duplex mutual exclusion lock (`asyncio.Lock`) out of `ResilientModbusUnit` into `FoxessRuntimeData.bus_lock` and coordinator instances.
  2. All entity platforms (`sensor.py`, `select.py`, `number.py`) interact purely with `FoxessDevice` and coordinator data.
  3. `ResilientModbusUnit` reduced purely to an internal fallback transport adapter when Core Modbus is unavailable.

### Phase 2: Core Modbus Connection Sharing
* **Objective**: Enable seamless Core Modbus connection leasing via `homeassistant.components.modbus.async_get_unit` without requiring manual YAML configuration.
* **Status**: **Complete & Verified Live in Core 2026.9.3**.
* **Key Achievements**:
  1. Leases shared `ModbusUnit` on startup via `async_get_unit`, pooling connections under `hass.data[DATA_MODBUS_CONNECTIONS]` with 0 YAML configuration.
  2. Automatic multi-device bus sharing without socket contention.
  3. Fully decoupled from deprecated YAML hubs (`modbus.get_hub`).
  4. Retains seamless fallback to standalone `modbus-connection` if Core Modbus raises an error.

### Phase 3: Dynamic Diagnostics & Adaptive Transceiver Pacing
* **Objective**: Add diagnostic visibility and bridge tolerance for lossy Wi-Fi/Ethernet transceivers.
* **Status**: **Complete & Verified Live**.
* **Key Achievements**:
  1. Native Diagnostics Platform ([`diagnostics.py`](file:///c:/Users/jover/.gemini/antigravity/scratch/foxess-modbus/custom_components/foxess_modern/diagnostics.py)):
     * Exposes transport lease status (`is_leased: True`), gateway address (`192.168.86.162:502`), Slave ID `247`, message spacing, and link timeouts.
     * Exposes coordinator health, intervals, consecutive timeout counters, and failed subsystem sets.
     * Automatically redacts serial numbers and unique IDs via `async_redact_data`.
  2. Adaptive Transceiver Bus Pacing:
     * Base pacing at `300ms` (optimal for FoxESS AUX UART and 4-string KH10 background calculations).
     * Automatically backs off to `450ms` on transient timeouts to let transceiver line ringing and bridge FIFO buffers clear, returning to `300ms` upon successful communication.
* **Future Extension**: Register boundary auto-discovery if future firmware introduces non-contiguous blocks.

### Phase 4: PyPI Release & Upstream Repository Alignment
* **Objective**: Formalize the public release pipeline.
* **Status**: **Complete & Ready for Release Tag**.
* **Key Achievements**:
  1. Configured PyPI Trusted Publishing (OIDC) workflow in `.github/workflows/publish.yml` with dual-tree check, test suite execution, and wheel build validation.
  2. Registered `foxess-modern` as a pending publisher on PyPI linked to `joverell/foxess-modbus`.
  3. Maintained CI workflow (`pytest.yaml`) verifying byte-for-byte synchronization between `src/foxess_modbus/` and `custom_components/foxess_modern/device/` via `python scripts/vendor.py --check`.

---

## 4. Key Lessons & Field Constraints to Preserve

Any future architectural refactoring must strictly respect these field-tested realities:

1. **The 60-Second Half-Duplex Collision Trap**:
   `readings_coordinator` (15s) and `settings_coordinator` (60s) poll concurrently in `asyncio`. Every 60 seconds, without a shared mutex, their read frames collide on the physical RS-485 wire. Mutual exclusion locking between coordinators is non-negotiable.
2. **300ms RS-485 Transceiver Line Decay & Inverter Computation**:
   Waveshare and High-Flying RS-485 bridge transceivers exhibit up to 200ms of line capacitance ringing and direction-switch delay. In addition, FoxESS KH10 AUX microcontrollers calculate 4 MPPT strings asynchronously. `message_spacing` must remain at least 0.30 seconds (300ms).
3. **Universal Coordinator Timeout Debouncing**:
   Wi-Fi gateways drop occasional packets. Inverter control entities (`Export Power Limit`, `Min SoC`, `Work Mode`) poll on a 60-second cycle. If slow coordinators lack debouncing, a single dropped frame causes all controls to flap to `Unavailable` for up to two minutes. `self._timeouts < 2` debouncing across all coordinators is mandatory.
4. **Single-Socket Gateway Isolation**:
   On RS-485 to Ethernet/Wi-Fi bridges (such as Waveshare), secondary sockets (e.g. Socket B on port 18899) must be turned OFF. When enabled, internal RAM contention causes the bridge to emit `Transaction ID: 0` error responses during prolonged inverter calculations.
5. **No Unconditional Core Manifest Dependencies**:
   Never add `"dependencies": ["modbus"]` until Home Assistant Core supports zero-YAML UI configuration for Modbus gateways.

---

## 5. Review Checklist for Future PRs

Before introducing changes targeting the future architecture:
* [ ] Does the change keep all entities functioning without requiring manual YAML `modbus:` entries?
* [ ] Is half-duplex bus locking preserved across all polling cycles and UI write commands?
* [ ] Is `message_spacing` maintained at or above 300ms?
* [ ] Do control entities and connection status remain debounced against isolated Wi-Fi timeouts?
* [ ] Does `python scripts/vendor.py --check` report 100% synchronization?
* [ ] Does `python -m pytest tests/` pass all tests?
