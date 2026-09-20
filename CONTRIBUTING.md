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
   > **Microcontroller Buffer Limit**: FoxESS AUX UART microcontrollers have bounded FIFO buffers. Keep `max_span = 32` on all components to prevent serial communication lockups.

2. **Implement the Inverter Class**:
   Subclass `Device` from `modbus_connection.model`, instantiate your components, and group fast telemetry (`_readings`) and slower configuration (`_settings`).

3. **Add Unit Tests**:
   Create a test fixture in `tests/` using `MockModbusConnection`:
   ```python
   from modbus_connection.mock import MockModbusConnection

   conn = MockModbusConnection()
   unit = conn.for_unit(247)
   unit.holding[39070] = 3805  # 380.5 V
   ```

---

## Running Tests & Checks

Before submitting a Pull Request, verify that all unit tests pass:

```bash
pytest -v
```

---

## Pull Request Guidelines

- Use clear commit messages following Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`).
- Keep changes focused and atomic.
- Ensure any new registers include their verified scaling factors and units.
