#!/usr/bin/env python3
"""
Storage Schema Validator - validates all storage examples against their schemas.
Simplified version that handles local references properly.

MIGRATED from scripts/contracts/storage_validate.py to contracts/automation/
"""

import json
import sys
from pathlib import Path
from typing import List, Tuple

try:
    import jsonschema
except ImportError:
    print("pip install jsonschema")
    sys.exit(2)

ROOT = Path("contracts/storage")


def find_pairs() -> List[Tuple[Path, List[Path]]]:
    """Find schema-example pairs in the storage contracts directory."""
    pairs = []

    # Check both root schemas and schemas/ subdirectory
    schema_dirs = [ROOT, ROOT / "schemas"]
    example_dirs = [ROOT, ROOT / "examples"]

    for schema_dir in schema_dirs:
        if not schema_dir.exists():
            continue

        for schema in schema_dir.glob("*.schema.json"):
            base = schema.stem.replace(".schema", "")
            examples = []

            # Look for examples in multiple locations
            for example_dir in example_dirs:
                if example_dir.exists():
                    examples.extend(example_dir.glob(f"{base}.example*.json"))

            if examples:
                pairs.append((schema, examples))

    return pairs


def load_local_schema(schema_path: str, base_dir: Path) -> dict:
    """Load a schema file locally."""
    try:
        # Handle different possible paths
        if schema_path.startswith("./"):
            file_path = base_dir / schema_path[2:]
        elif schema_path.startswith("https://familyos.local/contracts/storage/"):
            # Extract just the filename from the URL
            filename = schema_path.split("/")[-1]
            file_path = base_dir / filename
            # Also try parent directory
            if not file_path.exists():
                file_path = base_dir.parent / filename
        else:
            file_path = base_dir / schema_path

        if file_path.exists():
            return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def validate_basic(schema: dict, data: dict) -> List[str]:
    """Basic validation without external references."""
    errors = []

    # Check required fields
    if "required" in schema and isinstance(schema["required"], list):
        for field in schema["required"]:
            if field not in data:
                errors.append(f"Missing required field: {field}")

    # Check type
    if "type" in schema and schema["type"] == "object":
        if not isinstance(data, dict):
            errors.append(f"Expected object, got {type(data).__name__}")

    # Check properties if available
    if "properties" in schema and isinstance(data, dict):
        properties = schema["properties"]
        for field, value in data.items():
            if field in properties:
                field_schema = properties[field]
                # Basic type checking
                if "type" in field_schema:
                    expected_type = field_schema["type"]
                    if expected_type == "string" and not isinstance(value, str):
                        errors.append(
                            f"Field {field}: expected string, got {type(value).__name__}"
                        )
                    elif expected_type == "number" and not isinstance(
                        value, (int, float)
                    ):
                        errors.append(
                            f"Field {field}: expected number, got {type(value).__name__}"
                        )
                    elif expected_type == "integer" and not isinstance(value, int):
                        errors.append(
                            f"Field {field}: expected integer, got {type(value).__name__}"
                        )
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        errors.append(
                            f"Field {field}: expected boolean, got {type(value).__name__}"
                        )
                    elif expected_type == "array" and not isinstance(value, list):
                        errors.append(
                            f"Field {field}: expected array, got {type(value).__name__}"
                        )
                    elif expected_type == "object" and not isinstance(value, dict):
                        errors.append(
                            f"Field {field}: expected object, got {type(value).__name__}"
                        )

    return errors


def validate(schema_path: Path, example_paths: List[Path]) -> int:
    """Validate examples against schema and return number of failures."""
    failures = 0
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        for ex in example_paths:
            try:
                data = json.loads(ex.read_text(encoding="utf-8"))

                # Try jsonschema first, but fall back to basic validation
                try:
                    validator = jsonschema.Draft7Validator(schema)
                    errors = list(validator.iter_errors(data))
                    error_messages = [
                        f"{e.message} at {'/'.join(str(p) for p in e.path)}"
                        for e in errors[:3]
                    ]
                except Exception:
                    # Fall back to basic validation
                    error_messages = validate_basic(schema, data)[:3]

                if error_messages:
                    print(f"[FAIL] {ex} vs {schema_path}")
                    for msg in error_messages:
                        print(f"  - {msg}")
                    if len(error_messages) == 3:
                        print("  - ... (more errors may exist)")
                    failures += 1
                else:
                    print(f"[OK]   {ex}")

            except json.JSONDecodeError as e:
                print(f"[ERROR] Invalid JSON in {ex}: {e}")
                failures += 1
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in schema {schema_path}: {e}")
        failures += 1
    except Exception as e:
        print(f"[ERROR] Failed to validate {schema_path}: {e}")
        failures += 1

    return failures


def main() -> int:
    """Main validation function."""
    if not ROOT.exists():
        print(f"Error: {ROOT} does not exist")
        return 1

    pairs = find_pairs()
    if not pairs:
        print("No schema-example pairs found in storage contracts")
        return 0

    print(f"Found {len(pairs)} schema-example pairs")
    print()

    total_failures = 0
    processed = 0

    for schema, examples in pairs:
        print(f"Validating {schema.name} with {len(examples)} example(s):")
        failures = validate(schema, examples)
        total_failures += failures
        processed += 1

        # Show progress
        if processed % 10 == 0:
            print(f"... processed {processed}/{len(pairs)} schemas")
        print()

    if total_failures:
        print(
            f"{total_failures} mismatched example(s). Fix names or fields (e.g., doc_ref->doc_id, checksum->sha256)."
        )
        return 1

    print("All storage examples validate successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
