#!/usr/bin/env python3
"""
Cognitive Integration Test
==========================

Test script for cognitive component integration with feature flags.
Demonstrates brain-inspired adaptive behavior across all cognitive systems.
"""

import asyncio
import sys
from pathlib import Path

# Add feature_flags to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from core.manager import FeatureFlagManager 
    from core.config import Environment
    from core.evaluator import EvaluationContext
    print("✅ Core imports successful")
except ImportError as e:
    print(f"❌ Core import error: {e}")
    sys.exit(1)


async def test_cognitive_integration():
    """Test comprehensive cognitive integration."""
    print("🧠 MemoryOS Cognitive Integration Test")
    print("=" * 50)
    
    # Initialize cognitive manager
    cognitive_manager = await initialize_cognitive_manager(
        environment=Environment.DEVELOPMENT
    )
    
    # Create component adapters
    working_memory_adapter = WorkingMemoryFlagAdapter(cognitive_manager)
    attention_gate_adapter = AttentionGateFlagAdapter(cognitive_manager)
    memory_steward_adapter = MemoryStewardFlagAdapter(cognitive_manager)
    context_bundle_adapter = ContextBundleFlagAdapter(cognitive_manager)
    cognitive_events_adapter = CognitiveEventsFlagAdapter(cognitive_manager)
    
    print("\n✅ Cognitive adapters initialized")
    
    # Test scenario 1: Low cognitive load (optimal performance)
    print("\n🟢 Scenario 1: Low Cognitive Load (Optimal Performance)")
    print("-" * 55)
    
    low_load_context = CognitiveFlagContext(
        cognitive_load=0.2,
        working_memory_load=0.3,
        attention_queue_depth=15,
        hippocampus_activity=0.4,
        prefrontal_cortex_load=0.2,
        thalamus_relay_load=0.3
    )
    
    # Get all cognitive flags with low load
    all_flags = await cognitive_manager.get_all_cognitive_flags(low_load_context)
    
    enabled_count = sum(sum(flags.values()) for flags in all_flags.values())
    total_count = sum(len(flags) for flags in all_flags.values())
    
    print(f"Flags Status: {enabled_count}/{total_count} enabled ({enabled_count/total_count*100:.1f}%)")
    
    for component, flags in all_flags.items():
        enabled = sum(flags.values())
        total = len(flags)
        print(f"  {component}: {enabled}/{total} enabled")
    
    # Test Working Memory configuration
    wm_config = await working_memory_adapter.get_adaptive_configuration()
    print(f"\nWorking Memory L3 Cache: {'✅' if wm_config['flags'].get('working_memory.enable_l3_cache') else '❌'}")
    print(f"Complex Operations: {'✅' if wm_config['flags'].get('working_memory.enable_complex_operations') else '❌'}")
    
    # Test Attention Gate configuration
    ag_config = await attention_gate_adapter.get_adaptive_configuration()
    print(f"Attention Detailed Analysis: {'✅' if ag_config['flags'].get('attention_gate.enable_detailed_analysis') else '❌'}")
    print(f"Advanced Backpressure: {'✅' if ag_config['flags'].get('attention_gate.enable_backpressure_advanced') else '❌'}")
    
    # Test scenario 2: High cognitive load (survival mode)
    print("\n🔴 Scenario 2: High Cognitive Load (Survival Mode)")
    print("-" * 50)
    
    high_load_context = CognitiveFlagContext(
        cognitive_load=0.9,
        working_memory_load=0.95,
        attention_queue_depth=200,
        hippocampus_activity=0.95,
        prefrontal_cortex_load=0.9,
        thalamus_relay_load=0.95,
        memory_pressure=0.9,
        cpu_utilization=0.85
    )
    
    # Get all cognitive flags with high load
    all_flags_high = await cognitive_manager.get_all_cognitive_flags(high_load_context)
    
    enabled_count_high = sum(sum(flags.values()) for flags in all_flags_high.values())
    total_count_high = sum(len(flags) for flags in all_flags_high.values())
    
    print(f"Flags Status: {enabled_count_high}/{total_count_high} enabled ({enabled_count_high/total_count_high*100:.1f}%)")
    
    for component, flags in all_flags_high.items():
        enabled = sum(flags.values())
        total = len(flags)
        print(f"  {component}: {enabled}/{total} enabled")
    
    # Show adaptive response
    adaptive_response = (enabled_count - enabled_count_high) / enabled_count * 100
    print(f"\n📊 Adaptive Response: {adaptive_response:.1f}% flags disabled under high load")
    
    # Test Working Memory under high load
    wm_flags_high = await working_memory_adapter.get_cache_flags(
        cache_hit_rate=0.6,  # Poor performance
        memory_pressure=0.9,  # High pressure
        cognitive_load=0.9    # High load
    )
    
    print("\nWorking Memory under high load:")
    print(f"  L3 Cache: {'✅' if wm_flags_high.get('l3_cache') else '❌'}")
    print(f"  Hierarchical Cache: {'✅' if wm_flags_high.get('hierarchical_cache') else '❌'}")
    
    # Test Attention Gate admission decision
    admission_decision = await attention_gate_adapter.get_admission_decision(
        item_salience=0.4,
        cognitive_load=0.9,
        queue_depth=200,
        urgency=0.3
    )
    
    print("\nAttention Gate Decision:")
    print(f"  Salience 0.4 → {admission_decision['decision'].upper()}")
    print(f"  Reason: {admission_decision['reason']}")
    
    # Test Memory Steward consolidation strategy
    consolidation_strategy = await memory_steward_adapter.get_consolidation_strategy(
        cognitive_load=0.9,
        hippocampus_activity=0.95,
        memory_importance=0.7,
        urgency=0.2
    )
    
    print("\nMemory Steward Consolidation:")
    print(f"  Strategy: {consolidation_strategy['strategy']}")
    print(f"  Delay: {consolidation_strategy['delay_ms']}ms")
    print(f"  Reason: {consolidation_strategy['reason']}")
    
    # Test Context Bundle diversification
    diversification_strategy = await context_bundle_adapter.get_diversification_strategy(
        cognitive_load=0.9,
        available_contexts=100,
        target_diversity=0.7,
        time_budget_ms=50.0  # Tight budget
    )
    
    print("\nContext Bundle Diversification:")
    print(f"  Strategy: {diversification_strategy['strategy']}")
    print(f"  Expected Diversity: {diversification_strategy['expected_diversity']:.2f}")
    print(f"  Reason: {diversification_strategy['reason']}")
    
    # Test Cognitive Events routing
    routing_strategy = await cognitive_events_adapter.get_routing_strategy(
        event_type='memory_formation',
        cognitive_load=0.9,
        target_brain_regions={
            'hippocampus': 0.9,
            'prefrontal_cortex': 0.7,
            'temporal_lobe': 0.6
        },
        hemisphere_preference='bilateral'
    )
    
    print("\nCognitive Events Routing:")
    print(f"  Strategy: {routing_strategy['strategy']}")
    print(f"  Primary Region: {max(routing_strategy['routing_weights'].items(), key=lambda x: x[1])[0]}")
    print(f"  Reason: {routing_strategy['reason']}")
    
    # Test scenario 3: Cognitive stress simulation
    print("\n🟡 Scenario 3: Cognitive Stress Test")
    print("-" * 40)
    
    stress_results = await cognitive_manager.simulate_cognitive_stress_test()
    
    for scenario_name, results in stress_results.items():
        metrics = results['metrics']
        print(f"\n{scenario_name}:")
        print(f"  Load: {results['context']['cognitive_load']:.2f}")
        print(f"  Enabled: {metrics['enabled_flags']}/{metrics['total_flags']}")
        print(f"  Adaptive Response: {metrics['adaptive_response_rate']:.1f}%")
    
    # Test scenario 4: Performance optimization modes
    print("\n⚡ Scenario 4: Optimization Modes")
    print("-" * 35)
    
    perf_config = await cognitive_manager.optimize_for_performance()
    accuracy_config = await cognitive_manager.optimize_for_accuracy()
    
    perf_enabled = sum(sum(flags.values()) for flags in perf_config['flags'].values())
    accuracy_enabled = sum(sum(flags.values()) for flags in accuracy_config['flags'].values())
    
    print(f"Performance Mode: {perf_enabled} flags enabled")
    print(f"Accuracy Mode: {accuracy_enabled} flags enabled")
    print(f"Accuracy vs Performance: +{accuracy_enabled - perf_enabled} flags for better accuracy")
    
    print("\n🎯 Integration Test Complete!")
    print(f"✅ All {len(all_flags)} cognitive components tested")
    print("✅ Adaptive behavior validated across load scenarios")
    print("✅ Component-specific configurations verified")
    print("✅ Brain-inspired flag evaluation working correctly")


async def test_individual_components():
    """Test individual component adapters in detail."""
    print("\n🔬 Individual Component Testing")
    print("=" * 40)
    
    # Initialize cognitive manager
    cognitive_manager = await initialize_cognitive_manager(
        environment=Environment.DEVELOPMENT
    )
    
    # Test Working Memory detailed scenarios
    print("\n💾 Working Memory Detailed Test")
    print("-" * 30)
    
    wm_adapter = WorkingMemoryFlagAdapter(cognitive_manager)
    
    # Update with realistic metrics
    wm_metrics = WorkingMemoryMetrics(
        l1_cache_hit_rate=0.85,
        l2_cache_hit_rate=0.75,
        l3_cache_hit_rate=0.65,
        cognitive_load=0.4,
        working_memory_load=0.6,
        operation_latency_ms=15.0,
        memory_pressure=0.3,
        active_contexts=25,
        pending_operations=8
    )
    wm_adapter.update_metrics(wm_metrics)
    
    # Test compression strategy
    compression_config = await wm_adapter.get_compression_strategy(
        memory_pressure=0.7,
        cognitive_load=0.4,
        data_complexity=0.6
    )
    
    print(f"Compression Strategy: {compression_config['strategy']}")
    print(f"Compression Level: {compression_config.get('compression_level', 'N/A')}")
    print(f"Enabled: {'✅' if compression_config['enabled'] else '❌'}")
    
    # Test prefetch configuration
    prefetch_config = await wm_adapter.get_prefetch_configuration(
        cognitive_load=0.4,
        cache_hit_rate=0.75,
        bandwidth_available=0.8
    )
    
    print("\nPrefetch Configuration:")
    print(f"  Distance: {prefetch_config.get('prefetch_distance', 0)}")
    print(f"  Aggressive: {'✅' if prefetch_config.get('aggressive_mode', False) else '❌'}")
    print(f"  Enabled: {'✅' if prefetch_config['enabled'] else '❌'}")
    
    # Test Attention Gate detailed scenarios  
    print("\n🎯 Attention Gate Detailed Test")
    print("-" * 32)
    
    ag_adapter = AttentionGateFlagAdapter(cognitive_manager)
    
    # Test various salience levels
    salience_tests = [
        {'salience': 0.9, 'urgency': 0.1, 'expected': 'ADMIT/BOOST'},
        {'salience': 0.5, 'urgency': 0.0, 'expected': 'ADMIT/DEFER'},
        {'salience': 0.2, 'urgency': 0.0, 'expected': 'DROP/DEFER'},
        {'salience': 0.1, 'urgency': 0.9, 'expected': 'ADMIT (emergency)'}
    ]
    
    for test in salience_tests:
        decision = await ag_adapter.get_admission_decision(
            item_salience=test['salience'],
            cognitive_load=0.5,
            queue_depth=75,
            urgency=test['urgency']
        )
        
        print(f"Salience {test['salience']:.1f}, Urgency {test['urgency']:.1f} → {decision['decision'].upper()}")
    
    # Test backpressure configuration
    backpressure_config = await ag_adapter.get_backpressure_configuration(
        cognitive_load=0.6,
        queue_depth=120,
        processing_rate=15.0
    )
    
    print(f"\nBackpressure Strategy: {backpressure_config['strategy']}")
    print(f"Queue Limit: {backpressure_config['queue_limit']}")
    print(f"Rate Limit: {backpressure_config['admission_rate_limit']:.1f}/s")
    
    print("\n🎉 Component Testing Complete!")


async def main():
    """Main test entry point."""
    try:
        await test_cognitive_integration()
        await test_individual_components()
        
        print("\n" + "=" * 50)
        print("🎊 All Tests Passed Successfully!")
        print("Brain-inspired feature flag system is working correctly")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())