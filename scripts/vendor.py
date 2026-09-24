#!/usr/bin/env python3
"""Vendor synchronization tool.

Synchronizes the standalone library (src/foxess_modbus) into the vendored
integration directory (custom_components/foxess_modern/device).

Usage:
    python scripts/vendor.py --check
    python scripts/vendor.py --sync
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys
from pathlib import Path


def get_paths() -> tuple[Path, Path]:
    """Return repository root paths for source and vendored directories."""
    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src" / "foxess_modbus"
    dev_dir = repo_root / "custom_components" / "foxess_modern" / "device"
    return src_dir, dev_dir


def check_sync(src_dir: Path, dev_dir: Path) -> bool:
    """Check whether src and dev directories are identical byte-for-byte."""
    if not src_dir.is_dir():
        print(f"Error: Source directory {src_dir} does not exist.")
        return False

    if not dev_dir.is_dir():
        print(f"Error: Vendored device directory {dev_dir} does not exist.")
        return False

    differences: list[str] = []

    # Check that every file in src exists and matches in dev
    for src_path in src_dir.rglob("*"):
        if src_path.is_dir() or "__pycache__" in src_path.parts or src_path.suffix == ".pyc":
            continue

        rel_path = src_path.relative_to(src_dir)
        target_path = dev_dir / rel_path

        if not target_path.exists():
            differences.append(f"Missing in vendored component: {rel_path}")
            continue

        if not filecmp.cmp(src_path, target_path, shallow=False):
            differences.append(f"Content differs: {rel_path}")

    # Check for extraneous files in dev
    for dev_path in dev_dir.rglob("*"):
        if dev_path.is_dir() or "__pycache__" in dev_path.parts or dev_path.suffix == ".pyc":
            continue

        rel_path = dev_path.relative_to(dev_dir)
        source_path = src_dir / rel_path

        if not source_path.exists():
            differences.append(f"Extraneous file in vendored component: {rel_path}")

    if differences:
        print(f"FAILED: Found {len(differences)} drift differences between library and vendored component:")
        for diff in differences:
            print(f"  - {diff}")
        return False

    print("SUCCESS: Standalone library and vendored device component are 100% synchronized.")
    return True


def perform_sync(src_dir: Path, dev_dir: Path) -> None:
    """Copy files from src to dev, removing obsolete files."""
    if not src_dir.is_dir():
        print(f"Error: Source directory {src_dir} does not exist.")
        sys.exit(1)

    print(f"Syncing from {src_dir} to {dev_dir}...")
    dev_dir.mkdir(parents=True, exist_ok=True)

    # Copy / update all files from src
    copied_count = 0
    for src_path in src_dir.rglob("*"):
        if src_path.is_dir() or "__pycache__" in src_path.parts or src_path.suffix == ".pyc":
            continue

        rel_path = src_path.relative_to(src_dir)
        target_path = dev_dir / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if not target_path.exists() or not filecmp.cmp(src_path, target_path, shallow=False):
            shutil.copy2(src_path, target_path)
            copied_count += 1

    # Remove extraneous files from dev
    removed_count = 0
    for dev_path in dev_dir.rglob("*"):
        if dev_path.is_dir() or "__pycache__" in dev_path.parts or dev_path.suffix == ".pyc":
            continue

        rel_path = dev_path.relative_to(dev_dir)
        source_path = src_dir / rel_path

        if not source_path.exists():
            dev_path.unlink()
            removed_count += 1

    print(f"Synchronization complete: {copied_count} files copied/updated, {removed_count} extraneous files removed.")


def main() -> None:
    """CLI entry point for vendor tool."""
    parser = argparse.ArgumentParser(description="Vendor synchronization utility")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check",
        action="store_true",
        help="Check whether standalone library and vendored component match.",
    )
    group.add_argument(
        "--sync",
        action="store_true",
        help="Synchronize src/foxess_modbus into custom_components/foxess_modern/device.",
    )

    args = parser.parse_args()
    src_dir, dev_dir = get_paths()

    if args.check:
        success = check_sync(src_dir, dev_dir)
        sys.exit(0 if success else 1)
    elif args.sync:
        perform_sync(src_dir, dev_dir)
        sys.exit(0)


if __name__ == "__main__":
    main()
