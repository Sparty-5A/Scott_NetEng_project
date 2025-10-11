"""
Pytest fixtures for NSO testing.

Provides reusable test fixtures for NSO client initialization,
device management, and test cleanup.
"""

import pytest
import os
from loguru import logger
from automation.nso_client import NSOClient

# Configure loguru for tests
logger.remove()  # Remove default handler
logger.add(
    "logs/test_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)
logger.add(
    lambda msg: print(msg, end=""),  # Console output
    level="INFO",
    colorize=True
)


@pytest.fixture(scope="session")
def nso_credentials():
    """
    NSO credentials from environment variables.

    Set these before running tests:
        export NSO_HOST=10.10.20.49
        export NSO_PORT=8888
        export NSO_USERNAME=admin
        export NSO_PASSWORD=admin
    """
    return {
        "host": os.getenv("NSO_HOST", "sandbox-nso-1.cisco.com"),
        "port": int(os.getenv("NSO_PORT", "8888")),
        "username": os.getenv("NSO_USERNAME", "admin"),
        "password": os.getenv("NSO_PASSWORD", "admin"),
    }


@pytest.fixture(scope="session")
def nso_client_session(nso_credentials):
    """
    Session-scoped NSO client for health checks and device discovery.

    Use this for read-only operations that can be shared across tests.
    """
    logger.info("Creating session-scoped NSO client")
    client = NSOClient(**nso_credentials)

    # Verify connectivity
    if not client.health_check():
        pytest.skip("NSO is not reachable - skipping tests")

    yield client

    logger.info("Tearing down session-scoped NSO client")


@pytest.fixture(scope="function")
def nso_client(nso_credentials):
    """
    Function-scoped NSO client for tests that modify configuration.

    Each test gets a fresh client instance. Use this for write operations
    to ensure proper isolation.
    """
    logger.info("Creating function-scoped NSO client")
    client = NSOClient(**nso_credentials)

    yield client

    logger.info("Tearing down function-scoped NSO client")


@pytest.fixture(scope="session")
def available_devices(nso_client_session):
    """
    Discover available devices in NSO.

    Returns a list of device names that can be used in tests.
    If no devices found, skip all tests.
    """
    logger.info("Discovering devices from NSO")
    devices = nso_client_session.get_devices()

    if not devices:
        pytest.skip("No devices found in NSO - cannot run tests")

    logger.info(f"Available devices: {devices}")
    return devices


@pytest.fixture(scope="function")
def test_device(available_devices):
    """
    Provide a single test device for simple tests.

    Returns the first IOS XE device found, or skips if none available.
    """
    # Prefer devices with 'rtr' or 'router' in the name (typically IOS XE)
    for device in available_devices:
        if any(keyword in device.lower() for keyword in ['rtr', 'router', 'csr', 'ios']):
            logger.info(f"Selected test device: {device}")
            return device

    # Fallback to first device
    logger.info(f"Using first available device: {available_devices[0]}")
    return available_devices[0]


@pytest.fixture(scope="function")
def sync_device(nso_client, test_device):
    """
    Ensure test device is synced before test runs.

    Performs sync-from at start of each test to ensure NSO has
    latest device state.
    """
    logger.info(f"Pre-test sync for {test_device}")
    success = nso_client.sync_from_device(test_device)

    if not success:
        pytest.skip(f"Could not sync {test_device} - device may be unreachable")

    return test_device


@pytest.fixture(scope="function")
def clean_loopback(nso_client, test_device, request):
    """
    Cleanup fixture for loopback tests.

    Usage in test:
        @pytest.mark.usefixtures("clean_loopback")
        def test_something(nso_client, test_device):
            loopback_id = "100"
            # Test creates Loopback100

    The fixture will automatically clean up Loopback100 after the test.
    """
    # Store loopback IDs created during test
    created_loopbacks = []

    def _register_loopback(loopback_id: str):
        """Register a loopback for cleanup"""
        created_loopbacks.append(loopback_id)

    # Make registration function available to tests
    request.instance.register_loopback = _register_loopback if hasattr(request, 'instance') else None

    yield created_loopbacks

    # Cleanup after test
    logger.info(f"Cleaning up loopbacks: {created_loopbacks}")
    for loopback_id in created_loopbacks:
        try:
            nso_client.delete_loopback(test_device, loopback_id)
            nso_client.commit()
        except Exception as e:
            logger.warning(f"Failed to cleanup Loopback{loopback_id}: {e}")


@pytest.fixture(scope="function")
def test_loopback_config():
    """
    Sample loopback configuration for testing.

    Returns a dict with test loopback parameters.
    """
    return {
        "loopback_id": "100",
        "ip_address": "10.100.100.1",
        "netmask": "255.255.255.255",
        "description": "TEST_LOOPBACK_DO_NOT_USE"
    }


@pytest.fixture(autouse=True)
def log_test_info(request):
    """
    Automatically log test start/end for all tests.

    This fixture runs for every test automatically.
    """
    test_name = request.node.name
    logger.info(f"{'=' * 60}")
    logger.info(f"Starting test: {test_name}")
    logger.info(f"{'=' * 60}")

    yield

    logger.info(f"{'=' * 60}")
    logger.info(f"Finished test: {test_name}")
    logger.info(f"{'=' * 60}\n")


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "nso: mark test as requiring NSO connectivity"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )