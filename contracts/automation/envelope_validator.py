#!/usr/bin/env python3
"""
Envelope Invariants Checker
Validates that frozen envelope schema invariants are never removed.

Part of Contract Council's stabilization plan.
MIGRATED from scripts/contracts/check_envelope_invariants.py to contracts/automation/
"""

import json
import sys
from pathlib import Path
from typing import List


def check_envelope_invariants() -> bool:
    """Check that frozen envelope invariants are preserved."""

    # Define frozen invariants that must never be removed
    FROZEN_INVARIANTS: List[str] = [
        "band",
        "obligations",
        "policy_version",
        "id",
        "ts",
        "topic",
        "actor",
        "device",
        "space_id",
        "qos",
        "hashes",
        "signature",
    ]

    envelope_path = Path("contracts/events/envelope.schema.json")

    if not envelope_path.exists():
        print(f"ERROR: Envelope schema not found: {envelope_path}")
        return False

    try:
        with open(envelope_path) as f:
            schema = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in envelope schema: {e}")
        return False

    # Check required fields
    required_fields = schema.get("required", [])

    # Find missing invariants
    missing_invariants = [
        field for field in FROZEN_INVARIANTS if field not in required_fields
    ]

    if missing_invariants:
        print(f"ERROR: Frozen envelope invariants removed: {missing_invariants}")
        print(f"Current required fields: {required_fields}")
        print(f"Must include all of: {FROZEN_INVARIANTS}")
        return False

    print("[OK] All frozen envelope invariants preserved")
    print(f"[OK] Validated {len(FROZEN_INVARIANTS)} required invariant fields")

    return True


def main() -> int:
    """Main envelope validation function."""
    if not check_envelope_invariants():
        return 1
    print("[OK] Envelope invariants check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
