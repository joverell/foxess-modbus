"""Unit tests for Net Grid Power sensor and firmware version formatting."""

import pytest
from unittest.mock import MagicMock

from custom_components.foxess_modern.sensor import (
    format_version,
    SINGLE_PHASE_GRID_DESCRIPTIONS,
    THREE_PHASE_GRID_DESCRIPTIONS,
)


def test_format_version():
    """Verify version integer is formatted into decimal or hex version string."""
    assert format_version(133) == "1.33"
    assert format_version(100) == "1.00"
    assert format_version(115) == "1.15"
    assert format_version(205) == "2.05"
    assert format_version(None) is None
    assert format_version("1.02.00") == "1.02.00"
    # Hex version format (e.g. KH10 Master 1.69, Slave 1.03, Manager 1.64)
    assert format_version(0x0169, is_hex=True) == "1.69"
    assert format_version(0x0103, is_hex=True) == "1.03"
    assert format_version(0x0164, is_hex=True) == "1.64"
    assert format_version(356, is_hex=True) == "1.64"


def test_single_phase_net_grid_power():
    """Verify net_grid_power reflects signed CT meter power on single-phase."""
    desc = next(d for d in SINGLE_PHASE_GRID_DESCRIPTIONS if d.key == "net_grid_power")

    # Exporting (+2500 W)
    dev_export = MagicMock()
    dev_export.grid.ct_meter_power = 2500
    assert desc.value_fn(dev_export) == 2500

    # Importing (-1800 W)
    dev_import = MagicMock()
    dev_import.grid.ct_meter_power = -1800
    assert desc.value_fn(dev_import) == -1800


def test_three_phase_net_grid_power():
    """Verify net_grid_power reflects total signed grid power on three-phase."""
    desc = next(d for d in THREE_PHASE_GRID_DESCRIPTIONS if d.key == "net_grid_power")

    # Exporting (+3500 W across phases)
    dev_export = MagicMock()
    dev_export.grid.grid_power_total = 3500.0
    assert desc.value_fn(dev_export) == 3500.0

    # Importing (-4200 W across phases)
    dev_import = MagicMock()
    dev_import.grid.grid_power_total = -4200.0
    assert desc.value_fn(dev_import) == -4200.0


def test_kh10_inverter_state_and_versions_sensor():
    """Verify KH10 inverter state and versions through sensor definitions."""
    from custom_components.foxess_modern.sensor import BASE_SENSOR_DESCRIPTIONS
    from foxess_modbus.const import InverterState

    dev = MagicMock()
    dev.inverter.version_is_hex = True
    dev.inverter.master_version = 0x0169  # 361 dec
    dev.inverter.slave_version = 0x0103   # 259 dec
    dev.inverter.manager_version = 0x0164 # 356 dec
    dev.inverter.state = InverterState.ON_GRID

    state_desc = next(d for d in BASE_SENSOR_DESCRIPTIONS if d.key == "inverter_state")
    master_desc = next(d for d in BASE_SENSOR_DESCRIPTIONS if d.key == "master_version")
    slave_desc = next(d for d in BASE_SENSOR_DESCRIPTIONS if d.key == "slave_version")
    manager_desc = next(d for d in BASE_SENSOR_DESCRIPTIONS if d.key == "manager_version")

    assert state_desc.value_fn(dev) == "On Grid"
    assert "On Grid" in state_desc.options
    assert master_desc.value_fn(dev) == "1.69"
    assert slave_desc.value_fn(dev) == "1.03"
    assert manager_desc.value_fn(dev) == "1.64"
