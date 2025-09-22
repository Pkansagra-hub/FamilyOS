#!/usr/bin/env python3
"""
Advanced Pipeline Example Enhancer
Fixes pipeline IDs and applies brain region-specific mappings for P01-P20.

This implements Priority 2: Advanced Template Customization
"""

import json
import re
from pathlib import Path


def fix_pipeline_example_with_brain_mapping(example_path: Path) -> bool:
    """Fix pipeline example with correct ID and brain-specific mapping."""

    try:
        # Extract pipeline ID from filename
        match = re.search(r"pipeline_p(\d+)", example_path.name)
        if not match:
            print(f"⚠️ Could not extract pipeline ID from {example_path.name}")
            return False

        pipeline_num = int(match.group(1))
        pipeline_id = f"P{pipeline_num:02d}"

        # Read the existing example
        with open(example_path, encoding="utf-8") as f:
            example = json.load(f)

        # Fix the pipeline ID
        example["pipeline_id"] = pipeline_id

        # Apply brain region-specific mappings
        brain_mappings = {
            "P01": (
                "hippocampus",
                "CA3-CA1-PFC recall circuit",
                ["memory", "attention"],
                ["acetylcholine", "glutamate"],
                "theta",
            ),
            "P02": (
                "hippocampus",
                "DG-CA3 encoding circuit",
                ["memory", "learning"],
                ["dopamine", "acetylcholine"],
                "gamma",
            ),
            "P03": (
                "hippocampus",
                "hippocampal-cortical consolidation",
                ["memory", "learning"],
                ["acetylcholine", "norepinephrine"],
                "delta",
            ),
            "P04": (
                "motor_cortex",
                "M1-basal ganglia-thalamus loop",
                ["motor_control", "executive_control"],
                ["dopamine", "gaba"],
                "beta",
            ),
            "P05": (
                "prefrontal_cortex",
                "dlPFC-ACC decision circuit",
                ["decision_making", "executive_control"],
                ["dopamine", "norepinephrine"],
                "alpha",
            ),
            "P06": (
                "thalamus",
                "thalamic reticular nucleus",
                ["attention", "executive_control"],
                ["gaba", "glutamate"],
                "gamma",
            ),
            "P07": (
                "basal_ganglia",
                "striatal learning circuit",
                ["learning", "memory"],
                ["dopamine", "acetylcholine"],
                "theta",
            ),
            "P08": (
                "sensory_cortex",
                "S1-S2 sensory integration",
                ["attention", "memory"],
                ["glutamate", "gaba"],
                "gamma",
            ),
            "P09": (
                "prefrontal_cortex",
                "working memory circuit",
                ["memory", "executive_control"],
                ["dopamine", "glutamate"],
                "alpha",
            ),
            "P10": (
                "basal_ganglia",
                "action selection circuit",
                ["decision_making", "motor_control"],
                ["dopamine", "gaba"],
                "beta",
            ),
            "P11": (
                "thalamus",
                "thalamic relay circuit",
                ["attention", "memory"],
                ["glutamate", "gaba"],
                "alpha",
            ),
            "P12": (
                "hippocampus",
                "pattern completion circuit",
                ["memory", "learning"],
                ["acetylcholine", "glutamate"],
                "theta",
            ),
            "P13": (
                "prefrontal_cortex",
                "cognitive control circuit",
                ["executive_control", "attention"],
                ["dopamine", "norepinephrine"],
                "beta",
            ),
            "P14": (
                "motor_cortex",
                "motor planning circuit",
                ["motor_control", "executive_control"],
                ["gaba", "glutamate"],
                "beta",
            ),
            "P15": (
                "sensory_cortex",
                "sensory attention circuit",
                ["attention", "memory"],
                ["acetylcholine", "glutamate"],
                "gamma",
            ),
            "P16": (
                "basal_ganglia",
                "habit formation circuit",
                ["learning", "motor_control"],
                ["dopamine", "acetylcholine"],
                "alpha",
            ),
            "P17": (
                "hippocampus",
                "spatial navigation circuit",
                ["memory", "attention"],
                ["acetylcholine", "glutamate"],
                "theta",
            ),
            "P18": (
                "prefrontal_cortex",
                "error monitoring circuit",
                ["executive_control", "learning"],
                ["dopamine", "norepinephrine"],
                "alpha",
            ),
            "P19": (
                "thalamus",
                "arousal regulation circuit",
                ["attention", "executive_control"],
                ["norepinephrine", "acetylcholine"],
                "beta",
            ),
            "P20": (
                "sensory_cortex",
                "multimodal integration circuit",
                ["attention", "memory"],
                ["glutamate", "acetylcholine"],
                "gamma",
            ),
        }

        if pipeline_id in brain_mappings:
            (
                brain_region,
                neural_circuit,
                cognitive_functions,
                neurotransmitters,
                freq_band,
            ) = brain_mappings[pipeline_id]

            # Update neural substrate
            example["neural_substrate"] = {
                "brain_region": brain_region,
                "neural_circuit": neural_circuit,
                "neurotransmitter_systems": neurotransmitters,
                "oscillatory_patterns": {
                    "frequency_band": freq_band,
                    "amplitude": 0.65 + (pipeline_num % 5) * 0.03,  # Vary by pipeline
                    "phase_coherence": 0.75 + (pipeline_num % 10) * 0.01,
                },
            }

            # Update cognitive functions
            example["cognitive_functions"] = cognitive_functions

            # Update input/output events based on pipeline type
            if "recall" in neural_circuit.lower() or pipeline_id in [
                "P01",
                "P12",
                "P17",
            ]:
                example["input_events"] = ["recall_request", "context_query"]
                example["output_events"] = ["recall_response", "context_assembled"]
            elif "encoding" in neural_circuit.lower() or pipeline_id in ["P02"]:
                example["input_events"] = ["store_request", "memory_item"]
                example["output_events"] = ["store_response", "memory_encoded"]
            elif "motor" in neural_circuit.lower() or pipeline_id in ["P04", "P14"]:
                example["input_events"] = ["action_request", "motor_plan"]
                example["output_events"] = ["action_executed", "motor_feedback"]
            elif "attention" in neural_circuit.lower() or pipeline_id in [
                "P06",
                "P11",
                "P15",
                "P19",
            ]:
                example["input_events"] = ["attention_request", "stimulus_info"]
                example["output_events"] = ["attention_response", "focus_updated"]
            elif "decision" in neural_circuit.lower() or pipeline_id in ["P05", "P10"]:
                example["input_events"] = ["decision_request", "option_set"]
                example["output_events"] = ["decision_response", "choice_made"]
            elif "learning" in neural_circuit.lower() or pipeline_id in ["P07", "P16"]:
                example["input_events"] = ["learning_signal", "experience_data"]
                example["output_events"] = ["learning_response", "adaptation_complete"]
            else:
                example["input_events"] = ["cognitive_request", "input_data"]
                example["output_events"] = ["cognitive_response", "output_data"]

        # Write the enhanced example back
        with open(example_path, "w", encoding="utf-8") as f:
            json.dump(example, f, indent=2, ensure_ascii=False)

        brain_region = brain_mappings.get(pipeline_id, ("default", "", [], [], ""))[0]
        print(f"✓ Enhanced {example_path.name} → {pipeline_id} ({brain_region})")
        return True

    except Exception as e:
        print(f"❌ Failed to enhance {example_path}: {e}")
        return False


def main():
    """Main function to enhance all pipeline examples."""

    examples_dir = Path("contracts/storage/examples")
    updated_count = 0

    print("🧠 Applying advanced brain region-specific pipeline mappings...")
    print()

    # Process all pipeline examples
    for example_file in sorted(examples_dir.glob("pipeline_p*.example.json")):
        if "fixed" not in example_file.name:  # Skip test files
            if fix_pipeline_example_with_brain_mapping(example_file):
                updated_count += 1

    print()
    print(
        f"🎉 Applied brain region-specific mappings to {updated_count} pipeline examples!"
    )
    print()
    print("📋 Pipeline Brain Region Mapping Applied:")
    print("   P01-P03, P12, P17: Hippocampus (Memory circuits)")
    print("   P04, P14: Motor Cortex (Action circuits)")
    print("   P05, P09, P13, P18: Prefrontal Cortex (Executive circuits)")
    print("   P06, P11, P19: Thalamus (Attention/relay circuits)")
    print("   P07, P10, P16: Basal Ganglia (Learning/action selection)")
    print("   P08, P15, P20: Sensory Cortex (Sensory processing)")


if __name__ == "__main__":
    main()
