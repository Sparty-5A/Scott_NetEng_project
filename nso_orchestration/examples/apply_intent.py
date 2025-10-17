#!/usr/bin/env python3
"""
Apply network intent to devices via NSO.

This script reads the intent file (desired state), compares it to
actual device state, and applies only the necessary changes.
"""

import sys
from pathlib import Path
from loguru import logger
from decouple import config
import yaml
import json

from nso_orchestration.automation.nso_client import NSOClient
from nso_orchestration.automation.intent_models import NetworkIntent
from nso_orchestration.automation.intent_engine import IntentEngine


def load_intent_from_yaml(file_path: Path) -> NetworkIntent:
    """
    Load and validate network intent from YAML file.

    Args:
        file_path: Path to YAML intent file

    Returns:
        Validated NetworkIntent object

    Raises:
        ValidationError: If intent file is invalid
    """
    logger.info(f"Loading intent from {file_path}")

    with open(file_path) as f:
        intent_data = yaml.safe_load(f)

    # Validate with Pydantic
    intent = NetworkIntent(**intent_data)
    logger.info(f"✓ Intent validated: {len(intent.devices)} devices")

    return intent


def main():
    """Main orchestration logic."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Apply network intent via NSO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run (show changes without applying)
  python apply_intent.py --dry-run

  # Apply intent
  python apply_intent.py

  # Use custom intent file
  python apply_intent.py --intent custom_intent.yaml
        """
    )
    parser.add_argument(
        "--intent",
        type=Path,
        default=Path("intent/network_intent.yaml"),
        help="Path to intent file (default: intent/network_intent.yaml)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without applying them"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )

    args = parser.parse_args()

    # Resolve intent file path
    intent_file = args.intent
    if not intent_file.is_absolute():
        # Relative to script directory
        script_dir = Path(__file__).parent.parent
        intent_file = script_dir / intent_file

    if not intent_file.exists():
        logger.error(f"Intent file not found: {intent_file}")
        return 1

    try:
        # Load and validate intent
        intent = load_intent_from_yaml(intent_file)

        # Connect to NSO
        nso_host = config("NSO_HOST", default="10.10.20.49")
        logger.info(f"Connecting to NSO at {nso_host}")

        with NSOClient(host=nso_host) as client:
            # Health check
            if not client.health_check():
                logger.error("NSO health check failed")
                return 1

            # Create intent engine
            engine = IntentEngine(nso_client=client)

            # Apply intent
            success, failed = engine.apply_intent(intent, dry_run=args.dry_run)

            # Output results
            if args.json:
                result = {
                    "dry_run": args.dry_run,
                    "intent_file": str(intent_file),
                    "devices": len(intent.devices),
                    "changes": {
                        "successful": success,
                        "failed": failed
                    },
                    "status": "success" if failed == 0 else "partial_failure"
                }
                print(json.dumps(result, indent=2))

            # Return exit code
            return 0 if failed == 0 else 1

    except Exception as e:
        logger.exception(f"Error applying intent: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())