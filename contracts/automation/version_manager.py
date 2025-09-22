#!/usr/bin/env python3
"""
Contract Version Manager - creates versioned frozen artifacts with SHA index.
Implements Contract Council's artifact preservation requirements.

MIGRATED from scripts/contracts/contracts_freeze.py to contracts/automation/
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

CONTRACTS_DIR = Path("contracts")
FROZEN_DIR = Path("contracts/_frozen")


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_current_version() -> str:
    """Get the current contract version from git or increment."""
    try:
        import subprocess

        # Try to get version from git tags
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            cwd=CONTRACTS_DIR.parent,
        )
        if result.returncode == 0:
            last_tag = result.stdout.strip()
            if last_tag.startswith("v"):
                last_tag = last_tag[1:]

            # Check if we have uncommitted changes to contracts
            result = subprocess.run(
                ["git", "status", "--porcelain", "contracts/"],
                capture_output=True,
                text=True,
                cwd=CONTRACTS_DIR.parent,
            )
            if result.stdout.strip():
                # Increment patch version for dirty changes
                parts = last_tag.split(".")
                if len(parts) >= 3:
                    patch = int(parts[2]) + 1
                    return f"{parts[0]}.{parts[1]}.{patch}-dev"
                else:
                    return f"{last_tag}.1-dev"
            else:
                return last_tag
        else:
            # No tags found, start with 1.0.0
            return "1.0.0-dev"
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Git not available or other error
        return "1.0.0-dev"


def freeze_contract_artifact(file_path: Path, base_dir: Path) -> Dict[str, Any]:
    """Freeze a single contract artifact."""
    relative_path = file_path.relative_to(base_dir)
    sha256_hash = calculate_sha256(file_path)

    # Read content
    if file_path.suffix in [".json", ".yaml", ".yml"]:
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="utf-8", errors="replace")
    else:
        # Binary files
        content = file_path.read_bytes().hex()

    return {
        "path": str(relative_path),
        "sha256": sha256_hash,
        "size": file_path.stat().st_size,
        "content": content,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
    }


def create_contract_freeze(version: str) -> Dict[str, Any]:
    """Create a complete freeze of all contract artifacts."""
    print(f"Creating contract freeze for version {version}...")

    # Find all contract files
    contract_files: List[Path] = []
    for pattern in ["**/*.json", "**/*.yaml", "**/*.yml", "**/*.md"]:
        contract_files.extend(CONTRACTS_DIR.glob(pattern))

    # Exclude frozen artifacts and temp files
    contract_files = [
        f
        for f in contract_files
        if not any(part.startswith("_") for part in f.parts)
        and f.name != "README.md"  # Skip root README
        and not f.name.startswith(".")
    ]

    print(f"Found {len(contract_files)} contract artifacts")

    # Freeze each artifact
    frozen_artifacts: List[Dict[str, Any]] = []
    for file_path in sorted(contract_files):
        artifact = freeze_contract_artifact(file_path, CONTRACTS_DIR)
        frozen_artifacts.append(artifact)
        print(f"  Frozen: {artifact['path']} ({artifact['sha256'][:8]}...)")

    # Create freeze manifest
    freeze_manifest = {
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": frozen_artifacts,
        "summary": {
            "total_artifacts": len(frozen_artifacts),
            "api_specs": len([a for a in frozen_artifacts if "api/" in a["path"]]),
            "event_schemas": len(
                [a for a in frozen_artifacts if "events/" in a["path"]]
            ),
            "storage_schemas": len(
                [a for a in frozen_artifacts if "storage/" in a["path"]]
            ),
            "policies": len([a for a in frozen_artifacts if "policy/" in a["path"]]),
        },
    }

    return freeze_manifest


def create_sha_index(freeze_manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Create SHA256 index for quick artifact lookup."""
    sha_index = {
        "version": freeze_manifest["version"],
        "created_at": freeze_manifest["created_at"],
        "index": {},
    }

    for artifact in freeze_manifest["artifacts"]:
        sha_index["index"][artifact["sha256"]] = {
            "path": artifact["path"],
            "size": artifact["size"],
            "frozen_at": artifact["frozen_at"],
        }

    return sha_index


def save_frozen_artifacts(freeze_manifest: Dict[str, Any]) -> bool:
    """Save frozen artifacts to disk."""
    version = freeze_manifest["version"]

    # Create frozen directory
    FROZEN_DIR.mkdir(exist_ok=True)

    # Save freeze manifest
    freeze_file = FROZEN_DIR / f"freeze-{version}.json"
    with open(freeze_file, "w", encoding="utf-8") as f:
        json.dump(freeze_manifest, f, indent=2, ensure_ascii=False)

    # Save SHA index
    sha_index = create_sha_index(freeze_manifest)
    index_file = FROZEN_DIR / f"sha-index-{version}.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(sha_index, f, indent=2, ensure_ascii=False)

    # Update latest symlinks/copies
    latest_freeze = FROZEN_DIR / "freeze-latest.json"
    latest_index = FROZEN_DIR / "sha-index-latest.json"

    try:
        # Copy instead of symlink for Windows compatibility
        import shutil

        shutil.copy2(freeze_file, latest_freeze)
        shutil.copy2(index_file, latest_index)
    except Exception as e:
        print(f"Warning: Could not update latest links: {e}")

    print("\\nFrozen artifacts saved:")
    print(f"  Freeze manifest: {freeze_file}")
    print(f"  SHA index: {index_file}")
    print(f"  Latest links: {latest_freeze}, {latest_index}")

    return True


def list_frozen_versions() -> List[str]:
    """List all available frozen versions."""
    if not FROZEN_DIR.exists():
        return []

    versions: List[str] = []
    for freeze_file in FROZEN_DIR.glob("freeze-*.json"):
        if not freeze_file.name.endswith("-latest.json"):
            version = freeze_file.stem.replace("freeze-", "")
            versions.append(version)

    return sorted(versions)


def main() -> int:
    """Main freeze command."""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            versions = list_frozen_versions()
            if versions:
                print("Available frozen contract versions:")
                for version in versions:
                    print(f"  {version}")
            else:
                print("No frozen contract versions found.")
            return 0

        elif command == "create":
            version = sys.argv[2] if len(sys.argv) > 2 else get_current_version()
        else:
            print(f"Unknown command: {command}")
            return 1
    else:
        version = get_current_version()

    # Check if contracts directory exists
    if not CONTRACTS_DIR.exists():
        print(f"Contracts directory not found: {CONTRACTS_DIR}")
        return 1

    # Create freeze
    freeze_manifest = create_contract_freeze(version)

    # Save artifacts
    if save_frozen_artifacts(freeze_manifest):
        print(f"\\nContract freeze {version} created successfully!")
        print(f"Summary: {freeze_manifest['summary']}")
        return 0
    else:
        print("Failed to save frozen artifacts")
        return 1


if __name__ == "__main__":
    sys.exit(main())
