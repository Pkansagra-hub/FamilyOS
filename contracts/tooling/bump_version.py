#!/usr/bin/env python3
"""
MemoryOS Contract Version Bumper
================================

Utility to bump module versions following SemVer and update version history.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml


def load_versions(versions_file: Path) -> Dict[str, Any]:
    """Load versions.yaml file."""
    if not versions_file.exists():
        return {
            "current": "0.1.0",
            "history": [],
            "versioning": {
                "scheme": "semver",
                "deprecation_window": "90d",
                "support_policy": "Last 2 major versions supported",
            },
        }

    with open(versions_file, "r") as f:
        return yaml.safe_load(f)


def save_versions(versions_file: Path, versions: Dict[str, Any]) -> None:
    """Save versions.yaml file."""
    with open(versions_file, "w") as f:
        yaml.dump(versions, f, default_flow_style=False, sort_keys=False)


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse SemVer version string."""
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")
    return tuple(int(p) for p in parts)


def bump_version(current: str, bump_type: str) -> str:
    """Bump version according to SemVer rules."""
    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def update_history(
    versions: Dict[str, Any],
    new_version: str,
    changes: list[str],
    breaking_changes: list[str] = None,
) -> None:
    """Update version history."""
    if "history" not in versions:
        versions["history"] = []

    history_entry = {
        "version": new_version,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "changes": changes,
    }

    if breaking_changes:
        history_entry["breaking_changes"] = breaking_changes
        history_entry["migration_notes"] = "See migration guide for breaking changes"
    else:
        history_entry["breaking_changes"] = []

    versions["history"].insert(0, history_entry)


def main():
    parser = argparse.ArgumentParser(description="Bump MemoryOS contract versions")
    parser.add_argument("module", help="Module name to bump version for")
    parser.add_argument(
        "bump_type", choices=["major", "minor", "patch"], help="Type of version bump"
    )
    parser.add_argument("changes", nargs="+", help="List of changes")
    parser.add_argument("--breaking", nargs="*", help="List of breaking changes")
    parser.add_argument(
        "--contracts-root", default=".", help="Contracts root directory"
    )

    args = parser.parse_args()

    # Find module directory
    contracts_root = Path(args.contracts_root)
    module_dir = contracts_root / "modules" / args.module

    if not module_dir.exists():
        print(f"❌ Module directory not found: {module_dir}")
        sys.exit(1)

    versions_file = module_dir / "versions.yaml"
    versions = load_versions(versions_file)

    # Get current version
    current_version = versions.get("current", "0.0.0")
    print(f"📦 Module: {args.module}")
    print(f"📄 Current version: {current_version}")

    # Bump version
    try:
        new_version = bump_version(current_version, args.bump_type)
        print(f"⬆️  New version: {new_version}")

        # Update versions
        versions["current"] = new_version
        update_history(versions, new_version, args.changes, args.breaking)

        # Save file
        save_versions(versions_file, versions)

        print("✅ Version bumped successfully!")
        print(f"📝 Changes: {', '.join(args.changes)}")

        if args.breaking:
            print(f"⚠️  Breaking changes: {', '.join(args.breaking)}")

        print("\n📋 Next steps:")
        print("1. Review and commit the changes")
        print(f"2. Tag the release: git tag contracts-{args.module}-{new_version}")
        print("3. Update the implementation to match the new contracts")

    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
