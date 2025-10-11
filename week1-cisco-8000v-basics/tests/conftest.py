"""
Pytest configuration for validation tests.
"""
import sys
from pathlib import Path

# Calculate project root correctly
# This file is at: validation/tests/conftest.py
# Project root is 2 levels up: ../../
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

print(f"DEBUG: conftest.py location: {Path(__file__)}")
print(f"DEBUG: Project root: {project_root}")
print(f"DEBUG: Project root exists: {project_root.exists()}")

# Verify the config file path
config_path = project_root / "net" / "nornir" / "config.yaml"
print(f"DEBUG: Config path: {config_path}")
print(f"DEBUG: Config exists: {config_path.exists()}")

import pytest
from nornir import InitNornir


@pytest.fixture(scope="session")
def project_root_path():
    """Provide project root path to all tests."""
    return project_root


@pytest.fixture(scope="function")
def nornir_instance(project_root_path):
    """Reusable Nornir instance for all tests in a module."""
    from net.nornir.tasks.show_httpx import restconf_close

    # Define paths relative to project root
    nornir_dir = project_root_path / "net" / "nornir"
    config_file = nornir_dir / "config.yaml"
    inventory_dir = nornir_dir / "inventory"

    if not config_file.exists():
        pytest.skip(f"Config file not found: {config_file}")

    print(f"Initializing Nornir with config: {config_file}")
    print(f"Inventory directory: {inventory_dir}")

    # Initialize Nornir with explicit inventory paths
    nr = InitNornir(
        config_file=str(config_file),
        inventory={
            "plugin": "SimpleInventory",
            "options": {
                "host_file": str(inventory_dir / "hosts.yaml"),
                "group_file": str(inventory_dir / "groups.yaml"),
                "defaults_file": str(inventory_dir / "defaults.yaml"),
            }
        },
        logging={"enabled": False}
    )

    yield nr

    # Cleanup after all tests
    nr.run(task=restconf_close)