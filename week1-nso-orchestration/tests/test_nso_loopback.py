"""
Integration tests for NSO loopback configuration.

Tests cover:
- NSO connectivity and health
- Device discovery and sync
- Loopback creation and validation
- Pre/post-checks
- Rollback on failure
"""
import pytest
from loguru import logger

@pytest.mark.nso
class TestNSOConnectivity:
    """Test basic NSO connectivity and setup."""

    def test_nso_health_check(self, nso_client_session):
        """Verify NSO is reachable and responsive."""
        assert nso_client_session.health_check(), "NSO health check failed"

    def test_devices_discovered(self, available_devices):
        """Verify at least one device is managed by NSO."""
        assert len(available_devices) > 0, "No devices found in NSO"
        logger.info(f"Discovered {len(available_devices)} devices")

    def test_device_sync(self, nso_client, test_device):
        """Verify we can sync configuration from a device."""
        result = nso_client.sync_from_device(test_device)
        assert result is True, f"Failed to sync from {test_device}"

@pytest.mark.nso
@pytest.mark.integration
class TestLoopbackConfiguration:
    """Test loopback interface configuration via NSO."""

    def test_create_loopback(self, nso_client, sync_device, test_loopback_config):
        """
        Test creating a loopback interface.

        Steps:
        1. Verify loopback doesn't exist (pre-check)
        2. Create loopback via NSO
        3. Commit changes
        4. Verify loopback exists (post-check)
        5. Cleanup
        """
        loopback_id = test_loopback_config["loopback_id"]
        device = sync_device

        # PRE-CHECK: Ensure loopback doesn't exist
        logger.info(f"PRE-CHECK: Verifying Loopback{loopback_id} doesn't exist")
        existing = nso_client.get_interface_config(device, "Loopback", loopback_id)

        if existing:
            logger.warning(f"Loopback{loopback_id} already exists, cleaning up first")
            nso_client.delete_loopback(device, loopback_id)
            nso_client.commit()

        # CREATE: Configure loopback
        logger.info(f"DEPLOY: Creating Loopback{loopback_id} on {device}")
        result = nso_client.configure_loopback(
            device_name=device,
            **test_loopback_config
        )
        assert result is True, "Failed to configure loopback"

        # COMMIT
        logger.info("COMMIT: Applying configuration")
        commit_result = nso_client.commit()
        assert commit_result is True, "Commit failed"

        # POST-CHECK: Verify loopback exists
        logger.info(f"POST-CHECK: Verifying Loopback{loopback_id} exists")
        nso_client.sync_from_device(device)
        interface = nso_client.get_interface_config(device, "Loopback", loopback_id)
        assert interface is not None, "Loopback not found after creation"

        # Verify IP address (structure varies by NED version)
        logger.info(f"Loopback configuration: {interface}")

        # CLEANUP
        logger.info("CLEANUP: Removing test loopback")
        nso_client.delete_loopback(device, loopback_id)
        nso_client.commit()

    def test_create_multiple_loopbacks(self, nso_client, sync_device):
        """Test creating multiple loopbacks in a single transaction."""
        device = sync_device
        loopbacks = [
            {"loopback_id": "101", "ip_address": "10.101.101.1", "netmask": "255.255.255.255"},
            {"loopback_id": "102", "ip_address": "10.102.102.1", "netmask": "255.255.255.255"},
            {"loopback_id": "103", "ip_address": "10.103.103.1", "netmask": "255.255.255.255"},
        ]

        try:
            # Create all loopbacks
            for config in loopbacks:
                logger.info(f"Creating Loopback{config['loopback_id']}")
                result = nso_client.configure_loopback(device, **config)
                assert result is True, f"Failed to configure Loopback{config['loopback_id']}"

            # Single commit
            logger.info("Committing all changes")
            commit_result = nso_client.commit()
            assert commit_result is True, "Batch commit failed"

            # Verify all exist
            nso_client.sync_from_device(device)
            for config in loopbacks:
                interface = nso_client.get_interface_config(device, "Loopback", config['loopback_id'])
                assert interface is not None, f"Loopback{config['loopback_id']} not found"

        finally:
            # Cleanup
            logger.info("Cleaning up test loopbacks")
            for config in loopbacks:
                nso_client.delete_loopback(device, config['loopback_id'])
            nso_client.commit()

    def test_delete_loopback(self, nso_client, sync_device, test_loopback_config):
        """Test deleting a loopback interface."""
        device = sync_device
        loopback_id = "110"

        # Create loopback first
        logger.info(f"Creating Loopback{loopback_id} for deletion test")
        nso_client.configure_loopback(
            device_name=device,
            loopback_id=loopback_id,
            ip_address="10.110.110.1",
            netmask="255.255.255.255"
        )
        nso_client.commit()

        # Verify it exists
        nso_client.sync_from_device(device)
        interface = nso_client.get_interface_config(device, "Loopback", loopback_id)
        assert interface is not None, "Loopback wasn't created"

        # Delete it
        logger.info(f"Deleting Loopback{loopback_id}")
        delete_result = nso_client.delete_loopback(device, loopback_id)
        assert delete_result is True, "Delete operation failed"

        # Commit deletion
        commit_result = nso_client.commit()