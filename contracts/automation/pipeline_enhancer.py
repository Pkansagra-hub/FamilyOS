#!/usr/bin/env python3
"""
Pipeline Example Enhancer
Updates all existing pipeline examples with proper neural substrate and cognitive functions.

This addresses Priority 1: Contract Quality Enhancement
"""

import json
from pathlib import Path

# Brain region mappings for different pipelines
PIPELINE_BRAIN_MAPPINGS = {
    "P01": {  # Recall/Read
        "brain_region": "hippocampus",
        "neural_circuit": "CA3-CA1-PFC recall circuit",
        "neurotransmitter_systems": ["acetylcholine", "glutamate"],
        "oscillatory_patterns": {
            "frequency_band": "theta",
            "amplitude": 0.65,
            "phase_coherence": 0.78,
        },
        "cognitive_functions": ["memory", "attention"],
    },
    "P02": {  # Write/Store
        "brain_region": "hippocampus",
        "neural_circuit": "DG-CA3 encoding circuit",
        "neurotransmitter_systems": ["dopamine", "acetylcholine"],
        "oscillatory_patterns": {
            "frequency_band": "gamma",
            "amplitude": 0.72,
            "phase_coherence": 0.82,
        },
        "cognitive_functions": ["memory", "learning"],
    },
    "P03": {  # Consolidation
        "brain_region": "hippocampus",
        "neural_circuit": "hippocampal-cortical consolidation loop",
        "neurotransmitter_systems": ["acetylcholine", "norepinephrine"],
        "oscillatory_patterns": {
            "frequency_band": "delta",
            "amplitude": 0.55,
            "phase_coherence": 0.75,
        },
        "cognitive_functions": ["memory", "learning"],
    },
    "P04": {  # Action/Execute
        "brain_region": "motor_cortex",
        "neural_circuit": "M1-basal ganglia-thalamus loop",
        "neurotransmitter_systems": ["dopamine", "gaba"],
        "oscillatory_patterns": {
            "frequency_band": "beta",
            "amplitude": 0.68,
            "phase_coherence": 0.85,
        },
        "cognitive_functions": ["motor_control", "executive_control"],
    },
    "P05": {  # Decision Making
        "brain_region": "prefrontal_cortex",
        "neural_circuit": "dlPFC-ACC decision circuit",
        "neurotransmitter_systems": ["dopamine", "norepinephrine"],
        "oscillatory_patterns": {
            "frequency_band": "alpha",
            "amplitude": 0.62,
            "phase_coherence": 0.79,
        },
        "cognitive_functions": ["decision_making", "executive_control"],
    },
    "P06": {  # Attention Gate
        "brain_region": "thalamus",
        "neural_circuit": "thalamic reticular nucleus",
        "neurotransmitter_systems": ["gaba", "glutamate"],
        "oscillatory_patterns": {
            "frequency_band": "gamma",
            "amplitude": 0.75,
            "phase_coherence": 0.88,
        },
        "cognitive_functions": ["attention", "executive_control"],
    },
    "P07": {  # Learning/Adaptation
        "brain_region": "basal_ganglia",
        "neural_circuit": "striatal learning circuit",
        "neurotransmitter_systems": ["dopamine", "acetylcholine"],
        "oscillatory_patterns": {
            "frequency_band": "theta",
            "amplitude": 0.58,
            "phase_coherence": 0.73,
        },
        "cognitive_functions": ["learning", "memory"],
    },
    "P08": {  # Sensory Processing
        "brain_region": "sensory_cortex",
        "neural_circuit": "S1-S2 sensory integration",
        "neurotransmitter_systems": ["glutamate", "gaba"],
        "oscillatory_patterns": {
            "frequency_band": "gamma",
            "amplitude": 0.70,
            "phase_coherence": 0.80,
        },
        "cognitive_functions": ["attention", "memory"],
    },
}

# Default mapping for P09-P20 (can be customized later)
DEFAULT_MAPPING = {
    "brain_region": "prefrontal_cortex",
    "neural_circuit": "general cognitive processing circuit",
    "neurotransmitter_systems": ["dopamine", "glutamate"],
    "oscillatory_patterns": {
        "frequency_band": "alpha",
        "amplitude": 0.65,
        "phase_coherence": 0.75,
    },
    "cognitive_functions": ["executive_control", "memory"],
}


def enhance_pipeline_example(example_path: Path) -> bool:
    """Enhance a pipeline example with neural substrate and cognitive functions."""

    try:
        # Read the existing example
        with open(example_path, encoding="utf-8") as f:
            example = json.load(f)

        # Extract pipeline ID
        pipeline_id = example.get("pipeline_id", "P01")

        # Get brain mapping
        brain_mapping = PIPELINE_BRAIN_MAPPINGS.get(pipeline_id, DEFAULT_MAPPING)

        # Add missing fields
        if "neural_substrate" not in example:
            example["neural_substrate"] = {
                "brain_region": brain_mapping["brain_region"],
                "neural_circuit": brain_mapping["neural_circuit"],
                "neurotransmitter_systems": brain_mapping["neurotransmitter_systems"],
                "oscillatory_patterns": brain_mapping["oscillatory_patterns"],
            }

        if "cognitive_functions" not in example:
            example["cognitive_functions"] = brain_mapping["cognitive_functions"]

        # Write the enhanced example back
        with open(example_path, "w", encoding="utf-8") as f:
            json.dump(example, f, indent=2, ensure_ascii=False)

        print(f"✓ Enhanced {example_path.name} with {pipeline_id} brain mapping")
        return True

    except Exception as e:
        print(f"❌ Failed to enhance {example_path}: {e}")
        return False


def update_all_pipeline_examples() -> int:
    """Update all pipeline examples with neural substrate information."""

    examples_dir = Path("contracts/storage/examples")
    updated_count = 0

    print("🧠 Enhancing pipeline examples with neural substrate information...")
    print()

    # Find all pipeline examples
    for example_file in examples_dir.glob("pipeline_p*.example.json"):
        if "fixed" not in example_file.name:  # Skip our test file
            if enhance_pipeline_example(example_file):
                updated_count += 1

    print()
    print(
        f"🎉 Enhanced {updated_count} pipeline examples with brain-inspired neural substrate information!"
    )
    return updated_count


if __name__ == "__main__":
    updated = update_all_pipeline_examples()

    if updated > 0:
        print()
        print("📋 Next steps:")
        print("1. Run validation to confirm all examples now pass:")
        print("   python contracts/automation/validation_helper.py")
        print("2. Test specific pipeline contract validation:")
        print("   python contracts/automation/storage_validator.py")
    else:
        print("⚠️ No pipeline examples were updated. Check if files exist.")
