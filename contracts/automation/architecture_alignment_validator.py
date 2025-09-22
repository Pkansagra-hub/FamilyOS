#!/usr/bin/env python3
"""
Enhanced Architecture Alignment Validator
Implements Priority 3: Architecture Alignment Validation

Provides advanced checking against architecture diagrams and brain-inspired patterns.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


class ArchitectureDiagramAnalyzer:
    """Analyzes architecture diagrams for contract alignment."""

    def __init__(self):
        self.contracts_root = Path("contracts")
        self.docs_root = Path("docs")

        # Expected brain regions from architecture diagrams
        self.expected_brain_regions = {
            "thalamus": ["attention_gate", "relay_processing", "arousal_regulation"],
            "hippocampus": [
                "memory_formation",
                "recall",
                "consolidation",
                "spatial_navigation",
            ],
            "prefrontal_cortex": [
                "executive_control",
                "decision_making",
                "working_memory",
                "error_monitoring",
            ],
            "basal_ganglia": ["action_selection", "learning", "habit_formation"],
            "motor_cortex": ["action_execution", "motor_planning"],
            "sensory_cortex": [
                "sensory_processing",
                "attention",
                "multimodal_integration",
            ],
        }

        # Expected pipeline flow from diagrams
        self.expected_pipeline_flows = {
            "P01": ["recall_request", "hippocampal_retrieval", "recall_response"],
            "P02": ["store_request", "hippocampal_encoding", "store_response"],
            "P03": [
                "consolidation_trigger",
                "hippocampal_cortical_loop",
                "consolidation_complete",
            ],
            "P04": ["action_request", "motor_cortex_execution", "action_complete"],
            "P05": ["decision_request", "prefrontal_deliberation", "decision_response"],
            "P06": ["stimulus_detection", "thalamic_gating", "attention_focus"],
        }

        # Critical integration points from diagrams
        self.integration_points = [
            ("thalamus", "prefrontal_cortex", "attention_control"),
            ("hippocampus", "prefrontal_cortex", "memory_executive_integration"),
            ("basal_ganglia", "motor_cortex", "action_selection_execution"),
            ("sensory_cortex", "thalamus", "sensory_attention_gating"),
            ("hippocampus", "sensory_cortex", "memory_sensory_binding"),
        ]

    def validate_brain_region_coverage(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate that all expected brain regions are covered in contracts."""

        coverage_report = {
            "total_regions": len(self.expected_brain_regions),
            "covered_regions": 0,
            "missing_regions": [],
            "coverage_details": {},
        }

        # Check storage schemas for brain region coverage
        storage_schemas = self.contracts_root / "storage" / "schemas"

        for brain_region, expected_functions in self.expected_brain_regions.items():
            found_functions = []

            # Look for brain region references in schemas
            for schema_file in storage_schemas.glob("*.json"):
                try:
                    with open(schema_file, encoding="utf-8") as f:
                        schema_content = f.read()

                    if brain_region in schema_content.lower():
                        schema_data = json.loads(schema_content)
                        found_functions.extend(
                            self._extract_functions_from_schema(schema_data)
                        )

                except Exception:
                    continue

            coverage_details = {
                "expected_functions": expected_functions,
                "found_functions": list(set(found_functions)),
                "coverage_percentage": len(
                    set(found_functions) & set(expected_functions)
                )
                / len(expected_functions)
                * 100,
            }

            coverage_report["coverage_details"][brain_region] = coverage_details

            if coverage_details["coverage_percentage"] > 50:  # At least 50% coverage
                coverage_report["covered_regions"] += 1
            else:
                coverage_report["missing_regions"].append(brain_region)

        coverage_report["overall_coverage"] = (
            coverage_report["covered_regions"] / coverage_report["total_regions"] * 100
        )

        return coverage_report["overall_coverage"] >= 80, coverage_report

    def validate_pipeline_flow_alignment(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate that pipeline flows match architecture diagram expectations."""

        flow_report = {
            "total_pipelines": len(self.expected_pipeline_flows),
            "aligned_pipelines": 0,
            "misaligned_pipelines": [],
            "alignment_details": {},
        }

        storage_examples = self.contracts_root / "storage" / "examples"

        for pipeline_id, expected_flow in self.expected_pipeline_flows.items():
            pipeline_file = (
                storage_examples / f"pipeline_{pipeline_id.lower()}.example.json"
            )

            if pipeline_file.exists():
                try:
                    with open(pipeline_file, encoding="utf-8") as f:
                        pipeline_data = json.load(f)

                    # Check input/output events alignment
                    input_events = pipeline_data.get("input_events", [])
                    output_events = pipeline_data.get("output_events", [])
                    neural_circuit = pipeline_data.get("neural_substrate", {}).get(
                        "neural_circuit", ""
                    )

                    alignment_score = self._calculate_flow_alignment(
                        expected_flow, input_events, output_events, neural_circuit
                    )

                    alignment_details = {
                        "expected_flow": expected_flow,
                        "actual_inputs": input_events,
                        "actual_outputs": output_events,
                        "neural_circuit": neural_circuit,
                        "alignment_score": alignment_score,
                    }

                    flow_report["alignment_details"][pipeline_id] = alignment_details

                    if alignment_score >= 70:  # At least 70% alignment
                        flow_report["aligned_pipelines"] += 1
                    else:
                        flow_report["misaligned_pipelines"].append(pipeline_id)

                except Exception as e:
                    flow_report["alignment_details"][pipeline_id] = {"error": str(e)}
                    flow_report["misaligned_pipelines"].append(pipeline_id)
            else:
                flow_report["misaligned_pipelines"].append(pipeline_id)

        flow_report["overall_alignment"] = (
            flow_report["aligned_pipelines"] / flow_report["total_pipelines"] * 100
        )

        return flow_report["overall_alignment"] >= 80, flow_report

    def validate_integration_points(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate critical integration points from architecture diagrams."""

        integration_report = {
            "total_integration_points": len(self.integration_points),
            "implemented_points": 0,
            "missing_points": [],
            "integration_details": {},
        }

        # Check for integration patterns in contracts
        for region1, region2, integration_type in self.integration_points:
            integration_found = self._find_integration_evidence(
                region1, region2, integration_type
            )

            integration_details = {
                "regions": [region1, region2],
                "integration_type": integration_type,
                "evidence_found": integration_found,
            }

            integration_key = f"{region1}-{region2}"
            integration_report["integration_details"][
                integration_key
            ] = integration_details

            if integration_found:
                integration_report["implemented_points"] += 1
            else:
                integration_report["missing_points"].append(integration_key)

        integration_report["overall_integration"] = (
            integration_report["implemented_points"]
            / integration_report["total_integration_points"]
            * 100
        )

        return integration_report["overall_integration"] >= 60, integration_report

    def _extract_functions_from_schema(self, schema_data: Dict[str, Any]) -> List[str]:
        """Extract cognitive functions from schema data."""
        functions = []

        # Look for cognitive_functions field
        if "properties" in schema_data:
            props = schema_data["properties"]
            if "cognitive_functions" in props:
                cog_func = props["cognitive_functions"]
                if "items" in cog_func and "enum" in cog_func["items"]:
                    functions.extend(cog_func["items"]["enum"])

        # Look for neural substrate descriptions
        if "neural_substrate" in schema_data.get("properties", {}):
            neural_props = schema_data["properties"]["neural_substrate"]
            if "description" in neural_props:
                desc = neural_props["description"].lower()
                if "attention" in desc:
                    functions.append("attention")
                if "memory" in desc:
                    functions.append("memory_formation")
                if "control" in desc:
                    functions.append("executive_control")

        return functions

    def _calculate_flow_alignment(
        self,
        expected_flow: List[str],
        inputs: List[str],
        outputs: List[str],
        neural_circuit: str,
    ) -> float:
        """Calculate alignment score between expected and actual pipeline flow."""

        # Check if flow stages are represented
        flow_score = 0
        total_checks = len(expected_flow)

        flow_text = " ".join(inputs + outputs + [neural_circuit]).lower()

        for flow_stage in expected_flow:
            stage_keywords = flow_stage.lower().split("_")
            if any(keyword in flow_text for keyword in stage_keywords):
                flow_score += 1

        return (flow_score / total_checks) * 100 if total_checks > 0 else 0

    def _find_integration_evidence(
        self, region1: str, region2: str, integration_type: str
    ) -> bool:
        """Find evidence of integration between brain regions."""

        # Look for integration patterns in schemas
        storage_schemas = self.contracts_root / "storage" / "schemas"

        for schema_file in storage_schemas.glob("*.json"):
            try:
                with open(schema_file, encoding="utf-8") as f:
                    content = f.read().lower()

                # Check if both regions and integration type are mentioned
                if (
                    region1 in content
                    and region2 in content
                    and any(
                        keyword in content for keyword in integration_type.split("_")
                    )
                ):
                    return True

            except Exception:
                continue

        return False

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive architecture alignment report."""

        print("🏗️ Running comprehensive architecture alignment validation...")
        print()

        # Run all validations
        brain_coverage_ok, brain_report = self.validate_brain_region_coverage()
        flow_alignment_ok, flow_report = self.validate_pipeline_flow_alignment()
        integration_ok, integration_report = self.validate_integration_points()

        # Generate summary
        overall_score = (
            brain_report["overall_coverage"]
            + flow_report["overall_alignment"]
            + integration_report["overall_integration"]
        ) / 3

        comprehensive_report = {
            "overall_alignment_score": overall_score,
            "brain_region_coverage": brain_report,
            "pipeline_flow_alignment": flow_report,
            "integration_points": integration_report,
            "recommendations": self._generate_recommendations(
                brain_report, flow_report, integration_report
            ),
        }

        # Print summary
        print(f"🎯 Overall Architecture Alignment: {overall_score:.1f}%")
        print(f"   Brain Region Coverage: {brain_report['overall_coverage']:.1f}%")
        print(f"   Pipeline Flow Alignment: {flow_report['overall_alignment']:.1f}%")
        print(
            f"   Integration Points: {integration_report['overall_integration']:.1f}%"
        )
        print()

        if overall_score >= 80:
            print("✅ Excellent architecture alignment!")
        elif overall_score >= 60:
            print("⚠️ Good architecture alignment with room for improvement")
        else:
            print("❌ Architecture alignment needs attention")

        return comprehensive_report

    def _generate_recommendations(
        self, brain_report: Dict, flow_report: Dict, integration_report: Dict
    ) -> List[str]:
        """Generate recommendations for improving architecture alignment."""

        recommendations = []

        if brain_report["overall_coverage"] < 80:
            recommendations.append(
                f"Enhance brain region coverage - missing: {', '.join(brain_report['missing_regions'])}"
            )

        if flow_report["overall_alignment"] < 80:
            recommendations.append(
                f"Improve pipeline flow alignment - review: {', '.join(flow_report['misaligned_pipelines'])}"
            )

        if integration_report["overall_integration"] < 60:
            recommendations.append(
                f"Implement missing integration points: {', '.join(integration_report['missing_points'])}"
            )

        if not recommendations:
            recommendations.append(
                "Architecture alignment is excellent - continue maintaining high standards"
            )

        return recommendations


def main():
    """Main function to run architecture alignment validation."""

    analyzer = ArchitectureDiagramAnalyzer()
    report = analyzer.generate_comprehensive_report()

    # Save report
    report_file = Path("contracts/ARCHITECTURE_ALIGNMENT_REPORT.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"📊 Detailed report saved to: {report_file}")

    return report["overall_alignment_score"] >= 70


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
