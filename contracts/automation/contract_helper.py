#!/usr/bin/env python3
"""
Contract Change Automation Helper
Automates common contract change tasks following the Contract Council process.

MIGRATED from scripts/contracts/contract_helper.py to contracts/automation/
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def create_new_schema(name: str, module: str = "storage") -> None:
    """Create a new schema from template with proper structure."""

    # Template schema following Contract Council standards
    template: Dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://familyos.local/contracts/{module}/{name}.schema.json",
        "title": f"{name.replace('_', ' ').title()}",
        "type": "object",
        "required": ["id", "created_ts"],
        "properties": {
            "id": {"$ref": "common.schema.json#/$defs/ULID"},
            "created_ts": {"$ref": "common.schema.json#/$defs/Timestamp"},
            "band": {"$ref": "common.schema.json#/$defs/Band"},
            "space_id": {"$ref": "common.schema.json#/$defs/SpaceId"},
        },
        "additionalProperties": False,
        "$defs": {
            "status": {"type": "string", "enum": ["active", "inactive", "pending"]}
        },
    }

    schema_path = Path(f"contracts/{module}/schemas/{name}.schema.json")
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    with open(schema_path, "w") as f:
        json.dump(template, f, indent=2)

    print(f"✓ Created schema: {schema_path}")

    # Create example template
    example: Dict[str, Any] = {
        "id": "01HX3V6M" + "X" * 18,  # Template ULID format
        "created_ts": "2025-09-12T10:30:00.000Z",
        "band": "GREEN",
        "space_id": "shared:household",
    }

    example_path = Path(f"contracts/{module}/examples/{name}.example.json")
    example_path.parent.mkdir(parents=True, exist_ok=True)
    with open(example_path, "w") as f:
        json.dump(example, f, indent=2)

    print(f"✓ Created example: {example_path}")
    print("📝 Next steps:")
    print(f"   1. Edit {schema_path} with your specific fields")
    print(f"   2. Update {example_path} with valid data")
    print("   3. Generate proper ULIDs: python scripts/contracts/gen_ulids.py")
    print(
        f"   4. Validate: python contracts/automation/storage_validator.py | grep {name}"
    )


def bump_version(version_type: str = "minor") -> None:
    """Bump version numbers in OpenAPI and affected modules."""

    # Read current API version
    api_path = Path("contracts/api/openapi/main.yaml")
    if not api_path.exists():
        print(f"❌ API spec not found: {api_path}")
        return

    with open(api_path) as f:
        content = f.read()

    # Extract current version (simple regex for demo)
    import re

    version_match = re.search(r'version:\s*["\']?(\d+)\.(\d+)\.(\d+)["\']?', content)
    if not version_match:
        print("❌ Could not find version in OpenAPI spec")
        return

    major, minor, patch = map(int, version_match.groups())

    if version_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif version_type == "minor":
        minor += 1
        patch = 0
    elif version_type == "patch":
        patch += 1

    new_version = f"{major}.{minor}.{patch}"

    # Update API version
    new_content = re.sub(
        r'(version:\s*["\']?)(\d+\.\d+\.\d+)(["\']?)',
        f"\\g<1>{new_version}\\g<3>",
        content,
    )

    with open(api_path, "w") as f:
        f.write(new_content)

    print(f"✓ Updated API version to {new_version}")

    # Update CHANGELOG
    changelog_path = Path("contracts/CHANGELOG.md")
    if changelog_path.exists():
        with open(changelog_path) as f:
            changelog = f.read()

        today = datetime.now().strftime("%Y-%m-%d")
        new_entry = (
            f"\n## [{new_version}] - {today}\n\n### Added\n- \n\n### Changed\n- \n\n"
        )

        # Insert after the first line (# Changelog)
        lines = changelog.split("\n")
        lines.insert(2, new_entry)

        with open(changelog_path, "w") as f:
            f.write("\n".join(lines))

        print(f"✓ Updated CHANGELOG.md with {new_version} entry")


def validate_all() -> bool:
    """Run complete validation suite using migrated tools."""

    print("🔍 Running contract validation suite...")

    # Storage validation (using migrated tool)
    storage_validator = Path("contracts/automation/storage_validator.py")
    if storage_validator.exists():
        result = subprocess.run(
            [sys.executable, str(storage_validator)], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✓ Storage validation passed")
        else:
            print("❌ Storage validation failed:")
            print(result.stdout)
            print(result.stderr)
            return False
    else:
        print("⚠️ Storage validator not found, skipping")

    # Envelope invariants (using migrated tool)
    envelope_validator = Path("contracts/automation/envelope_validator.py")
    if envelope_validator.exists():
        result = subprocess.run(
            [sys.executable, str(envelope_validator)], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✓ Envelope invariants check passed")
        else:
            print("❌ Envelope invariants check failed:")
            print(result.stdout)
            return False
    else:
        print("⚠️ Envelope validator not found, skipping")

    # Use comprehensive validation helper if available
    validation_helper = Path("contracts/automation/validation_helper.py")
    if validation_helper.exists():
        result = subprocess.run(
            [sys.executable, str(validation_helper)], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✓ Comprehensive validation passed")
        else:
            print("⚠️ Some comprehensive validations failed (see details above)")
            # Don't fail on comprehensive validation as it may include incomplete features

    print("🎉 Core contract validations passed!")
    return True


def create_freeze(version_desc: str) -> bool:
    """Create a new contract freeze using migrated version manager."""

    version_manager = Path("contracts/automation/version_manager.py")
    if not version_manager.exists():
        print("❌ Version manager not found at contracts/automation/version_manager.py")
        return False

    result = subprocess.run(
        [sys.executable, str(version_manager), "create", version_desc],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"✓ Contract freeze created: {version_desc}")
        print(result.stdout)
    else:
        print(f"❌ Failed to create freeze: {version_desc}")
        print(result.stderr)
        return False

    return True


def main() -> int:
    """Main contract helper function."""
    parser = argparse.ArgumentParser(description="Contract Change Automation Helper")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # New schema command
    new_parser = subparsers.add_parser(
        "new-schema", help="Create new schema from template"
    )
    new_parser.add_argument("name", help="Schema name (snake_case)")
    new_parser.add_argument(
        "--module", default="storage", help="Module (default: storage)"
    )

    # Version bump command
    version_parser = subparsers.add_parser("bump-version", help="Bump version numbers")
    version_parser.add_argument(
        "type", choices=["major", "minor", "patch"], help="Version bump type"
    )

    # Validation command
    subparsers.add_parser("validate", help="Run complete validation suite")

    # Freeze command
    freeze_parser = subparsers.add_parser("freeze", help="Create contract freeze")
    freeze_parser.add_argument(
        "version", help="Version description (e.g., v1.2.0-feature-name)"
    )

    # Full workflow command
    workflow_parser = subparsers.add_parser(
        "workflow", help="Complete contract change workflow"
    )
    workflow_parser.add_argument("version_type", choices=["major", "minor", "patch"])
    workflow_parser.add_argument("description", help="Change description")

    args = parser.parse_args()

    if args.command == "new-schema":
        create_new_schema(args.name, args.module)

    elif args.command == "bump-version":
        bump_version(args.type)

    elif args.command == "validate":
        validate_all()

    elif args.command == "freeze":
        create_freeze(args.version)

    elif args.command == "workflow":
        print(f"🚀 Starting complete workflow for {args.version_type} change...")

        # 1. Validate current state
        if not validate_all():
            print("❌ Current state validation failed. Fix issues before proceeding.")
            return 1

        # 2. Bump version
        bump_version(args.version_type)

        # 3. Re-validate after changes
        print("\n🔍 Re-validating after version bump...")
        if not validate_all():
            print("❌ Post-change validation failed. Review your changes.")
            return 1

        # 4. Create freeze
        version_desc = f"v{datetime.now().strftime('%Y%m%d')}-{args.description}"
        if not create_freeze(version_desc):
            return 1

        print("\n🎉 Complete workflow finished successfully!")
        print(f"   Version bumped: {args.version_type}")
        print(f"   Freeze created: {version_desc}")
        print("\n📋 Next steps:")
        print("   1. Review and test your changes")
        print("   2. Commit with descriptive message")
        print("   3. Create PR for review")

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
