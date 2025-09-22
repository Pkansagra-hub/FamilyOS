#!/usr/bin/env python3
"""
Enhanced Contract Automation Suite
Comprehensive tooling for contract management, validation, and automation.

Consolidated from scattered scripts into a unified automation system.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple


class ContractAutomationSuite:
    """Main automation suite for contract management."""

    def __init__(self):
        self.contracts_root = Path("contracts")
        self.scripts_root = Path("scripts/contracts")

    def validate_environment(self) -> bool:
        """Validate that we're in the right environment."""
        if not self.contracts_root.exists():
            print("❌ contracts/ directory not found. Run from repository root.")
            return False
        return True

    # === SCHEMA MANAGEMENT ===

    def create_new_schema(
        self, name: str, module: str = "storage", template_type: str = "basic"
    ) -> bool:
        """Create a new schema from enhanced templates."""

        templates = {
            "basic": self._get_basic_template,
            "brain_inspired": self._get_brain_inspired_template,
            "pipeline": self._get_pipeline_template,
            "integration": self._get_integration_template,
        }

        if template_type not in templates:
            print(f"❌ Unknown template type: {template_type}")
            print(f"Available: {', '.join(templates.keys())}")
            return False

        template_func = templates[template_type]
        template = template_func(name, module)

        # Create schema file
        schema_dir = self.contracts_root / module / "schemas"
        schema_dir.mkdir(parents=True, exist_ok=True)
        schema_path = schema_dir / f"{name}.schema.json"

        with open(schema_path, "w") as f:
            json.dump(template, f, indent=2)

        print(f"✓ Created schema: {schema_path}")

        # Create example
        example = self._create_example_for_template(template, template_type)
        example_dir = self.contracts_root / module / "examples"
        example_dir.mkdir(parents=True, exist_ok=True)
        example_path = example_dir / f"{name}.example.json"

        with open(example_path, "w") as f:
            json.dump(example, f, indent=2)

        print(f"✓ Created example: {example_path}")
        print(f"📝 Template type: {template_type}")
        print("📝 Next steps:")
        print(f"   1. Customize {schema_path} for your specific use case")
        print(f"   2. Update {example_path} with realistic data")
        print("   3. Validate: python contracts/automation/contract_suite.py validate")

        return True

    def _get_basic_template(self, name: str, module: str) -> Dict[str, Any]:
        """Basic contract template."""
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"https://familyos.local/contracts/{module}/{name}.schema.json",
            "title": f"{name.replace('_', ' ').title()}",
            "description": f"Schema for {name} in {module} module",
            "type": "object",
            "required": ["id", "created_ts", "cognitive_trace_id"],
            "properties": {
                "id": {"$ref": "common.schema.json#/$defs/ULID"},
                "created_ts": {"$ref": "common.schema.json#/$defs/Timestamp"},
                "cognitive_trace_id": {"$ref": "common.schema.json#/$defs/ULID"},
                "band": {"$ref": "common.schema.json#/$defs/Band"},
                "space_id": {"$ref": "common.schema.json#/$defs/SpaceId"},
            },
            "additionalProperties": False,
        }

    def _get_brain_inspired_template(self, name: str, module: str) -> Dict[str, Any]:
        """Brain-inspired contract template with neuroanatomical structure."""
        template = self._get_basic_template(name, module)

        # Add brain-inspired fields
        template["properties"].update(
            {
                "neural_substrate": {
                    "type": "object",
                    "description": "Neural substrate information",
                    "properties": {
                        "brain_region": {
                            "type": "string",
                            "enum": [
                                "thalamus",
                                "hippocampus",
                                "prefrontal_cortex",
                                "basal_ganglia",
                                "motor_cortex",
                                "sensory_cortex",
                            ],
                        },
                        "neural_circuit": {"type": "string"},
                        "neurotransmitter_systems": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "dopamine",
                                    "serotonin",
                                    "acetylcholine",
                                    "norepinephrine",
                                    "gaba",
                                    "glutamate",
                                ],
                            },
                        },
                        "oscillatory_patterns": {
                            "type": "object",
                            "properties": {
                                "frequency_band": {
                                    "type": "string",
                                    "enum": [
                                        "delta",
                                        "theta",
                                        "alpha",
                                        "beta",
                                        "gamma",
                                    ],
                                },
                                "amplitude": {"type": "number", "minimum": 0},
                                "phase_coherence": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                },
                            },
                        },
                    },
                    "required": ["brain_region"],
                },
                "cognitive_functions": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "attention",
                            "memory",
                            "executive_control",
                            "learning",
                            "decision_making",
                            "motor_control",
                        ],
                    },
                },
                "processing_mode": {
                    "type": "string",
                    "enum": ["fast_path", "smart_path", "cognitive_deliberation"],
                    "description": "Processing pathway for this cognitive operation",
                },
            }
        )

        template["required"].extend(["neural_substrate", "cognitive_functions"])

        return template

    def _get_pipeline_template(self, name: str, module: str) -> Dict[str, Any]:
        """Pipeline-specific contract template."""
        template = self._get_brain_inspired_template(name, module)

        # Extract pipeline ID from name (P01, P02, etc.)
        pipeline_match = re.search(r"P(\d{2})", name.upper())
        pipeline_id = pipeline_match.group(0) if pipeline_match else "P00"

        pipeline_descriptions = {
            "P01": "Recall/Read - Hippocampal-Cortical Retrieval",
            "P02": "Write/Ingest - Hippocampal Memory Formation",
            "P03": "Consolidation/Forgetting - Sleep-Dependent Consolidation",
            "P04": "Arbitration/Action - Basal Ganglia Action Selection",
            "P05": "Prospective/Triggers - Prefrontal Future Memory",
            "P06": "Learning/Neuromod - Dopaminergic Learning Signals",
            # Add more pipeline descriptions...
        }

        template["description"] = (
            f"Pipeline {pipeline_id}: {pipeline_descriptions.get(pipeline_id, 'Unknown Pipeline')}"
        )

        # Add pipeline-specific fields
        template["properties"].update(
            {
                "pipeline_id": {
                    "type": "string",
                    "const": pipeline_id,
                    "description": f"Pipeline identifier: {pipeline_id}",
                },
                "input_events": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Event types that trigger this pipeline",
                },
                "output_events": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Event types produced by this pipeline",
                },
                "processing_stage": {
                    "type": "string",
                    "enum": [
                        "input_validation",
                        "cognitive_processing",
                        "brain_simulation",
                        "output_generation",
                        "event_emission",
                    ],
                },
                "performance_sla": {
                    "type": "object",
                    "properties": {
                        "max_latency_ms": {"type": "integer", "minimum": 1},
                        "throughput_per_sec": {"type": "integer", "minimum": 1},
                        "accuracy_threshold": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },
                    },
                },
            }
        )

        template["required"].extend(["pipeline_id", "processing_stage"])

        return template

    def _get_integration_template(self, name: str, module: str) -> Dict[str, Any]:
        """Integration contract template for cross-system coordination."""
        template = self._get_brain_inspired_template(name, module)

        template["properties"].update(
            {
                "integration_type": {
                    "type": "string",
                    "enum": [
                        "memory_consolidation",
                        "attention_coordination",
                        "executive_control",
                        "motor_coordination",
                        "learning_integration",
                    ],
                },
                "coordinated_systems": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "system_name": {"type": "string"},
                            "brain_region": {"type": "string"},
                            "coordination_type": {
                                "type": "string",
                                "enum": [
                                    "synchronous",
                                    "asynchronous",
                                    "competitive",
                                    "cooperative",
                                ],
                            },
                        },
                        "required": ["system_name", "coordination_type"],
                    },
                },
                "coordination_mechanism": {
                    "type": "object",
                    "properties": {
                        "synchronization_method": {
                            "type": "string",
                            "enum": [
                                "oscillatory_coupling",
                                "event_driven",
                                "resource_sharing",
                            ],
                        },
                        "conflict_resolution": {
                            "type": "string",
                            "enum": [
                                "priority_based",
                                "competitive_inhibition",
                                "cooperative_binding",
                            ],
                        },
                    },
                },
            }
        )

        template["required"].extend(["integration_type", "coordinated_systems"])

        return template

    def _create_example_for_template(
        self, template: Dict[str, Any], template_type: str
    ) -> Dict[str, Any]:
        """Create appropriate example data for template type."""

        base_example: Dict[str, Any] = {
            "id": "01JA9X6M" + "X" * 18,  # Template ULID
            "created_ts": "2025-09-16T10:30:00.000Z",
            "cognitive_trace_id": "01JA9X6N" + "Y" * 18,
            "band": "GREEN",
            "space_id": "shared:household",
        }

        if template_type == "brain_inspired":
            base_example["neural_substrate"] = {
                "brain_region": "thalamus",
                "neural_circuit": "thalamic_attention_circuit",
                "neurotransmitter_systems": ["acetylcholine", "dopamine"],
                "oscillatory_patterns": {
                    "frequency_band": "gamma",
                    "amplitude": 0.75,
                    "phase_coherence": 0.85,
                },
            }
            base_example["cognitive_functions"] = ["attention", "executive_control"]
            base_example["processing_mode"] = "fast_path"

        elif template_type == "pipeline":
            base_example.update(
                {
                    "neural_substrate": {
                        "brain_region": "hippocampus",
                        "neural_circuit": "CA3-CA1-PFC recall circuit",
                        "neurotransmitter_systems": ["acetylcholine", "glutamate"],
                        "oscillatory_patterns": {
                            "frequency_band": "theta",
                            "amplitude": 0.65,
                            "phase_coherence": 0.78,
                        },
                    },
                    "cognitive_functions": ["memory", "attention"],
                    "pipeline_id": "P01",
                    "input_events": ["recall_request", "context_query"],
                    "output_events": ["recall_response", "context_assembled"],
                    "processing_stage": "cognitive_processing",
                    "performance_sla": {
                        "max_latency_ms": 120,
                        "throughput_per_sec": 100,
                        "accuracy_threshold": 0.95,
                    },
                }
            )

        elif template_type == "integration":
            base_example.update(
                {
                    "integration_type": "attention_coordination",
                    "coordinated_systems": [
                        {
                            "system_name": "thalamic_attention_gate",
                            "brain_region": "thalamus",
                            "coordination_type": "synchronous",
                        },
                        {
                            "system_name": "prefrontal_executive_control",
                            "brain_region": "prefrontal_cortex",
                            "coordination_type": "cooperative",
                        },
                    ],
                    "coordination_mechanism": {
                        "synchronization_method": "oscillatory_coupling",
                        "conflict_resolution": "priority_based",
                    },
                }
            )

        return base_example

    # === VALIDATION SUITE ===

    def validate_all(self, verbose: bool = False) -> bool:
        """Run comprehensive validation suite."""

        print("🔍 Running enhanced contract validation suite...")

        validation_results = []

        # Storage validation
        result = self._run_validation_script(
            "storage_validate.py", "Storage validation"
        )
        validation_results.append(result)

        # Envelope invariants
        result = self._run_validation_script(
            "check_envelope_invariants.py", "Envelope invariants"
        )
        validation_results.append(result)

        # ULID format tests
        result = self._run_validation_script("test_ulid.py", "ULID format tests")
        validation_results.append(result)

        # Brain-inspired contract validation
        result = self._validate_brain_inspired_contracts()
        validation_results.append(("Brain-inspired validation", result))

        # Architecture alignment check
        result = self._validate_architecture_alignment()
        validation_results.append(("Architecture alignment", result))

        # Report results
        passed = 0
        total = len(validation_results)

        for name, success in validation_results:
            if success:
                print(f"✓ {name} passed")
                passed += 1
            else:
                print(f"❌ {name} failed")

        success_rate = passed / total
        if success_rate == 1.0:
            print(f"🎉 All {total} validations passed!")
        elif success_rate >= 0.8:
            print(f"⚠️  {passed}/{total} validations passed ({success_rate:.1%})")
        else:
            print(f"❌ Only {passed}/{total} validations passed ({success_rate:.1%})")

        return success_rate >= 0.8

    def _run_validation_script(
        self, script_name: str, description: str
    ) -> Tuple[str, bool]:
        """Run a validation script and return result."""
        script_path = self.scripts_root / script_name

        if not script_path.exists():
            print(f"⚠️  {description}: Script not found at {script_path}")
            return description, False

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            success = result.returncode == 0
            return description, success
        except subprocess.TimeoutExpired:
            print(f"⚠️  {description}: Validation timed out")
            return description, False
        except Exception as e:
            print(f"⚠️  {description}: Error running validation: {e}")
            return description, False

    def _validate_brain_inspired_contracts(self) -> bool:
        """Validate brain-inspired contracts for neuroanatomical accuracy."""

        brain_schema_dirs = [
            self.contracts_root / "events" / "schemas" / "thalamus",
            self.contracts_root / "events" / "schemas" / "hippocampus",
            self.contracts_root / "events" / "schemas" / "working_memory",
            self.contracts_root / "events" / "schemas" / "learning",
            self.contracts_root / "events" / "schemas" / "motor_control",
        ]

        valid_brain_regions = [
            "thalamus",
            "hippocampus",
            "prefrontal_cortex",
            "basal_ganglia",
            "motor_cortex",
            "sensory_cortex",
            "cerebellum",
            "amygdala",
        ]

        valid_neurotransmitters = [
            "dopamine",
            "serotonin",
            "acetylcholine",
            "norepinephrine",
            "gaba",
            "glutamate",
        ]

        issues = []

        for schema_dir in brain_schema_dirs:
            if not schema_dir.exists():
                continue

            for schema_file in schema_dir.glob("*.json"):
                try:
                    with open(schema_file) as f:
                        schema = json.load(f)

                    # Check for brain-inspired structure
                    if "neural_substrate" in schema.get("properties", {}):
                        neural_props = schema["properties"]["neural_substrate"]

                        # Validate brain region enum
                        if "brain_region" in neural_props.get("properties", {}):
                            brain_region_def = neural_props["properties"][
                                "brain_region"
                            ]
                            if "enum" in brain_region_def:
                                invalid_regions = set(brain_region_def["enum"]) - set(
                                    valid_brain_regions
                                )
                                if invalid_regions:
                                    issues.append(
                                        f"{schema_file}: Invalid brain regions: {invalid_regions}"
                                    )

                        # Validate neurotransmitter systems
                        if "neurotransmitter_systems" in neural_props.get(
                            "properties", {}
                        ):
                            nt_def = neural_props["properties"][
                                "neurotransmitter_systems"
                            ]
                            if "items" in nt_def and "enum" in nt_def["items"]:
                                invalid_nt = set(nt_def["items"]["enum"]) - set(
                                    valid_neurotransmitters
                                )
                                if invalid_nt:
                                    issues.append(
                                        f"{schema_file}: Invalid neurotransmitters: {invalid_nt}"
                                    )

                except json.JSONDecodeError:
                    issues.append(f"{schema_file}: Invalid JSON")
                except Exception as e:
                    issues.append(f"{schema_file}: Error validating: {e}")

        if issues:
            print("Brain-inspired validation issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False

        return True

    def _validate_architecture_alignment(self) -> bool:
        """Validate that contracts align with architecture diagrams."""

        # Check for required pipeline contracts (P01-P20)
        pipeline_contracts = []
        event_schemas_dir = self.contracts_root / "events" / "schemas"

        for i in range(1, 21):
            pipeline_id = f"P{i:02d}"
            found = False

            # Look for pipeline-related contracts
            if event_schemas_dir.exists():
                for schema_file in event_schemas_dir.rglob("*.json"):
                    try:
                        with open(schema_file) as f:
                            content = f.read()
                        if pipeline_id in content:
                            pipeline_contracts.append(pipeline_id)
                            found = True
                            break
                    except:
                        continue

        missing_pipelines = [
            f"P{i:02d}" for i in range(1, 21) if f"P{i:02d}" not in pipeline_contracts
        ]

        if missing_pipelines:
            print(f"Missing pipeline contracts: {', '.join(missing_pipelines)}")
            return False

        return True

    # === VERSION MANAGEMENT ===

    def bump_version(self, version_type: str = "minor") -> bool:
        """Enhanced version bumping with better validation."""

        # Read current API version
        api_path = self.contracts_root / "api" / "openapi" / "main.yaml"
        if not api_path.exists():
            print(f"❌ OpenAPI spec not found at {api_path}")
            return False

        with open(api_path) as f:
            content = f.read()

        # Extract and bump version
        version_match = re.search(
            r'version:\s*["\']?(\d+)\.(\d+)\.(\d+)["\']?', content
        )
        if not version_match:
            print("❌ Could not find version in OpenAPI spec")
            return False

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
        else:
            print(f"❌ Invalid version type: {version_type}")
            return False

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
        self._update_changelog(new_version)

        return True

    def _update_changelog(self, version: str) -> None:
        """Update changelog with new version entry."""

        changelog_path = self.contracts_root / "CHANGELOG.md"
        if not changelog_path.exists():
            print("⚠️  CHANGELOG.md not found, skipping changelog update")
            return

        with open(changelog_path) as f:
            changelog = f.read()

        today = datetime.now().strftime("%Y-%m-%d")
        new_entry = f"""
## [{version}] - {today}

### Added
-

### Changed
-

### Deprecated
-

### Removed
-

### Fixed
-

### Security
-

"""

        # Insert after the first heading
        lines = changelog.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("## [") or line.startswith("# "):
                if i > 0:  # Skip the main title
                    lines.insert(i, new_entry)
                    break
        else:
            # No existing entries, add after title
            lines.insert(2, new_entry)

        with open(changelog_path, "w") as f:
            f.write("\n".join(lines))

        print(f"✓ Updated CHANGELOG.md with {version} entry")

    # === CONTRACT FREEZE MANAGEMENT ===

    def create_freeze(self, version_desc: str) -> bool:
        """Create contract freeze with enhanced metadata."""

        freeze_script = self.scripts_root / "contracts_freeze.py"
        if not freeze_script.exists():
            print(f"❌ Freeze script not found at {freeze_script}")
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(freeze_script), "create", version_desc],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                print(f"✓ Contract freeze created: {version_desc}")
                if result.stdout:
                    print(result.stdout)
                return True
            else:
                print(f"❌ Failed to create freeze: {version_desc}")
                if result.stderr:
                    print(result.stderr)
                return False

        except subprocess.TimeoutExpired:
            print(f"❌ Freeze creation timed out for: {version_desc}")
            return False
        except Exception as e:
            print(f"❌ Error creating freeze: {e}")
            return False


def main():
    """Main CLI interface."""

    suite = ContractAutomationSuite()

    if not suite.validate_environment():
        return 1

    parser = argparse.ArgumentParser(
        description="Enhanced Contract Automation Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python contract_suite.py new-schema memory_tag --template brain_inspired
  python contract_suite.py new-schema pipeline_p01 --template pipeline
  python contract_suite.py validate --verbose
  python contract_suite.py workflow minor "add memory tagging system"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # New schema command
    new_parser = subparsers.add_parser(
        "new-schema", help="Create new schema from template"
    )
    new_parser.add_argument("name", help="Schema name (snake_case)")
    new_parser.add_argument(
        "--module", default="storage", help="Module (default: storage)"
    )
    new_parser.add_argument(
        "--template",
        default="basic",
        choices=["basic", "brain_inspired", "pipeline", "integration"],
        help="Template type (default: basic)",
    )

    # Validation command
    validate_parser = subparsers.add_parser(
        "validate", help="Run comprehensive validation suite"
    )
    validate_parser.add_argument(
        "--verbose", action="store_true", help="Verbose output"
    )

    # Version management
    version_parser = subparsers.add_parser("bump-version", help="Bump version numbers")
    version_parser.add_argument(
        "type", choices=["major", "minor", "patch"], help="Version bump type"
    )

    # Freeze management
    freeze_parser = subparsers.add_parser("freeze", help="Create contract freeze")
    freeze_parser.add_argument(
        "version", help="Version description (e.g., v1.2.0-feature-name)"
    )

    # Full workflow
    workflow_parser = subparsers.add_parser(
        "workflow", help="Complete contract change workflow"
    )
    workflow_parser.add_argument("version_type", choices=["major", "minor", "patch"])
    workflow_parser.add_argument("description", help="Change description")
    workflow_parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip initial validation (use with caution)",
    )

    args = parser.parse_args()

    if args.command == "new-schema":
        success = suite.create_new_schema(args.name, args.module, args.template)
        return 0 if success else 1

    elif args.command == "validate":
        success = suite.validate_all(args.verbose)
        return 0 if success else 1

    elif args.command == "bump-version":
        success = suite.bump_version(args.type)
        return 0 if success else 1

    elif args.command == "freeze":
        success = suite.create_freeze(args.version)
        return 0 if success else 1

    elif args.command == "workflow":
        print(f"🚀 Starting enhanced workflow for {args.version_type} change...")

        # 1. Validate current state (unless skipped)
        if not args.skip_validation:
            print("1️⃣ Validating current state...")
            if not suite.validate_all():
                print(
                    "❌ Current state validation failed. Fix issues or use --skip-validation"
                )
                return 1

        # 2. Bump version
        print("2️⃣ Bumping version...")
        if not suite.bump_version(args.version_type):
            print("❌ Version bump failed")
            return 1

        # 3. Re-validate after changes
        print("3️⃣ Re-validating after changes...")
        if not suite.validate_all():
            print("❌ Post-change validation failed. Review your changes.")
            return 1

        # 4. Create freeze
        print("4️⃣ Creating contract freeze...")
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        version_desc = f"v{timestamp}-{args.description.replace(' ', '-')}"
        if not suite.create_freeze(version_desc):
            print("❌ Freeze creation failed")
            return 1

        print("\n🎉 Enhanced workflow completed successfully!")
        print(f"   Version bumped: {args.version_type}")
        print(f"   Freeze created: {version_desc}")
        print("\n📋 Next steps:")
        print("   1. Review and test your changes")
        print("   2. Commit with descriptive message")
        print("   3. Create PR for review")
        print("   4. Deploy after approval")

        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
