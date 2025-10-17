"""
BGP Peering Service deployment module.

This module provides idempotent deployment of BGP peering services
using a template-based approach.
"""

from loguru import logger
from pathlib import Path

from nso_orchestration.automation.nso_client import NSOClient
from nso_orchestration.automation.service_models import BGPPeeringServiceIntent
from nso_orchestration.automation.template_renderer import render_template


def check_bgp_configured(client: NSOClient, device_name: str, intent: BGPPeeringServiceIntent) -> bool:
    """
    Check if BGP is already configured according to intent.

    Args:
        client: NSO client
        device_name: Target device
        intent: Desired BGP configuration

    Returns:
        True if BGP matches intent (no changes needed)
    """
    logger.info(f"[{device_name}] Checking if BGP already configured")

    try:
        # Sync from device to get current state
        client.sync_from_device(device_name)

        # Get device config
        config = client.get_device_config(device_name)
        if not config:
            logger.warning(f"[{device_name}] Could not retrieve config")
            return False

        # Navigate to BGP config
        bgp_config = (
            config.get("tailf-ncs:config", {})
            .get("tailf-ned-cisco-ios:router", {})
            .get("bgp", {})
        )

        if not bgp_config:
            logger.info(f"[{device_name}] No BGP configuration found")
            return False

        # Check AS number
        current_as = bgp_config.get("as-no")
        if str(current_as) != str(intent.local_as):
            logger.info(f"[{device_name}] AS mismatch: current={current_as}, desired={intent.local_as}")
            return False

        # Check router ID
        current_router_id = bgp_config.get("bgp-router-id")
        if current_router_id != intent.router_id:
            logger.info(f"[{device_name}] Router-ID mismatch: current={current_router_id}, desired={intent.router_id}")
            return False

        # Check neighbors exist
        current_neighbors = bgp_config.get("neighbor", [])
        if not isinstance(current_neighbors, list):
            current_neighbors = [current_neighbors] if current_neighbors else []

        current_neighbor_ips = {n.get("id") for n in current_neighbors}
        desired_neighbor_ips = {n.neighbor_ip for n in intent.neighbors}

        if current_neighbor_ips != desired_neighbor_ips:
            logger.info(
                f"[{device_name}] Neighbor mismatch: current={current_neighbor_ips}, desired={desired_neighbor_ips}")
            return False

        # If we got here, BGP is configured correctly
        logger.info(f"[{device_name}] ✓ BGP already configured correctly")
        return True

    except Exception as e:
        logger.error(f"[{device_name}] Error checking BGP config: {e}")
        return False


def deploy_bgp_service(
        client: NSOClient,
        device_name: str,
        intent: BGPPeeringServiceIntent,
        dry_run: bool = False
) -> tuple[bool, str]:
    """
    Deploy BGP peering service to a device.

    Args:
        client: NSO client
        device_name: Target device name
        intent: BGP service intent
        dry_run: If True, only show what would change

    Returns:
        Tuple of (success: bool, message: str)
    """
    logger.info(f"[{device_name}] Deploying BGP peering service")
    logger.debug(f"  Local AS: {intent.local_as}")
    logger.debug(f"  Router ID: {intent.router_id}")
    logger.debug(f"  Neighbors: {[n.neighbor_ip for n in intent.neighbors]}")

    # Idempotency check
    if not dry_run and check_bgp_configured(client, device_name, intent):
        return True, "Already configured (no changes needed)"

    # Render template
    try:
        config_xml = render_template(
            "ios-xe/bgp_service.xml.j2",
            local_as=intent.local_as,
            router_id=intent.router_id,
            neighbors=[n.model_dump() for n in intent.neighbors],
            import_policy=intent.import_policy,
            export_policy=intent.export_policy
        )
    except Exception as e:
        logger.error(f"[{device_name}] Template rendering failed: {e}")
        return False, f"Template rendering failed: {e}"

    # Dry-run mode
    if dry_run:
        logger.info(f"[{device_name}] DRY-RUN: Would apply BGP configuration")

        # Optionally save artifact
        artifact_dir = Path("artifacts")
        artifact_dir.mkdir(exist_ok=True)
        artifact_file = artifact_dir / f"{device_name}_bgp_service.xml"
        artifact_file.write_text(config_xml, encoding="utf-8")
        logger.info(f"[{device_name}] DRY-RUN: Saved artifact to {artifact_file}")

        return True, f"DRY-RUN: Would apply BGP config (artifact saved to {artifact_file})"

    # Apply configuration via NSO
    try:
        # For BGP, we need to use the NSO RESTCONF endpoint
        # Since BGP is complex, we'll use the generic POST method

        url = f"{client.base_url}/data/tailf-ncs:devices/device={device_name}/config"

        resp = client._safe_post(url, config_xml, content_type="application/yang-data+xml")

        if resp and resp.status_code in (200, 201, 204):
            logger.info(f"[{device_name}] ✓ BGP service deployed successfully")
            return True, "BGP service deployed successfully"
        else:
            logger.error(f"[{device_name}] ✗ BGP deployment failed")
            return False, "BGP deployment failed"

    except Exception as e:
        logger.error(f"[{device_name}] Exception during BGP deployment: {e}")
        return False, f"Exception: {e}"


def remove_bgp_service(
        client: NSOClient,
        device_name: str,
        local_as: int,
        dry_run: bool = False
) -> tuple[bool, str]:
    """
    Remove BGP peering service from a device.

    Args:
        client: NSO client
        device_name: Target device name
        local_as: BGP AS number to remove
        dry_run: If True, only show what would change

    Returns:
        Tuple of (success: bool, message: str)
    """
    logger.info(f"[{device_name}] Removing BGP peering service (AS {local_as})")

    if dry_run:
        logger.info(f"[{device_name}] DRY-RUN: Would remove BGP AS {local_as}")
        return True, f"DRY-RUN: Would remove BGP AS {local_as}"

    try:
        # Delete BGP process
        url = f"{client.base_url}/data/tailf-ncs:devices/device={device_name}/config/tailf-ned-cisco-ios:router/bgp={local_as}"

        resp = client._safe_delete(url)

        if resp and resp.status_code in (200, 204):
            logger.info(f"[{device_name}] ✓ BGP service removed successfully")
            return True, "BGP service removed successfully"
        else:
            logger.error(f"[{device_name}] ✗ BGP removal failed")
            return False, "BGP removal failed"

    except Exception as e:
        logger.error(f"[{device_name}] Exception during BGP removal: {e}")
        return False, f"Exception: {e}"