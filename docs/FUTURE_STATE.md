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

## 2. Current State vs. Future State Comparison

| Architectural Dimension | Current State (Interim Production) | Target Future State |
| :--- | :--- | :--- |
| **Connection Management** | `ResilientModbusUnit` manages `ModbusConnection` lifecycle and socket creation | Home Assistant Core Modbus leases shared `ModbusUnit` instances via `async_get_unit` |
| **Half-Duplex Bus Locking** | `asyncio.Lock` embedded inside `ResilientModbusUnit` | Central bus serialization managed by Core Modbus broker or coordinator bus-lock manager |
| **Manifest Dependencies** | No Core dependencies (`requirements: ["modbus-connection[tmodbus]"]`) | `"after_dependencies": ["modbus"]` for graceful upgrade with standalone fallback |
| **Device Layer Interface** | `FoxessDevice` protocol accepts `ModbusUnit` | Native `ModbusUnit` passed directly with zero transport wrappers |
| **Coordinator Resilience** | Universal timeout debouncing (`self._timeouts < 2`) in `coordinator.py` | Native coordinator debouncing and error reporting standard |
| **PyPI Package Name** | Standalone library packaging configured as `foxess-modern` | Automated PyPI Trusted Publishing via GitHub Actions on release tags |

---

## 3. Phased Implementation Roadmap

### Phase 1: Decoupling and Encapsulating `ResilientModbusUnit`
* **Objective**: Remove all external dependencies on `ResilientModbusUnit` methods outside `connection.py`.
* **Action Items**:
  1. Move the `asyncio.Lock` out of `ResilientModbusUnit` and into a dedicated `BusLockManager` or directly into the coordinators.
  2. Ensure all entity platforms (`sensor.py`, `select.py`, `number.py`) only interact with `FoxessDevice` and never access transport connection handles.
  3. Ensure `device.async_update_readings()` and `device.async_update_settings()` accept pure `ModbusUnit` protocol implementations.
  4. Reduce `ResilientModbusUnit` to an internal fallback transport adapter used only when Core Modbus connection leasing is absent.

### Phase 2: Core Modbus Connection Sharing (Upstream Dependent)
* **Objective**: Adopt `homeassistant.components.modbus.async_get_unit` without breaking installations lacking manual YAML configuration.
* **Context & Limitations**:
  * In Home Assistant Core 2026.9, Core `modbus` remains an optional component that requires a `modbus:` block in `configuration.yaml`.
  * Declaring `"dependencies": ["modbus"]` in `manifest.json` blocks integration startup if Core `modbus` is unconfigured.
* **Target Actions**:
  1. When Home Assistant Core introduces UI configuration or automatic setup for shared Modbus gateways, declare `"after_dependencies": ["modbus"]`.
  2. Implement opportunistic leasing:
     * Check if Core Modbus connection sharing is active.
     * If active, call `async_get_unit(hass, entry, params, unit_id)`.
     * If inactive, smoothly fall back to the standalone `modbus_connection.tmodbus.ModbusConnection` instance.
  3. This ensures users never need manual YAML setup to run `foxess_modern`.

### Phase 3: Dynamic Register Planning & Diagnostics
* **Objective**: Enhance auto-tuning and diagnostics over lossy wireless bridges.
* **Action Items**:
  1. Implement dynamic message spacing: automatically back off from 250ms to 400ms if consecutive timeouts occur, and recover down to 200ms under stable low-jitter conditions.
  2. Add Home Assistant diagnostics (`diagnostics.py`) exposing Modbus transaction counters, CRC retry rates, and coordinator debounce metrics to the UI.
  3. Add register boundary discovery to detect custom firmware variations (e.g. new BMS registers on KH firmware 1.70+).

### Phase 4: PyPI Release & Upstream Repository Alignment
* **Objective**: Formalize the public release pipeline.
* **Action Items**:
  1. Complete PyPI Trusted Publisher registration for package `foxess-modern`.
  2. Maintain CI workflow (`pytest.yaml`) verifying byte-for-byte synchronization between `src/foxess_modbus/` and `custom_components/foxess_modern/device/` via `python scripts/vendor.py --check`.
  3. Tag and publish releases only upon explicit user instruction.

---

## 4. Key Lessons & Field Constraints to Preserve

Any future architectural refactoring must strictly respect these field-tested realities:

1. **The 60-Second Half-Duplex Collision Trap**:
   `readings_coordinator` (15s) and `settings_coordinator` (60s) poll concurrently in `asyncio`. Every 60 seconds, without a shared mutex, their read frames collide on the physical RS-485 wire. Mutual exclusion locking between coordinators is non-negotiable.
2. **250ms RS-485 Transceiver Line Decay**:
   Waveshare and High-Flying RS-485 bridge transceivers exhibit up to 200ms of line capacitance ringing and direction-switch delay. `message_spacing` must remain at least 0.25 seconds.
3. **Universal Coordinator Timeout Debouncing**:
   Wi-Fi gateways drop occasional packets. Inverter control entities (`Export Power Limit`, `Min SoC`, `Work Mode`) poll on a 60-second cycle. If slow coordinators lack debouncing, a single dropped frame causes all controls to flap to `Unavailable` for up to two minutes. `self._timeouts < 2` debouncing across all coordinators is mandatory.
4. **No Unconditional Core Manifest Dependencies**:
   Never add `"dependencies": ["modbus"]` until Home Assistant Core supports zero-YAML UI configuration for Modbus gateways.

---

## 5. Review Checklist for Future PRs

Before introducing changes targeting the future architecture:
* [ ] Does the change keep all entities functioning without requiring manual YAML `modbus:` entries?
* [ ] Is half-duplex bus locking preserved across all polling cycles and UI write commands?
* [ ] Is `message_spacing` maintained at or above 250ms?
* [ ] Do control entities remain debounced against isolated Wi-Fi timeouts?
* [ ] Does `python scripts/vendor.py --check` report 100% synchronization?
* [ ] Does `python -m pytest tests/` pass all tests?
