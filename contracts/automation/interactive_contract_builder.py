#!/usr/bin/env python3
"""
Interactive Contract Builder CLI
Implements Priority 4: Developer Experience Enhancement

Provides a user-friendly interface for creating and managing brain-inspired contracts.
"""

import json
import sys
from pathlib import Path
from typing import Optional


class InteractiveContractBuilder:
    """Interactive CLI for building brain-inspired contracts."""

    def __init__(self):
        self.contracts_root = Path("contracts")
        self.automation_root = Path("contracts/automation")

        # Brain region templates
        self.brain_regions = {
            "thalamus": {
                "description": "Attention gate and relay processing",
                "functions": ["attention", "executive_control"],
                "neurotransmitters": ["gaba", "glutamate"],
                "frequencies": ["alpha", "gamma"],
                "circuits": ["thalamic reticular nucleus", "thalamic relay circuit"],
            },
            "hippocampus": {
                "description": "Memory formation, recall, and consolidation",
                "functions": ["memory", "learning"],
                "neurotransmitters": ["acetylcholine", "glutamate"],
                "frequencies": ["theta", "gamma"],
                "circuits": [
                    "CA3-CA1 circuit",
                    "DG-CA3 encoding",
                    "hippocampal-cortical loop",
                ],
            },
            "prefrontal_cortex": {
                "description": "Executive control and decision making",
                "functions": ["executive_control", "decision_making"],
                "neurotransmitters": ["dopamine", "norepinephrine"],
                "frequencies": ["alpha", "beta"],
                "circuits": [
                    "dlPFC-ACC circuit",
                    "working memory circuit",
                    "cognitive control circuit",
                ],
            },
            "basal_ganglia": {
                "description": "Action selection and learning",
                "functions": ["learning", "motor_control", "decision_making"],
                "neurotransmitters": ["dopamine", "acetylcholine", "gaba"],
                "frequencies": ["alpha", "beta", "theta"],
                "circuits": ["striatal learning circuit", "action selection circuit"],
            },
            "motor_cortex": {
                "description": "Motor control and action execution",
                "functions": ["motor_control", "executive_control"],
                "neurotransmitters": ["dopamine", "gaba", "glutamate"],
                "frequencies": ["beta", "gamma"],
                "circuits": [
                    "M1-basal ganglia-thalamus loop",
                    "motor planning circuit",
                ],
            },
            "sensory_cortex": {
                "description": "Sensory processing and attention",
                "functions": ["attention", "memory"],
                "neurotransmitters": ["glutamate", "gaba", "acetylcholine"],
                "frequencies": ["gamma", "alpha"],
                "circuits": [
                    "S1-S2 integration",
                    "sensory attention circuit",
                    "multimodal integration",
                ],
            },
        }

        # Pipeline templates
        self.pipeline_types = {
            "recall": {
                "description": "Memory recall and retrieval",
                "typical_regions": ["hippocampus"],
            },
            "store": {
                "description": "Memory encoding and storage",
                "typical_regions": ["hippocampus"],
            },
            "consolidation": {
                "description": "Memory consolidation",
                "typical_regions": ["hippocampus"],
            },
            "action": {
                "description": "Action execution",
                "typical_regions": ["motor_cortex", "basal_ganglia"],
            },
            "decision": {
                "description": "Decision making",
                "typical_regions": ["prefrontal_cortex", "basal_ganglia"],
            },
            "attention": {
                "description": "Attention control",
                "typical_regions": ["thalamus", "prefrontal_cortex"],
            },
            "learning": {
                "description": "Learning and adaptation",
                "typical_regions": ["basal_ganglia", "hippocampus"],
            },
            "sensory": {
                "description": "Sensory processing",
                "typical_regions": ["sensory_cortex", "thalamus"],
            },
        }

    def run_interactive_session(self) -> None:
        """Run the main interactive session."""

        print("🧠 Interactive Brain-Inspired Contract Builder")
        print("=" * 50)
        print()

        while True:
            print("Choose an option:")
            print("1. 🏗️  Create new brain-inspired contract")
            print("2. 🔧 Create new pipeline contract")
            print("3. 📊 Validate existing contracts")
            print("4. 🧠 Browse brain region templates")
            print("5. 📋 Generate contract summary report")
            print("6. 🚪 Exit")
            print()

            choice = input("Enter your choice (1-6): ").strip()

            if choice == "1":
                self.guided_brain_inspired_creation()
            elif choice == "2":
                self.guided_pipeline_creation()
            elif choice == "3":
                self.run_validation_suite()
            elif choice == "4":
                self.browse_brain_templates()
            elif choice == "5":
                self.generate_contract_report()
            elif choice == "6":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please try again.")

            print()

    def guided_brain_inspired_creation(self) -> None:
        """Guide user through creating a brain-inspired contract."""

        print("\n🧠 Creating Brain-Inspired Contract")
        print("-" * 40)

        # Get contract name
        name = input("Enter contract name (e.g., attention_gate): ").strip()
        if not name:
            print("❌ Contract name is required.")
            return

        # Select brain region
        print("\nSelect brain region:")
        regions = list(self.brain_regions.keys())
        for i, region in enumerate(regions, 1):
            desc = self.brain_regions[region]["description"]
            print(f"{i}. {region} - {desc}")

        try:
            region_choice = int(input(f"Enter choice (1-{len(regions)}): ")) - 1
            if region_choice < 0 or region_choice >= len(regions):
                raise ValueError()
            brain_region = regions[region_choice]
        except (ValueError, IndexError):
            print("❌ Invalid brain region choice.")
            return

        # Get additional details
        description = input(
            f"Enter description (default: {brain_region} processing): "
        ).strip()
        if not description:
            description = f"{brain_region} processing"

        # Generate contract
        contract_id = self._generate_contract(
            name, "brain_inspired", brain_region, description
        )

        if contract_id:
            print(f"✅ Created brain-inspired contract: {contract_id}")
            print(f"   Brain region: {brain_region}")
            print(
                f"   Functions: {', '.join(self.brain_regions[brain_region]['functions'])}"
            )
            print(
                f"   Neurotransmitters: {', '.join(self.brain_regions[brain_region]['neurotransmitters'])}"
            )

    def guided_pipeline_creation(self) -> None:
        """Guide user through creating a pipeline contract."""

        print("\n🔧 Creating Pipeline Contract")
        print("-" * 35)

        # Get pipeline ID
        pipeline_id = input("Enter pipeline ID (e.g., P01, P21): ").strip().upper()
        if not pipeline_id or not pipeline_id.startswith("P"):
            print("❌ Pipeline ID must start with 'P' (e.g., P01).")
            return

        # Select pipeline type
        print("\nSelect pipeline type:")
        types = list(self.pipeline_types.keys())
        for i, ptype in enumerate(types, 1):
            desc = self.pipeline_types[ptype]["description"]
            regions = ", ".join(self.pipeline_types[ptype]["typical_regions"])
            print(f"{i}. {ptype} - {desc} (typical: {regions})")

        try:
            type_choice = int(input(f"Enter choice (1-{len(types)}): ")) - 1
            if type_choice < 0 or type_choice >= len(types):
                raise ValueError()
            pipeline_type = types[type_choice]
        except (ValueError, IndexError):
            print("❌ Invalid pipeline type choice.")
            return

        # Select brain region for this pipeline
        typical_regions = self.pipeline_types[pipeline_type]["typical_regions"]
        print(f"\nSelect brain region (recommended: {', '.join(typical_regions)}):")
        regions = list(self.brain_regions.keys())
        for i, region in enumerate(regions, 1):
            indicator = "⭐" if region in typical_regions else "  "
            print(f"{i}. {indicator} {region}")

        try:
            region_choice = int(input(f"Enter choice (1-{len(regions)}): ")) - 1
            brain_region = regions[region_choice]
        except (ValueError, IndexError):
            print("❌ Invalid brain region choice.")
            return

        # Generate pipeline contract
        contract_name = f"pipeline_{pipeline_id.lower()}"
        contract_id = self._generate_pipeline_contract(
            contract_name, pipeline_id, pipeline_type, brain_region
        )

        if contract_id:
            print(f"✅ Created pipeline contract: {contract_id}")
            print(f"   Pipeline ID: {pipeline_id}")
            print(f"   Type: {pipeline_type}")
            print(f"   Brain region: {brain_region}")

    def run_validation_suite(self) -> None:
        """Run the comprehensive validation suite."""

        print("\n📊 Running Validation Suite")
        print("-" * 30)

        # Import and run our validation helper
        try:
            import subprocess

            result = subprocess.run(
                [sys.executable, str(self.automation_root / "validation_helper.py")],
                capture_output=True,
                text=True,
                timeout=120,
            )

            print("Validation Results:")
            print("-" * 20)
            print(result.stdout)

            if result.stderr:
                print("Errors:")
                print(result.stderr)

        except Exception as e:
            print(f"❌ Error running validation: {e}")

    def browse_brain_templates(self) -> None:
        """Browse available brain region templates."""

        print("\n🧠 Brain Region Templates")
        print("-" * 30)

        for region, details in self.brain_regions.items():
            print(f"\n📍 {region.upper()}")
            print(f"   Description: {details['description']}")
            print(f"   Functions: {', '.join(details['functions'])}")
            print(f"   Neurotransmitters: {', '.join(details['neurotransmitters'])}")
            print(f"   Frequencies: {', '.join(details['frequencies'])}")
            print(f"   Circuits: {', '.join(details['circuits'][:2])}...")

    def generate_contract_report(self) -> None:
        """Generate a comprehensive contract report."""

        print("\n📋 Generating Contract Summary Report")
        print("-" * 40)

        # Count contracts by type
        storage_schemas = self.contracts_root / "storage" / "schemas"

        brain_inspired_count = 0
        pipeline_count = 0
        other_count = 0

        for schema_file in storage_schemas.glob("*.json"):
            if "pipeline_p" in schema_file.name:
                pipeline_count += 1
            elif any(
                region in schema_file.name for region in self.brain_regions.keys()
            ):
                brain_inspired_count += 1
            else:
                other_count += 1

        total_contracts = brain_inspired_count + pipeline_count + other_count

        print("📊 Contract Summary:")
        print(f"   Total contracts: {total_contracts}")
        print(f"   Pipeline contracts: {pipeline_count}")
        print(f"   Brain-inspired contracts: {brain_inspired_count}")
        print(f"   Other contracts: {other_count}")
        print()

        if pipeline_count >= 20:
            print("✅ Pipeline coverage: Complete (20+ pipelines)")
        else:
            print(f"⚠️ Pipeline coverage: {pipeline_count}/20 pipelines")

        print(
            f"🧠 Brain region coverage: {brain_inspired_count} brain-inspired contracts"
        )

        # Quick validation status
        print("\n🔍 Quick validation check...")
        try:
            import subprocess

            result = subprocess.run(
                [sys.executable, str(self.automation_root / "validation_helper.py")],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if "All pipelines (P01-P20) have contracts" in result.stdout:
                print("✅ Pipeline validation: All P01-P20 contracts found")
            else:
                print("⚠️ Pipeline validation: Some issues detected")

        except Exception:
            print("❌ Could not run validation check")

    def _generate_contract(
        self, name: str, template_type: str, brain_region: str, description: str
    ) -> Optional[str]:
        """Generate a contract using the contract suite."""

        try:
            import subprocess

            result = subprocess.run(
                [
                    sys.executable,
                    str(self.automation_root / "contract_suite.py"),
                    "new-schema",
                    name,
                    "--template",
                    template_type,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return name
            else:
                print(f"❌ Error generating contract: {result.stderr}")
                return None

        except Exception as e:
            print(f"❌ Error running contract generator: {e}")
            return None

    def _generate_pipeline_contract(
        self, name: str, pipeline_id: str, pipeline_type: str, brain_region: str
    ) -> Optional[str]:
        """Generate a pipeline contract."""

        try:
            import subprocess

            result = subprocess.run(
                [
                    sys.executable,
                    str(self.automation_root / "contract_suite.py"),
                    "new-schema",
                    name,
                    "--template",
                    "pipeline",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Customize the generated contract with specific pipeline details
                self._customize_pipeline_contract(name, pipeline_id, brain_region)
                return name
            else:
                print(f"❌ Error generating pipeline contract: {result.stderr}")
                return None

        except Exception as e:
            print(f"❌ Error running pipeline generator: {e}")
            return None

    def _customize_pipeline_contract(
        self, name: str, pipeline_id: str, brain_region: str
    ) -> None:
        """Customize a generated pipeline contract with specific details."""

        try:
            # Update the example file
            example_path = (
                self.contracts_root / "storage" / "examples" / f"{name}.example.json"
            )

            if example_path.exists():
                with open(example_path, encoding="utf-8") as f:
                    example_data = json.load(f)

                # Update pipeline ID
                example_data["pipeline_id"] = pipeline_id

                # Update brain region info
                if brain_region in self.brain_regions:
                    region_info = self.brain_regions[brain_region]
                    example_data["neural_substrate"]["brain_region"] = brain_region
                    example_data["neural_substrate"]["neurotransmitter_systems"] = (
                        region_info["neurotransmitters"][:2]
                    )
                    example_data["neural_substrate"]["oscillatory_patterns"][
                        "frequency_band"
                    ] = region_info["frequencies"][0]
                    example_data["cognitive_functions"] = region_info["functions"][:2]

                # Write back
                with open(example_path, "w", encoding="utf-8") as f:
                    json.dump(example_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"⚠️ Could not customize contract: {e}")


def main():
    """Main function to run the interactive contract builder."""

    try:
        builder = InteractiveContractBuilder()
        builder.run_interactive_session()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
