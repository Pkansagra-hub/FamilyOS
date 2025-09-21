"""
Cognitive Flag Manager
======================

High-level integration manager for MemoryOS cognitive components.
Provides specialized flag management for brain-inspired systems with
cognitive context awareness and neural pathway optimization.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .core import (
    Environment,
    EvaluationContext,
    FeatureFlagManager,
    get_global_manager,
    initialize_global_manager,
)


@dataclass
class CognitiveFlagContext:
    """Extended cognitive context for brain region integration."""

    # Core cognitive metrics
    cognitive_load: float = 0.0
    working_memory_load: float = 0.0
    attention_queue_depth: int = 0

    # Brain region specific
    brain_region: Optional[str] = None
    neural_pathway: Optional[str] = None
    hemisphere: Optional[str] = None  # left, right, bilateral
    cortical_layer: Optional[str] = None  # L1-L6 for neocortex

    # Memory systems
    hippocampus_activity: float = 0.0
    prefrontal_cortex_load: float = 0.0
    thalamus_relay_load: float = 0.0

    # Performance context
    processing_latency_ms: float = 0.0
    memory_pressure: float = 0.0
    cpu_utilization: float = 0.0

    # Request context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


class CognitiveFlagManager:
    """
    Specialized flag manager for MemoryOS cognitive components.

    Provides high-level integration with cognitive systems including:
    - Working Memory Manager
    - Attention Gate
    - Memory Steward
    - Context Bundle Builder
    - Cognitive Event Router
    """

    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        self.environment = environment
        self.flag_manager: Optional[FeatureFlagManager] = None
        self.component_contexts: Dict[str, CognitiveFlagContext] = {}

        # Component flag mappings
        self.component_flags = {
            "working_memory": [
                "working_memory.enable_hierarchical_cache",
                "working_memory.enable_l3_cache",
                "working_memory.enable_complex_operations",
                "working_memory.enable_predictive_prefetch",
                "working_memory.enable_compression",
            ],
            "attention_gate": [
                "attention_gate.enable_admission_control",
                "attention_gate.enable_detailed_analysis",
                "attention_gate.enable_backpressure_advanced",
                "attention_gate.enable_salience_boosting",
                "attention_gate.enable_dropout_protection",
            ],
            "memory_steward": [
                "memory_steward.enable_hippocampus_integration",
                "memory_steward.enable_auto_consolidation",
                "memory_steward.enable_predictive_prefetch",
                "memory_steward.enable_forgetting_algorithms",
                "memory_steward.enable_priority_elevation",
            ],
            "context_bundle": [
                "context_bundle.enable_mmr_diversification",
                "context_bundle.enable_semantic_clustering",
                "context_bundle.enable_temporal_weighting",
                "context_bundle.enable_multi_modal_fusion",
                "context_bundle.enable_adaptive_sizing",
            ],
            "cognitive_events": [
                "cognitive_events.enable_neural_pathway_routing",
                "cognitive_events.enable_brain_region_affinity",
                "cognitive_events.enable_cognitive_correlation",
                "cognitive_events.enable_trace_enrichment",
                "cognitive_events.enable_load_balancing",
            ],
        }

    async def initialize(self, config_path: Optional[Path] = None) -> None:
        """Initialize the cognitive flag manager."""
        if not get_global_manager():
            self.flag_manager = await initialize_global_manager(
                config_path=config_path,
                environment=self.environment,
                enable_hot_reload=True,
            )
        else:
            self.flag_manager = get_global_manager()

    async def get_working_memory_flags(
        self,
        cognitive_load: float = 0.0,
        working_memory_load: float = 0.0,
        prefrontal_cortex_load: float = 0.0,
        cache_pressure: float = 0.0,
    ) -> Dict[str, bool]:
        """Get working memory specific flags with cognitive context."""
        context = self._create_evaluation_context(
            cognitive_load=cognitive_load,
            working_memory_load=working_memory_load,
            brain_region="prefrontal_cortex",
            neural_pathway="executive_control",
            prefrontal_cortex_load=prefrontal_cortex_load,
            memory_pressure=cache_pressure,
        )

        flags = {}
        for flag_name in self.component_flags["working_memory"]:
            if self.flag_manager:
                flags[flag_name] = await self.flag_manager.is_enabled(
                    flag_name, context
                )

        return flags

    async def get_attention_gate_flags(
        self,
        cognitive_load: float = 0.0,
        attention_queue_depth: int = 0,
        thalamus_relay_load: float = 0.0,
        processing_latency_ms: float = 0.0,
    ) -> Dict[str, bool]:
        """Get attention gate specific flags with thalamic context."""
        context = self._create_evaluation_context(
            cognitive_load=cognitive_load,
            attention_queue_depth=attention_queue_depth,
            brain_region="thalamus",
            neural_pathway="attention_relay",
            thalamus_relay_load=thalamus_relay_load,
            processing_latency_ms=processing_latency_ms,
        )

        flags = {}
        for flag_name in self.component_flags["attention_gate"]:
            if self.flag_manager:
                flags[flag_name] = await self.flag_manager.is_enabled(
                    flag_name, context
                )

        return flags

    async def get_memory_steward_flags(
        self,
        cognitive_load: float = 0.0,
        hippocampus_activity: float = 0.0,
        consolidation_pressure: float = 0.0,
        memory_pressure: float = 0.0,
    ) -> Dict[str, bool]:
        """Get memory steward specific flags with hippocampal context."""
        context = self._create_evaluation_context(
            cognitive_load=cognitive_load,
            brain_region="hippocampus",
            neural_pathway="memory_formation",
            hippocampus_activity=hippocampus_activity,
            memory_pressure=memory_pressure,
        )

        flags = {}
        for flag_name in self.component_flags["memory_steward"]:
            if self.flag_manager:
                flags[flag_name] = await self.flag_manager.is_enabled(
                    flag_name, context
                )

        return flags

    async def get_context_bundle_flags(
        self,
        cognitive_load: float = 0.0,
        hippocampus_activity: float = 0.0,
        semantic_complexity: float = 0.0,
        bundle_size: int = 0,
    ) -> Dict[str, bool]:
        """Get context bundle specific flags with recall context."""
        context = self._create_evaluation_context(
            cognitive_load=cognitive_load,
            brain_region="hippocampus",
            neural_pathway="recall_assembly",
            hippocampus_activity=hippocampus_activity,
            memory_pressure=semantic_complexity,
        )

        flags = {}
        for flag_name in self.component_flags["context_bundle"]:
            if self.flag_manager:
                flags[flag_name] = await self.flag_manager.is_enabled(
                    flag_name, context
                )

        return flags

    async def get_cognitive_events_flags(
        self,
        cognitive_load: float = 0.0,
        inter_hemispheric_load: float = 0.0,
        event_throughput: float = 0.0,
        routing_complexity: float = 0.0,
    ) -> Dict[str, bool]:
        """Get cognitive events specific flags with routing context."""
        context = self._create_evaluation_context(
            cognitive_load=cognitive_load,
            brain_region="corpus_callosum",
            neural_pathway="inter_hemispheric",
            hemisphere="bilateral",
            cpu_utilization=event_throughput,
            memory_pressure=routing_complexity,
        )

        flags = {}
        for flag_name in self.component_flags["cognitive_events"]:
            if self.flag_manager:
                flags[flag_name] = await self.flag_manager.is_enabled(
                    flag_name, context
                )

        return flags

    async def get_all_cognitive_flags(
        self, global_context: Optional[CognitiveFlagContext] = None
    ) -> Dict[str, Dict[str, bool]]:
        """Get all cognitive component flags with unified context."""
        if global_context is None:
            global_context = CognitiveFlagContext()

        # Get flags for each component
        results = {
            "working_memory": await self.get_working_memory_flags(
                cognitive_load=global_context.cognitive_load,
                working_memory_load=global_context.working_memory_load,
                prefrontal_cortex_load=global_context.prefrontal_cortex_load,
                cache_pressure=global_context.memory_pressure,
            ),
            "attention_gate": await self.get_attention_gate_flags(
                cognitive_load=global_context.cognitive_load,
                attention_queue_depth=global_context.attention_queue_depth,
                thalamus_relay_load=global_context.thalamus_relay_load,
                processing_latency_ms=global_context.processing_latency_ms,
            ),
            "memory_steward": await self.get_memory_steward_flags(
                cognitive_load=global_context.cognitive_load,
                hippocampus_activity=global_context.hippocampus_activity,
                memory_pressure=global_context.memory_pressure,
            ),
            "context_bundle": await self.get_context_bundle_flags(
                cognitive_load=global_context.cognitive_load,
                hippocampus_activity=global_context.hippocampus_activity,
            ),
            "cognitive_events": await self.get_cognitive_events_flags(
                cognitive_load=global_context.cognitive_load,
                event_throughput=global_context.cpu_utilization,
            ),
        }

        return results

    async def simulate_cognitive_stress_test(self) -> Dict[str, Any]:
        """Simulate cognitive stress scenarios and flag responses."""
        scenarios = [
            {
                "name": "Baseline",
                "context": CognitiveFlagContext(
                    cognitive_load=0.1,
                    working_memory_load=0.2,
                    attention_queue_depth=10,
                    hippocampus_activity=0.3,
                    prefrontal_cortex_load=0.2,
                    thalamus_relay_load=0.2,
                ),
            },
            {
                "name": "Moderate Load",
                "context": CognitiveFlagContext(
                    cognitive_load=0.5,
                    working_memory_load=0.6,
                    attention_queue_depth=50,
                    hippocampus_activity=0.7,
                    prefrontal_cortex_load=0.5,
                    thalamus_relay_load=0.6,
                ),
            },
            {
                "name": "High Load",
                "context": CognitiveFlagContext(
                    cognitive_load=0.8,
                    working_memory_load=0.85,
                    attention_queue_depth=120,
                    hippocampus_activity=0.9,
                    prefrontal_cortex_load=0.8,
                    thalamus_relay_load=0.85,
                    memory_pressure=0.8,
                    cpu_utilization=0.8,
                ),
            },
            {
                "name": "Critical Load",
                "context": CognitiveFlagContext(
                    cognitive_load=0.95,
                    working_memory_load=0.95,
                    attention_queue_depth=250,
                    hippocampus_activity=0.95,
                    prefrontal_cortex_load=0.95,
                    thalamus_relay_load=0.95,
                    memory_pressure=0.9,
                    cpu_utilization=0.9,
                ),
            },
        ]

        results = {}
        for scenario in scenarios:
            scenario_name = scenario["name"]
            context = scenario["context"]

            flags = await self.get_all_cognitive_flags(context)

            # Calculate adaptive response metrics
            total_flags = sum(
                len(component_flags) for component_flags in flags.values()
            )
            enabled_flags = sum(
                sum(1 for enabled in component_flags.values() if enabled)
                for component_flags in flags.values()
            )

            results[scenario_name] = {
                "context": {
                    "cognitive_load": context.cognitive_load,
                    "working_memory_load": context.working_memory_load,
                    "attention_queue_depth": context.attention_queue_depth,
                    "hippocampus_activity": context.hippocampus_activity,
                    "memory_pressure": context.memory_pressure,
                },
                "flags": flags,
                "metrics": {
                    "total_flags": total_flags,
                    "enabled_flags": enabled_flags,
                    "disabled_flags": total_flags - enabled_flags,
                    "adaptive_response_rate": (total_flags - enabled_flags)
                    / total_flags
                    * 100,
                },
            }

        return results

    def _create_evaluation_context(self, **kwargs) -> EvaluationContext:
        """Create evaluation context from cognitive parameters."""
        if self.flag_manager:
            return self.flag_manager.create_context(**kwargs)
        else:
            # Fallback context creation
            return EvaluationContext(environment=self.environment, **kwargs)

    async def get_component_status(self, component: str) -> Dict[str, Any]:
        """Get comprehensive status for a specific cognitive component."""
        if component not in self.component_flags:
            raise ValueError(f"Unknown component: {component}")

        # Get current component context if available
        context = self.component_contexts.get(component, CognitiveFlagContext())

        # Get component-specific flags
        if component == "working_memory":
            flags = await self.get_working_memory_flags(
                cognitive_load=context.cognitive_load,
                working_memory_load=context.working_memory_load,
                prefrontal_cortex_load=context.prefrontal_cortex_load,
            )
        elif component == "attention_gate":
            flags = await self.get_attention_gate_flags(
                cognitive_load=context.cognitive_load,
                attention_queue_depth=context.attention_queue_depth,
                thalamus_relay_load=context.thalamus_relay_load,
            )
        elif component == "memory_steward":
            flags = await self.get_memory_steward_flags(
                cognitive_load=context.cognitive_load,
                hippocampus_activity=context.hippocampus_activity,
            )
        elif component == "context_bundle":
            flags = await self.get_context_bundle_flags(
                cognitive_load=context.cognitive_load,
                hippocampus_activity=context.hippocampus_activity,
            )
        elif component == "cognitive_events":
            flags = await self.get_cognitive_events_flags(
                cognitive_load=context.cognitive_load
            )
        else:
            flags = {}

        enabled_count = sum(1 for enabled in flags.values() if enabled)
        total_count = len(flags)

        return {
            "component": component,
            "flags": flags,
            "summary": {
                "total_flags": total_count,
                "enabled_flags": enabled_count,
                "disabled_flags": total_count - enabled_count,
                "enablement_rate": (
                    enabled_count / total_count * 100 if total_count > 0 else 0
                ),
            },
            "context": context,
        }

    def update_component_context(
        self, component: str, context: CognitiveFlagContext
    ) -> None:
        """Update cognitive context for a specific component."""
        self.component_contexts[component] = context

    async def optimize_for_performance(self) -> Dict[str, Any]:
        """Get performance-optimized flag configuration."""
        # High-performance context: low cognitive load, optimized for speed
        perf_context = CognitiveFlagContext(
            cognitive_load=0.1,
            working_memory_load=0.2,
            attention_queue_depth=5,
            hippocampus_activity=0.1,
            prefrontal_cortex_load=0.1,
            thalamus_relay_load=0.1,
            processing_latency_ms=1.0,
            memory_pressure=0.1,
            cpu_utilization=0.2,
        )

        flags = await self.get_all_cognitive_flags(perf_context)

        return {
            "optimization_target": "performance",
            "context": perf_context,
            "flags": flags,
            "description": "Optimized for maximum performance with minimal cognitive load",
        }

    async def optimize_for_accuracy(self) -> Dict[str, Any]:
        """Get accuracy-optimized flag configuration."""
        # High-accuracy context: moderate load, all cognitive features enabled
        accuracy_context = CognitiveFlagContext(
            cognitive_load=0.3,
            working_memory_load=0.4,
            attention_queue_depth=25,
            hippocampus_activity=0.6,
            prefrontal_cortex_load=0.4,
            thalamus_relay_load=0.3,
            processing_latency_ms=10.0,
            memory_pressure=0.3,
            cpu_utilization=0.4,
        )

        flags = await self.get_all_cognitive_flags(accuracy_context)

        return {
            "optimization_target": "accuracy",
            "context": accuracy_context,
            "flags": flags,
            "description": "Optimized for maximum accuracy with enhanced cognitive processing",
        }


# Global cognitive flag manager instance
_global_cognitive_manager: Optional[CognitiveFlagManager] = None


async def initialize_cognitive_manager(
    environment: Environment = Environment.DEVELOPMENT,
    config_path: Optional[Path] = None,
) -> CognitiveFlagManager:
    """Initialize the global cognitive flag manager."""
    global _global_cognitive_manager

    _global_cognitive_manager = CognitiveFlagManager(environment)
    await _global_cognitive_manager.initialize(config_path)

    return _global_cognitive_manager


def get_cognitive_manager() -> Optional[CognitiveFlagManager]:
    """Get the global cognitive flag manager instance."""
    return _global_cognitive_manager


async def get_working_memory_flags(**kwargs) -> Dict[str, bool]:
    """Convenience function for working memory flags."""
    if _global_cognitive_manager:
        return await _global_cognitive_manager.get_working_memory_flags(**kwargs)
    return {}


async def get_attention_gate_flags(**kwargs) -> Dict[str, bool]:
    """Convenience function for attention gate flags."""
    if _global_cognitive_manager:
        return await _global_cognitive_manager.get_attention_gate_flags(**kwargs)
    return {}


async def get_memory_steward_flags(**kwargs) -> Dict[str, bool]:
    """Convenience function for memory steward flags."""
    if _global_cognitive_manager:
        return await _global_cognitive_manager.get_memory_steward_flags(**kwargs)
    return {}


async def get_context_bundle_flags(**kwargs) -> Dict[str, bool]:
    """Convenience function for context bundle flags."""
    if _global_cognitive_manager:
        return await _global_cognitive_manager.get_context_bundle_flags(**kwargs)
    return {}


async def get_cognitive_events_flags(**kwargs) -> Dict[str, bool]:
    """Convenience function for cognitive events flags."""
    if _global_cognitive_manager:
        return await _global_cognitive_manager.get_cognitive_events_flags(**kwargs)
    return {}
