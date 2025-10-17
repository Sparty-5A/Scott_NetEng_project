"""
Intent reconciliation engine for network configuration.

This module compares desired state (intent) with actual state (from devices)
and calculates the minimal set of changes needed to achieve the intent.
"""

from dataclasses import dataclass
from typing import Any

from loguru import logger

from nso_orchestration.automation.intent_models import (
    DeviceIntent,
    NetworkIntent,
)
from nso_orchestration.automation.nso_client import NSOClient


@dataclass
class Change:
    """Represents a single configuration change."""

    action: str  # "create", "update", "delete"
    device: str
    resource_type: str  # "loopback", "bgp_neighbor", etc.
    resource_id: str
    current: dict[str, Any] | None
    desired: dict[str, Any] | None

    def __str__(self) -> str:
        if self.action == "create":
            return f"[{self.device}] CREATE {self.resource_type} {self.resource_id}"
        elif self.action == "delete":
            return f"[{self.device}] DELETE {self.resource_type} {self.resource_id}"
        else:
            return f"[{self.device}] UPDATE {self.resource_type} {self.resource_id}"


class IntentEngine:
    """Engine for reconciling network intent with actual state."""

    def __init__(self, nso_client: NSOClient):
        """
        Initialize intent engine.

        Args:
            nso_client: NSO client for querying and configuring devices
        """
        self.client = nso_client

    def get_current_loopbacks(self, device_name: str) -> dict[str, dict[str, Any]]:
        """
        Get current loopback configuration from device.

        Args:
            device_name: Name of device to query

        Returns:
            Dict mapping loopback ID to configuration
            Example: {"100": {"ip": "10.100.100.1", "netmask": "255.255.255.255", "description": "Mgmt"}}
        """
        logger.info(f"Querying current loopbacks from {device_name}")

        # Sync device first to get latest config
        self.client.sync_from_device(device_name)

        # Get full device config
        config = self.client.get_device_config(device_name)
        if not config:
            logger.warning(f"Could not retrieve config from {device_name}")
            return {}

        # Extract loopbacks from config
        loopbacks = {}

        try:
            # Navigate to interface config (structure varies by NED)
            interfaces = (
                config.get("tailf-ncs:config", {})
                .get("tailf-ned-cisco-ios:interface", {})
                .get("Loopback", [])
            )

            for lb in interfaces:
                lb_id = lb.get("name")
                if not lb_id:
                    continue

                # Extract IP config
                ip_config = lb.get("ip", {}).get("address", {}).get("primary", {})

                loopbacks[str(lb_id)] = {
                    "ip": ip_config.get("address"),
                    "netmask": ip_config.get("mask"),
                    "description": lb.get("description"),
                }

                logger.debug(f"Found Loopback{lb_id}: {loopbacks[lb_id]}")

        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing loopback config from {device_name}: {e}")
            return {}

        logger.info(f"Found {len(loopbacks)} loopbacks on {device_name}")
        return loopbacks

    def calculate_loopback_changes(
        self, device_intent: DeviceIntent
    ) -> list[Change]:
        """
        Calculate changes needed to achieve desired loopback state.

        Args:
            device_intent: Device intent including loopback config and deletion policy

        Returns:
            List of changes needed
        """
        changes = []
        device_name = device_intent.name
        desired_loopbacks = device_intent.loopbacks
        delete_unmanaged = device_intent.delete_unmanaged_loopbacks

        # Get current state
        current_loopbacks = self.get_current_loopbacks(device_name)

        # Build desired state map
        desired_map = {str(lb.id): lb for lb in desired_loopbacks}

        # Find creates and updates
        for lb_id, desired_lb in desired_map.items():
            if lb_id not in current_loopbacks:
                # CREATE: Loopback doesn't exist
                changes.append(
                    Change(
                        action="create",
                        device=device_name,
                        resource_type="loopback",
                        resource_id=lb_id,
                        current=None,
                        desired={
                            "ip": desired_lb.ipv4,
                            "netmask": desired_lb.netmask,
                            "description": desired_lb.description,
                        },
                    )
                )
            else:
                # Check if UPDATE needed
                current = current_loopbacks[lb_id]
                needs_update = False

                if current.get("ip") != desired_lb.ipv4:
                    needs_update = True
                if current.get("netmask") != desired_lb.netmask:
                    needs_update = True
                if current.get("description") != desired_lb.description:
                    needs_update = True

                if needs_update:
                    changes.append(
                        Change(
                            action="update",
                            device=device_name,
                            resource_type="loopback",
                            resource_id=lb_id,
                            current=current,
                            desired={
                                "ip": desired_lb.ipv4,
                                "netmask": desired_lb.netmask,
                                "description": desired_lb.description,
                            },
                        )
                    )

        # Find deletes (loopbacks that exist but aren't in intent)
        # Only delete if explicitly enabled
        unmanaged_loopbacks = [lb_id for lb_id in current_loopbacks if lb_id not in desired_map]

        if unmanaged_loopbacks:
            if delete_unmanaged:
                logger.warning(
                    f"[{device_name}] delete_unmanaged_loopbacks=True: "
                    f"Will DELETE {len(unmanaged_loopbacks)} loopbacks not in intent: {unmanaged_loopbacks}"
                )
                for lb_id in unmanaged_loopbacks:
                    changes.append(
                        Change(
                            action="delete",
                            device=device_name,
                            resource_type="loopback",
                            resource_id=lb_id,
                            current=current_loopbacks[lb_id],
                            desired=None,
                        )
                    )
            else:
                logger.info(
                    f"[{device_name}] delete_unmanaged_loopbacks=False (safe mode): "
                    f"Ignoring {len(unmanaged_loopbacks)} unmanaged loopbacks: {unmanaged_loopbacks}"
                )

        return changes

    def calculate_changes(self, intent: NetworkIntent) -> list[Change]:
        """
        Calculate all changes needed to achieve network intent.

        Args:
            intent: Desired network state

        Returns:
            List of all changes across all devices
        """
        all_changes = []

        for device_intent in intent.devices:
            logger.info(f"Calculating changes for {device_intent.name}")

            # Calculate loopback changes
            loopback_changes = self.calculate_loopback_changes(
                device_intent.name, device_intent.loopbacks
            )
            all_changes.extend(loopback_changes)

            # TODO: Add BGP changes calculation
            # if device_intent.bgp:
            #     bgp_changes = self.calculate_bgp_changes(device_intent.name, device_intent.bgp)
            #     all_changes.extend(bgp_changes)

        return all_changes

    def apply_change(self, change: Change, dry_run: bool = False) -> bool:
        """
        Apply a single configuration change.

        Args:
            change: Change to apply
            dry_run: If True, only show what would change

        Returns:
            True if successful
        """
        if dry_run:
            logger.info(f"[DRY-RUN] Would apply: {change}")
            return True

        logger.info(f"Applying: {change}")

        if change.resource_type == "loopback":
            if change.action in ("create", "update"):
                # Configure loopback
                success = self.client.configure_loopback(
                    device_name=change.device,
                    loopback_id=change.resource_id,
                    ip_address=change.desired["ip"],
                    netmask=change.desired["netmask"],
                    description=change.desired.get("description"),
                )
                return success

            elif change.action == "delete":
                # Delete loopback
                success = self.client.delete_loopback(
                    device_name=change.device, loopback_id=change.resource_id
                )
                return success

        return False

    def apply_intent(
        self, intent: NetworkIntent, dry_run: bool = False
    ) -> tuple[int, int]:
        """
        Apply network intent - reconcile desired state with actual state.

        Args:
            intent: Desired network state
            dry_run: If True, only show what would change without applying

        Returns:
            Tuple of (successful_changes, failed_changes)
        """
        logger.info("=" * 70)
        logger.info(f"{'DRY-RUN: ' if dry_run else ''}Applying network intent")
        logger.info("=" * 70)

        # Calculate changes
        changes = self.calculate_changes(intent)

        if not changes:
            logger.info("✓ No changes needed - network is in desired state")
            return 0, 0

        # Show summary
        creates = [c for c in changes if c.action == "create"]
        updates = [c for c in changes if c.action == "update"]
        deletes = [c for c in changes if c.action == "delete"]

        logger.info(f"Planned changes: {len(changes)} total")
        if creates:
            logger.info(f"  - {len(creates)} creates")
        if updates:
            logger.info(f"  - {len(updates)} updates")
        if deletes:
            logger.info(f"  - {len(deletes)} deletes")
        logger.info("")

        # Apply changes
        success_count = 0
        failure_count = 0

        for change in changes:
            try:
                if self.apply_change(change, dry_run=dry_run):
                    success_count += 1
                else:
                    failure_count += 1
                    logger.error(f"✗ Failed to apply: {change}")
            except Exception as e:
                failure_count += 1
                logger.error(f"✗ Exception applying {change}: {e}")

        # Summary
        logger.info("")
        logger.info("=" * 70)
        if dry_run:
            logger.info(f"DRY-RUN Complete: {success_count} changes would be applied")
        else:
            logger.info(
                f"Intent reconciliation complete: {success_count} succeeded, {failure_count} failed"
            )
        logger.info("=" * 70)

        return success_count, failure_count
