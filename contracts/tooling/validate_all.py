#!/usr/bin/env python3
"""
MemoryOS Contracts Validation Tool
==================================

Validates all schemas and contracts across the OBCF structure.
Supports JSON Schema validation, OpenAPI validation, and cross-references.
"""

import json
import pathlib
import sys
from typing import Any, List

import yaml
from jsonschema import Draft202012Validator as Validator
from jsonschema.exceptions import SchemaError, ValidationError

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMMON_SCHEMA = ROOT / "globals" / "storage" / "common.schema.json"
ENVELOPE_SCHEMA = ROOT / "globals" / "events" / "envelope.schema.json"


class ContractsValidator:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.validated_schemas = 0
        self.validated_examples = 0

    def load_json(self, path: pathlib.Path) -> Any:
        """Load JSON file with error handling."""
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON parse error in {path}: {e}")
            return None
        except Exception as e:
            self.errors.append(f"Error reading {path}: {e}")
            return None

    def load_yaml(self, path: pathlib.Path) -> Any:
        """Load YAML file with error handling."""
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parse error in {path}: {e}")
            return None
        except Exception as e:
            self.errors.append(f"Error reading {path}: {e}")
            return None

    def validate_json_schema(self, schema_path: pathlib.Path) -> bool:
        """Validate a JSON Schema file."""
        schema = self.load_json(schema_path)
        if schema is None:
            return False

        try:
            # Ensure $id for absolute refs
            if "$id" not in schema:
                schema["$id"] = schema_path.as_uri()

            # Validate schema itself
            Validator.check_schema(schema)
            self.validated_schemas += 1
            print(f"✅ Schema OK: {schema_path.relative_to(ROOT)}")
            return True

        except SchemaError as e:
            self.errors.append(f"Invalid schema {schema_path}: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Schema validation error {schema_path}: {e}")
            return False

    def validate_examples_against_schema(
        self, schema_path: pathlib.Path, examples_dir: pathlib.Path
    ) -> bool:
        """Validate example files against a schema."""
        if not examples_dir.exists():
            return True  # No examples to validate

        schema = self.load_json(schema_path)
        if schema is None:
            return False

        try:
            validator = Validator(schema)
            success = True

            for example_file in examples_dir.glob("*.json"):
                example = self.load_json(example_file)
                if example is None:
                    success = False
                    continue

                try:
                    validator.validate(example)
                    self.validated_examples += 1
                    print(f"✅ Example OK: {example_file.relative_to(ROOT)}")
                except ValidationError as e:
                    self.errors.append(f"Example validation failed {example_file}: {e}")
                    success = False

            return success

        except Exception as e:
            self.errors.append(f"Error validating examples for {schema_path}: {e}")
            return False

    def validate_module_versions(self, module_path: pathlib.Path) -> bool:
        """Validate module versions.yaml format."""
        versions_file = module_path / "versions.yaml"
        if not versions_file.exists():
            self.warnings.append(f"Missing versions.yaml in {module_path.name}")
            return True

        versions = self.load_yaml(versions_file)
        if versions is None:
            return False

        # Check required fields
        required_fields = ["current", "history"]
        for field in required_fields:
            if field not in versions:
                self.errors.append(
                    f"Missing required field '{field}' in {versions_file}"
                )
                return False

        # Validate version format
        current_version = versions["current"]
        if not self.is_valid_semver(current_version):
            self.errors.append(
                f"Invalid SemVer format '{current_version}' in {versions_file}"
            )
            return False

        print(f"✅ Versions OK: {module_path.name} v{current_version}")
        return True

    def is_valid_semver(self, version: str) -> bool:
        """Check if string is valid SemVer format."""
        import re

        pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)))*(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
        return bool(re.match(pattern, version))

    def validate_openapi_spec(self, spec_path: pathlib.Path) -> bool:
        """Validate OpenAPI specification."""
        try:
            # Try to import openapi-spec-validator if available
            from openapi_spec_validator import validate_spec

            spec = self.load_yaml(spec_path)
            if spec is None:
                return False

            validate_spec(spec)
            print(f"✅ OpenAPI OK: {spec_path.relative_to(ROOT)}")
            return True

        except ImportError:
            self.warnings.append(
                "openapi-spec-validator not installed, skipping OpenAPI validation"
            )
            return True
        except Exception as e:
            self.errors.append(f"OpenAPI validation failed {spec_path}: {e}")
            return False

    def validate_module(self, module_path: pathlib.Path) -> bool:
        """Validate a complete module."""
        if not module_path.is_dir():
            return True

        print(f"\n🔍 Validating module: {module_path.name}")
        success = True

        # Validate versions
        success &= self.validate_module_versions(module_path)

        # Validate storage schemas
        schemas_dir = module_path / "storage" / "schemas"
        if schemas_dir.exists():
            for schema_file in schemas_dir.glob("*.schema.json"):
                success &= self.validate_json_schema(schema_file)

                # Check for corresponding examples
                examples_dir = module_path / "tests" / "examples" / schema_file.stem
                if examples_dir.exists():
                    success &= self.validate_examples_against_schema(
                        schema_file, examples_dir
                    )

        # Validate OpenAPI specs
        api_spec = module_path / "api" / "openapi.yaml"
        if api_spec.exists():
            success &= self.validate_openapi_spec(api_spec)

        return success

    def validate_globals(self) -> bool:
        """Validate global schemas and definitions."""
        print("🌍 Validating global schemas...")
        success = True

        # Validate common storage schema
        common_schema = ROOT / "globals" / "storage" / "common.schema.json"
        if common_schema.exists():
            success &= self.validate_json_schema(common_schema)

        # Validate event envelope
        envelope_schema = ROOT / "globals" / "events" / "envelope.schema.json"
        if envelope_schema.exists():
            success &= self.validate_json_schema(envelope_schema)

        # Validate OpenAPI common components
        common_api = ROOT / "globals" / "api" / "openapi.common.yaml"
        if common_api.exists():
            success &= self.validate_openapi_spec(common_api)

        return success

    def validate_all(self) -> bool:
        """Validate entire contracts repository."""
        print("🏗️  MemoryOS Contracts Validation")
        print("=" * 40)

        success = True

        # Validate globals first
        success &= self.validate_globals()

        # Validate all modules
        modules_dir = ROOT / "modules"
        if modules_dir.exists():
            for module_dir in modules_dir.iterdir():
                if module_dir.is_dir():
                    success &= self.validate_module(module_dir)

        return success

    def print_summary(self, success: bool):
        """Print validation summary."""
        print("\n" + "=" * 40)
        print("📊 VALIDATION SUMMARY")
        print("=" * 40)
        print(f"✅ Schemas validated: {self.validated_schemas}")
        print(f"✅ Examples validated: {self.validated_examples}")

        if self.warnings:
            print(f"⚠️  Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"   ⚠️  {warning}")

        if self.errors:
            print(f"❌ Errors: {len(self.errors)}")
            for error in self.errors:
                print(f"   ❌ {error}")

        if success and not self.errors:
            print("\n🎉 ALL CONTRACTS VALID!")
        else:
            print("\n💥 VALIDATION FAILED!")


def main():
    """Main validation entry point."""
    validator = ContractsValidator()
    success = validator.validate_all()
    validator.print_summary(success)

    # Exit with error code if validation failed
    sys.exit(0 if success and not validator.errors else 1)


if __name__ == "__main__":
    main()
