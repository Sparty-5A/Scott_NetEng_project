"""
NSO RESTCONF Client with safe getters and comprehensive error handling.

This module provides a clean interface to Cisco NSO's RESTCONF API with:
- Safe getter pattern with logging
- Transaction management
- Device sync operations
- Rollback capabilities
- Built on httpx for modern HTTP/2 support and type safety
"""

import httpx
from typing import Optional, Dict, Any, List
from loguru import logger
import urllib3

# Suppress SSL warnings for sandbox environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NSOClient:
    """Client for interacting with Cisco NSO via RESTCONF API using httpx."""

    def __init__(
        self,
        host: str,
        port: int = 8888,
        username: str = "admin",
        password: str = "admin",
        verify_ssl: bool = False,
        timeout: float = 30.0
    ):
        """
        Initialize NSO client.

        Args:
            host: NSO server hostname or IP
            port: RESTCONF port (default 8888)
            username: NSO username
            password: NSO password
            verify_ssl: Verify SSL certificates (False for sandbox)
            timeout: Default timeout for requests in seconds
        """
        self.host = host
        self.port = port
        self.base_url = f"https://{host}:{port}/restconf"
        self.auth = (username, password)
        self.verify = verify_ssl
        self.timeout = timeout

        # Create httpx client with default headers
        self.client = httpx.Client(
            verify=self.verify,
            headers={
                "Content-Type": "application/yang-data+json",
                "Accept": "application/yang-data+json"
            },
            timeout=self.timeout
        )

        logger.info(f"Initialized NSO client for {host}:{port}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close client."""
        self.close()

    def close(self):
        """Close the httpx client."""
        self.client.close()
        logger.debug("NSO client closed")

    def _safe_get(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Safe GET request with error handling and logging.

        Args:
            url: Full URL to query
            **kwargs: Additional httpx arguments

        Returns:
            JSON response as dict, or None on error
        """
        try:
            logger.debug(f"GET {url}")
            resp = self.client.get(url, auth=self.auth, **kwargs)
            resp.raise_for_status()

            if resp.status_code == 204:
                logger.debug("Received 204 No Content")
                return {}

            return resp.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error on GET {url}: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.TimeoutException:
            logger.error(f"Timeout on GET {url}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request failed on GET {url}: {str(e)}")
            return None
        except ValueError as e:
            logger.error(f"Invalid JSON response from {url}: {str(e)}")
            return None

    def _safe_post(self, url: str, payload: Dict[str, Any], **kwargs) -> Optional[httpx.Response]:
        """Safe POST request with error handling."""
        try:
            logger.debug(f"POST {url}")
            resp = self.client.post(url, json=payload, auth=self.auth, **kwargs)
            resp.raise_for_status()
            return resp

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error on POST {url}: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request failed on POST {url}: {str(e)}")
            return None

    def _safe_patch(self, url: str, payload: Dict[str, Any], **kwargs) -> Optional[httpx.Response]:
        """Safe PATCH request with error handling."""
        try:
            logger.debug(f"PATCH {url}")
            resp = self.client.patch(url, json=payload, auth=self.auth, **kwargs)
            resp.raise_for_status()
            return resp

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error on PATCH {url}: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request failed on PATCH {url}: {str(e)}")
            return None

    def _safe_delete(self, url: str, **kwargs) -> Optional[httpx.Response]:
        """Safe DELETE request with error handling."""
        try:
            logger.debug(f"DELETE {url}")
            resp = self.client.delete(url, auth=self.auth, **kwargs)
            resp.raise_for_status()
            return resp

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error on DELETE {url}: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request failed on DELETE {url}: {str(e)}")
            return None

    def health_check(self) -> bool:
        """
        Verify NSO is reachable and responsive.

        Returns:
            True if NSO responds successfully
        """
        url = f"{self.base_url}/data/tailf-ncs:devices"
        result = self._safe_get(url)

        if result is not None:
            logger.info("✓ NSO health check passed")
            return True
        else:
            logger.error("✗ NSO health check failed")
            return False

    def get_devices(self) -> Optional[List[str]]:
        """
        Get list of all managed devices.

        Returns:
            List of device names, or None on error
        """
        url = f"{self.base_url}/data/tailf-ncs:devices/device"
        result = self._safe_get(url)

        if result and "tailf-ncs:device" in result:
            devices = [d["name"] for d in result["tailf-ncs:device"]]
            logger.info(f"Found {len(devices)} devices: {devices}")
            return devices

        logger.warning("No devices found or query failed")
        return None

    def sync_from_device(self, device_name: str) -> bool:
        """
        Sync configuration from device to NSO (sync-from).

        Args:
            device_name: Name of device to sync

        Returns:
            True if sync successful
        """
        url = f"{self.base_url}/data/tailf-ncs:devices/device={device_name}/sync-from"
        payload = {"input": {}}

        logger.info(f"Syncing from device: {device_name}")
        resp = self._safe_post(url, payload)

        if resp and resp.status_code in (200, 204):
            logger.info(f"✓ Sync-from successful for {device_name}")
            return True

        logger.error(f"✗ Sync-from failed for {device_name}")
        return False

    def get_device_config(self, device_name: str) -> Optional[Dict[str, Any]]:
        """
        Get full configuration for a device from NSO CDB.

        Args:
            device_name: Name of device

        Returns:
            Device config as dict, or None on error
        """
        url = f"{self.base_url}/data/tailf-ncs:devices/device={device_name}/config"
        result = self._safe_get(url)

        if result:
            logger.info(f"Retrieved config for {device_name}")
            return result

        logger.error(f"Failed to get config for {device_name}")
        return None

    def get_interface_config(self, device_name: str, interface_type: str, interface_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific interface configuration.

        Args:
            device_name: Device name
            interface_type: Interface type (e.g., 'Loopback', 'GigabitEthernet')
            interface_id: Interface ID (e.g., '0', '0/0/0')

        Returns:
            Interface config as dict, or None if not found
        """
        url = f"{self.base_url}/data/tailf-ncs:devices/device={device_name}/config/tailf-ned-cisco-ios:interface/{interface_type}={interface_id}"
        result = self._safe_get(url)

        if result:
            logger.info(f"Retrieved {interface_type}{interface_id} config from {device_name}")
            return result

        logger.warning(f"{interface_type}{interface_id} not found on {device_name}")
        return None

    def configure_loopback(
        self,
        device_name: str,
        loopback_id: str,
        ip_address: str,
        netmask: str,
        description: Optional[str] = None
    ) -> bool:
        """
        Configure a loopback interface on IOS XE device.

        Args:
            device_name: Target device
            loopback_id: Loopback number (e.g., '100')
            ip_address: IP address
            netmask: Subnet mask
            description: Optional interface description

        Returns:
            True if configuration successful
        """
        url = f"{self.base_url}/data/tailf-ncs:devices/device={device_name}/config"

        payload = {
            "tailf-ned-cisco-ios:interface": {
                "Loopback": [
                    {
                        "name": loopback_id,
                        "ip": {
                            "address": {
                                "primary": {
                                    "address": ip_address,
                                    "mask": netmask
                                }
                            }
                        }
                    }
                ]
            }
        }

        if description:
            payload["tailf-ned-cisco-ios:interface"]["Loopback"][0]["description"] = description

        logger.info(f"Configuring Loopback{loopback_id} on {device_name}: {ip_address}/{netmask}")
        resp = self._safe_patch(url, payload)

        if resp and resp.status_code in (200, 204):
            logger.info(f"✓ Loopback{loopback_id} configured successfully")
            return True

        logger.error(f"✗ Failed to configure Loopback{loopback_id}")
        return False

    def delete_loopback(self, device_name: str, loopback_id: str) -> bool:
        """
        Delete a loopback interface.

        Args:
            device_name: Target device
            loopback_id: Loopback number to delete

        Returns:
            True if deletion successful
        """
        url = f"{self.base_url}/data/tailf-ncs:devices/device={device_name}/config/tailf-ned-cisco-ios:interface/Loopback={loopback_id}"

        logger.info(f"Deleting Loopback{loopback_id} from {device_name}")
        resp = self._safe_delete(url)

        if resp and resp.status_code in (200, 204):
            logger.info(f"✓ Loopback{loopback_id} deleted successfully")
            return True

        logger.error(f"✗ Failed to delete Loopback{loopback_id}")
        return False

    def commit_dry_run(self) -> Optional[Dict[str, Any]]:
        """
        Perform a dry-run commit to see what would change.

        Returns:
            Dry-run results, or None on error
        """
        url = f"{self.base_url}/data/tailf-ncs:devices/commit-dry-run"
        payload = {"input": {"outformat": "native"}}

        logger.info("Running commit dry-run")
        resp = self._safe_post(url, payload)

        if resp:
            result = resp.json()
            logger.info("✓ Dry-run completed")
            return result

        logger.error("✗ Dry-run failed")
        return None

    def commit(self) -> bool:
        """
        Commit pending changes to devices.

        Returns:
            True if commit successful
        """
        url = f"{self.base_url}/data/tailf-ncs:devices/commit"
        payload = {"input": {}}

        logger.info("Committing changes to devices")
        resp = self._safe_post(url, payload)

        if resp and resp.status_code in (200, 204):
            logger.info("✓ Commit successful")
            return True

        logger.error("✗ Commit failed")
        return False

    def get_rollback_files(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of available rollback files.

        Returns:
            List of rollback file info, or None on error
        """
        url = f"{self.base_url}/data/tailf-ncs:rollback-files"
        result = self._safe_get(url)

        if result and "tailf-ncs:rollback-files" in result:
            files = result["tailf-ncs:rollback-files"].get("file", [])
            logger.info(f"Found {len(files)} rollback files")
            return files

        logger.warning("No rollback files found")
        return None

    def rollback(self, rollback_id: int = 0) -> bool:
        """
        Rollback to a previous configuration.

        Args:
            rollback_id: Rollback file number (0 = last commit)

        Returns:
            True if rollback successful
        """
        url = f"{self.base_url}/operations/tailf-ncs:rollback"
        payload = {"input": {"file": rollback_id}}

        logger.warning(f"Rolling back to rollback file {rollback_id}")
        resp = self._safe_post(url, payload)

        if resp and resp.status_code in (200, 204):
            logger.info(f"✓ Rollback to {rollback_id} successful")
            return True

        logger.error(f"✗ Rollback to {rollback_id} failed")
        return False