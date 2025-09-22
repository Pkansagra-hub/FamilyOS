#!/usr/bin/env python3
"""
Contract Validation Helper
Centralized validation functions for contract integrity.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def validate_contract_syntax() -> Tuple[bool, List[str]]:
    """Validate JSON/YAML syntax across all contracts."""

    errors = []
    contracts_root = Path("contracts")

    # Validate JSON files (skip frozen artifacts)
    for json_file in contracts_root.rglob("*.json"):
        # Skip frozen artifacts and temp files
        if "_frozen" in str(json_file) or json_file.name.startswith("."):
            continue

        try:
            with open(json_file, encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"JSON syntax error in {json_file}: {e}")
        except Exception as e:
            errors.append(f"Error reading {json_file}: {e}")

    return len(errors) == 0, errors


def run_storage_validation() -> Tuple[bool, str]:
    """Run storage validation script."""

    script_path = Path("contracts/automation/storage_validator.py")
    if not script_path.exists():
        return False, f"Storage validation script not found: {script_path}"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Storage validation timed out"
    except Exception as e:
        return False, f"Error running storage validation: {e}"


def run_envelope_validation() -> Tuple[bool, str]:
    """Run envelope invariants validation."""

    script_path = Path("contracts/automation/envelope_validator.py")
    if not script_path.exists():
        return False, f"Envelope validation script not found: {script_path}"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Envelope validation timed out"
    except Exception as e:
        return False, f"Error running envelope validation: {e}"


def validate_brain_inspired_accuracy() -> Tuple[bool, List[str]]:
    """Validate neuroanatomical accuracy in brain-inspired contracts."""

    valid_brain_regions = {
        "thalamus",
        "hippocampus",
        "prefrontal_cortex",
        "basal_ganglia",
        "motor_cortex",
        "sensory_cortex",
        "cerebellum",
        "amygdala",
        "temporal_cortex",
        "parietal_cortex",
        "occipital_cortex",
    }

    valid_neurotransmitters = {
        "dopamine",
        "serotonin",
        "acetylcholine",
        "norepinephrine",
        "gaba",
        "glutamate",
        "glycine",
        "histamine",
    }

    errors = []
    contracts_root = Path("contracts")

    # Check brain-inspired schema directories
    brain_dirs = [
        contracts_root / "events" / "schemas" / "thalamus",
        contracts_root / "events" / "schemas" / "hippocampus",
        contracts_root / "events" / "schemas" / "working_memory",
        contracts_root / "events" / "schemas" / "learning",
        contracts_root / "events" / "schemas" / "motor_control",
    ]

    for brain_dir in brain_dirs:
        if not brain_dir.exists():
            continue

        for schema_file in brain_dir.glob("*.json"):
            try:
                with open(schema_file) as f:
                    schema = json.load(f)

                # Check neural substrate definitions
                if "neural_substrate" in schema.get("properties", {}):
                    neural_props = schema["properties"]["neural_substrate"]

                    # Validate brain regions
                    if "brain_region" in neural_props.get("properties", {}):
                        brain_region_def = neural_props["properties"]["brain_region"]
                        if "enum" in brain_region_def:
                            invalid_regions = (
                                set(brain_region_def["enum"]) - valid_brain_regions
                            )
                            if invalid_regions:
                                errors.append(
                                    f"{schema_file}: Invalid brain regions: {invalid_regions}"
                                )

                    # Validate neurotransmitter systems
                    if "neurotransmitter_systems" in neural_props.get("properties", {}):
                        nt_def = neural_props["properties"]["neurotransmitter_systems"]
                        if "items" in nt_def and "enum" in nt_def["items"]:
                            invalid_nt = (
                                set(nt_def["items"]["enum"]) - valid_neurotransmitters
                            )
                            if invalid_nt:
                                errors.append(
                                    f"{schema_file}: Invalid neurotransmitters: {invalid_nt}"
                                )

            except json.JSONDecodeError:
                errors.append(f"{schema_file}: Invalid JSON")
            except Exception as e:
                errors.append(f"{schema_file}: Error validating: {e}")

    return len(errors) == 0, errors


def check_pipeline_coverage() -> Tuple[bool, List[str]]:
    """Check coverage of P01-P20 pipelines in contracts."""

    found_pipelines = set()
    missing_pipelines = []

    contracts_root = Path("contracts")

    # Look for pipeline references in both events and storage schemas
    search_dirs = [
        contracts_root / "events" / "schemas",
        contracts_root / "storage" / "schemas",
    ]

    # Look for pipeline references in contracts
    for i in range(1, 21):
        pipeline_id = f"P{i:02d}"
        found = False

        for search_dir in search_dirs:
            if search_dir.exists():
                # Look for both P01 pattern and pipeline_p01 filenames
                pipeline_patterns = [
                    pipeline_id,  # P01
                    f"pipeline_p{i:02d}",  # pipeline_p01
                    f"pipeline_{pipeline_id.lower()}",  # pipeline_p01
                ]

                for schema_file in search_dir.rglob("*.json"):
                    try:
                        # Check filename matches
                        filename = schema_file.stem
                        if any(pattern in filename for pattern in pipeline_patterns):
                            found_pipelines.add(pipeline_id)
                            found = True
                            break

                        # Check content matches
                        with open(schema_file, encoding="utf-8") as f:
                            content = f.read()
                        if any(pattern in content for pattern in pipeline_patterns):
                            found_pipelines.add(pipeline_id)
                            found = True
                            break
                    except Exception:
                        continue

                if found:
                    break

        if not found:
            missing_pipelines.append(pipeline_id)

    return len(missing_pipelines) == 0, missing_pipelines


def run_comprehensive_validation() -> bool:
    """Run all validation checks and report results."""

    print("🔍 Running comprehensive contract validation...")

    all_passed = True

    # 1. Syntax validation
    print("1️⃣ Validating contract syntax...")
    syntax_ok, syntax_errors = validate_contract_syntax()
    if syntax_ok:
        print("   ✓ Syntax validation passed")
    else:
        print("   ❌ Syntax validation failed:")
        for error in syntax_errors[:5]:  # Show first 5 errors
            print(f"     - {error}")
        if len(syntax_errors) > 5:
            print(f"     ... and {len(syntax_errors) - 5} more errors")
        all_passed = False

    # 2. Storage validation
    print("2️⃣ Running storage validation...")
    storage_ok, storage_output = run_storage_validation()
    if storage_ok:
        print("   ✓ Storage validation passed")
    else:
        print("   ❌ Storage validation failed")
        print(f"     {storage_output}")
        all_passed = False

    # 3. Envelope validation
    print("3️⃣ Checking envelope invariants...")
    envelope_ok, envelope_output = run_envelope_validation()
    if envelope_ok:
        print("   ✓ Envelope invariants check passed")
    else:
        print("   ❌ Envelope invariants check failed")
        print(f"     {envelope_output}")
        all_passed = False

    # 4. Brain-inspired validation
    print("4️⃣ Validating neuroanatomical accuracy...")
    brain_ok, brain_errors = validate_brain_inspired_accuracy()
    if brain_ok:
        print("   ✓ Brain-inspired validation passed")
    else:
        print("   ❌ Brain-inspired validation failed:")
        for error in brain_errors[:3]:  # Show first 3 errors
            print(f"     - {error}")
        if len(brain_errors) > 3:
            print(f"     ... and {len(brain_errors) - 3} more errors")
        all_passed = False

    # 5. Pipeline coverage
    print("5️⃣ Checking pipeline coverage...")
    pipeline_ok, missing_pipelines = check_pipeline_coverage()
    if pipeline_ok:
        print("   ✓ All pipelines (P01-P20) have contracts")
    else:
        print("   ⚠️ Missing pipeline contracts:")
        print(f"     Missing: {', '.join(missing_pipelines)}")
        # Don't fail on pipeline coverage since we know this is incomplete

    # Summary
    if all_passed:
        print("\n🎉 All critical validations passed!")
        if not pipeline_ok:
            print("⚠️ Note: Pipeline coverage incomplete (expected - see gap analysis)")
    else:
        print("\n❌ Some validations failed. Review errors above.")

    return all_passed


if __name__ == "__main__":
    success = run_comprehensive_validation()
    sys.exit(0 if success else 1)
