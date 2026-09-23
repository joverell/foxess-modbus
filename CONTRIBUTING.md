# Contributing to foxess-modbus

Thank you for your interest in improving `foxess-modbus`! We welcome contributions, whether they are bug fixes, documentation enhancements, or support for additional FoxESS inverter models (e.g., H1, H3, AIO, EVO).

---

## Development Setup

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/<your-username>/foxess-modbus.git
   cd foxess-modbus
   ```

2. **Set up a Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in Editable Mode**:
   ```bash
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```

---

## Adding Support for New Inverter Models

When contributing support for another FoxESS series:

1. **Subclass `FoxessComponent`**:
   Define registers using `modbus_connection.model` descriptors (`gauge`, `integer`, `int32`, `uint32`).
   
   > [!IMPORTANT]
   > **Microcontroller Buffer Limit**: FoxESS AUX UART microcontrollers have bounded FIFO buffers (typically 64 bytes). Set `max_span = 8` on all components to prevent serial communication lockups and timeout errors.

2. **Implement the Inverter Class**:
   Subclass `FoxessDevice` (which inherits from `modbus_connection.model.Device`), instantiate your components, and group fast telemetry (`_readings`) and slower configuration (`_settings`). Ensure `async_update()` returns `UpdateReport` and `async_read_raw(names=...)` returns `Raw`.

3. **Maintain Dual-Tree Zero Drift**:
   Synchronize any changes in `src/foxess_modbus/<series>/` with the vendored Home Assistant integration directory `custom_components/foxess_modern/device/<series>/`.

4. **Add Unit Tests & Parity Verification**:
   Create a test fixture in `tests/` using `MockModbusConnection`:
   ```python
   from modbus_connection.mock import MockModbusConnection

   conn = MockModbusConnection()
   unit = conn.for_unit(247)
   unit.holding[39070] = 3805  # 380.5 V
   ```
   Ensure the architectural invariants and zero-drift verification suite passes without modification.

---

## Running Tests & Checks

Before submitting a Pull Request, verify that all unit and specification tests pass:

```bash
pytest -v
```

This validates both functional inverter modeling and strict compliance with the upstream `modbus-connection` design specifications (`tests/test_modbus_connection_spec.py`).

---

## Pull Request Guidelines

- Use clear commit messages following Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`).
- Keep changes focused and atomic.
- Ensure any new registers include their verified scaling factors and units.
