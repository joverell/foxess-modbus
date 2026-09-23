"""Unit tests for Net Grid Power sensor and firmware version formatting."""

import pytest
from unittest.mock import MagicMock

from custom_components.foxess_modern.sensor import (
    format_version,
    SINGLE_PHASE_GRID_DESCRIPTIONS,
    THREE_PHASE_GRID_DESCRIPTIONS,
)


def test_format_version():
    """Verify version integer is formatted into decimal version string."""
    assert format_version(133) == "1.33"
    assert format_version(100) == "1.00"
    assert format_version(115) == "1.15"
    assert format_version(205) == "2.05"
    assert format_version(None) is None
    assert format_version("1.02.00") == "1.02.00"


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
