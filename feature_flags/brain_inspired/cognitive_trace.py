"""
Cognitive Trace Enrichment
==========================

Advanced cognitive trace enrichment for MemoryOS feature flags.
Provides brain-inspired trace correlation with neural pathway context
and cognitive load-aware trace detail levels.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ..flag_manager import CognitiveFlagContext, CognitiveFlagManager
from .neural_correlator import BrainRegion, NeuralPathway


class TraceDetailLevel(Enum):
    """Cognitive trace detail levels."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"
    NEURAL_DEBUG = "neural_debug"


class CognitiveContextType(Enum):
    """Types of cognitive context for trace enrichment."""

    WORKING_MEMORY = "working_memory"
    ATTENTION_CONTROL = "attention_control"
    MEMORY_FORMATION = "memory_formation"
    RECALL_PROCESSING = "recall_processing"
    EXECUTIVE_FUNCTION = "executive_function"
    SENSORY_PROCESSING = "sensory_processing"


@dataclass
class CognitiveTrace:
    """Enriched cognitive trace with neural pathway context."""

    # Basic trace information
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_trace_id: Optional[str] = None
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Timing information
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None

    # Operation context
    operation_name: str = "unknown"
    component_name: str = "unknown"
    service_name: str = "memoryos"

    # Neural pathway context
    neural_pathway: Optional[NeuralPathway] = None
    brain_region: Optional[BrainRegion] = None
    hemisphere: Optional[str] = None
    cortical_layer: Optional[str] = None

    # Cognitive context
    cognitive_context_type: Optional[CognitiveContextType] = None
    cognitive_load: float = 0.0
    working_memory_load: float = 0.0
    attention_queue_depth: int = 0

    # Brain region activity
    hippocampus_activity: float = 0.0
    prefrontal_activity: float = 0.0
    thalamus_activity: float = 0.0

    # Feature flag context
    active_flags: Dict[str, bool] = field(default_factory=dict)
    flag_decisions: Dict[str, str] = field(default_factory=dict)
    cognitive_overrides: List[str] = field(default_factory=list)

    # Performance metrics
    cpu_utilization: float = 0.0
    memory_usage_mb: float = 0.0
    cache_hit_rates: Dict[str, float] = field(default_factory=dict)

    # Trace metadata
    tags: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    # Correlation information
    correlated_traces: List[str] = field(default_factory=list)
    correlation_strength: float = 0.0
    causal_relationships: List[str] = field(default_factory=list)

    # Error and status information
    status: str = "ok"  # ok, error, timeout, cancelled
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class TraceEnrichmentConfig:
    """Configuration for cognitive trace enrichment."""

    detail_level: TraceDetailLevel = TraceDetailLevel.STANDARD
    include_flag_decisions: bool = True
    include_neural_context: bool = True
    include_performance_metrics: bool = True
    include_correlations: bool = False

    # Sampling configuration
    sampling_rate: float = 1.0  # 0.0 to 1.0
    high_load_sampling_rate: float = 0.1  # Reduced sampling under load

    # Performance thresholds
    max_enrichment_time_ms: float = 5.0
    max_correlation_lookback: int = 100

    # Detail level thresholds
    cognitive_load_threshold: float = 0.8
    memory_pressure_threshold: float = 0.9


class CognitiveTraceEnricher:
    """
    Cognitive trace enrichment engine.

    Provides brain-inspired trace enrichment including:
    - Neural pathway context annotation
    - Cognitive load correlation
    - Feature flag decision tracking
    - Brain region activity correlation
    - Cross-component trace correlation
    """

    def __init__(self, cognitive_manager: CognitiveFlagManager):
        self.cognitive_manager = cognitive_manager
        self.enrichment_config = TraceEnrichmentConfig()
        self.active_traces: Dict[str, CognitiveTrace] = {}
        self.completed_traces: List[CognitiveTrace] = []

        # Correlation tracking
        self.trace_correlations: Dict[str, List[str]] = {}

        # Statistics
        self.enrichment_stats = {
            "traces_enriched": 0,
            "enrichment_time_ms": 0.0,
            "correlations_found": 0,
            "flag_decisions_tracked": 0,
            "neural_contexts_added": 0,
            "performance_metrics_captured": 0,
        }

    async def start_trace(
        self,
        operation_name: str,
        component_name: str,
        cognitive_context: CognitiveFlagContext,
        parent_trace_id: Optional[str] = None,
    ) -> CognitiveTrace:
        """Start a new cognitive trace with enrichment."""

        # Check if tracing is enabled
        trace_flags = await self._get_trace_flags(cognitive_context.cognitive_load)

        if not trace_flags.get("trace_enrichment_enabled", False):
            # Return minimal trace
            return CognitiveTrace(
                operation_name=operation_name,
                component_name=component_name,
                parent_trace_id=parent_trace_id,
            )

        # Create enriched trace
        trace = CognitiveTrace(
            operation_name=operation_name,
            component_name=component_name,
            parent_trace_id=parent_trace_id,
            cognitive_load=cognitive_context.cognitive_load,
            working_memory_load=cognitive_context.working_memory_load,
            attention_queue_depth=cognitive_context.attention_queue_depth,
            hippocampus_activity=cognitive_context.hippocampus_activity,
            prefrontal_activity=cognitive_context.prefrontal_cortex_load,
            thalamus_activity=cognitive_context.thalamus_relay_load,
            cpu_utilization=cognitive_context.cpu_utilization,
            memory_usage_mb=cognitive_context.memory_pressure
            * 1000,  # Convert to MB estimate
        )

        # Add neural pathway context
        if trace_flags.get("neural_context_enabled", False):
            await self._add_neural_context(trace, component_name, cognitive_context)

        # Add feature flag context
        if trace_flags.get("flag_decisions_enabled", False):
            await self._add_flag_context(trace, cognitive_context)

        # Store active trace
        self.active_traces[trace.trace_id] = trace

        return trace

    async def finish_trace(
        self,
        trace: CognitiveTrace,
        status: str = "ok",
        error_message: Optional[str] = None,
    ) -> CognitiveTrace:
        """Finish and enrich a cognitive trace."""

        # Set end time and duration
        trace.end_time = datetime.now(timezone.utc)
        trace.duration_ms = (trace.end_time - trace.start_time).total_seconds() * 1000
        trace.status = status
        trace.error_message = error_message

        # Check if enrichment is enabled
        trace_flags = await self._get_trace_flags(trace.cognitive_load)

        if trace_flags.get("trace_enrichment_enabled", False):
            # Add performance metrics
            if trace_flags.get("performance_metrics_enabled", False):
                await self._add_performance_metrics(trace)

            # Add correlations
            if trace_flags.get("correlations_enabled", False):
                await self._add_trace_correlations(trace)

            # Add final enrichment
            await self._add_final_enrichment(trace)

        # Move to completed traces
        if trace.trace_id in self.active_traces:
            del self.active_traces[trace.trace_id]

        self.completed_traces.append(trace)
        self.enrichment_stats["traces_enriched"] += 1

        # Maintain completed traces limit
        if len(self.completed_traces) > 1000:
            self.completed_traces.pop(0)

        return trace

    async def add_trace_event(
        self,
        trace: CognitiveTrace,
        event_name: str,
        event_data: Dict[str, Any] = None,
        cognitive_load: float = None,
    ) -> None:
        """Add an event to a cognitive trace."""

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_name": event_name,
            "event_data": event_data or {},
            "cognitive_load": cognitive_load or trace.cognitive_load,
        }

        # Check if detailed events are enabled
        trace_flags = await self._get_trace_flags(trace.cognitive_load)

        if trace_flags.get("detailed_events_enabled", False):
            # Add neural pathway context to event
            if trace.neural_pathway:
                event["neural_pathway"] = trace.neural_pathway.value
            if trace.brain_region:
                event["brain_region"] = trace.brain_region.value

        trace.events.append(event)

    async def correlate_traces(
        self, trace1: CognitiveTrace, trace2: CognitiveTrace
    ) -> float:
        """Calculate correlation strength between two traces."""

        correlation_strength = 0.0

        # Temporal correlation
        if trace1.end_time and trace2.start_time:
            time_overlap = self._calculate_time_overlap(trace1, trace2)
            correlation_strength += time_overlap * 0.3

        # Component correlation
        if trace1.component_name == trace2.component_name:
            correlation_strength += 0.2

        # Neural pathway correlation
        if (
            trace1.neural_pathway
            and trace2.neural_pathway
            and trace1.neural_pathway == trace2.neural_pathway
        ):
            correlation_strength += 0.3

        # Cognitive load correlation
        load_correlation = 1.0 - abs(trace1.cognitive_load - trace2.cognitive_load)
        correlation_strength += load_correlation * 0.2

        return min(1.0, correlation_strength)

    async def get_trace_insights(
        self, component_name: Optional[str] = None, time_window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get insights from cognitive traces."""

        # Filter traces
        cutoff_time = datetime.now(timezone.utc)
        cutoff_time = cutoff_time.replace(
            minute=cutoff_time.minute - time_window_minutes
        )

        relevant_traces = [
            trace
            for trace in self.completed_traces
            if (
                trace.start_time >= cutoff_time
                and (component_name is None or trace.component_name == component_name)
            )
        ]

        if not relevant_traces:
            return {
                "trace_count": 0,
                "insights": "No traces found in specified time window",
            }

        insights = {
            "trace_count": len(relevant_traces),
            "average_duration_ms": sum(t.duration_ms or 0 for t in relevant_traces)
            / len(relevant_traces),
            "cognitive_load_distribution": self._analyze_cognitive_load_distribution(
                relevant_traces
            ),
            "neural_pathway_usage": self._analyze_neural_pathway_usage(relevant_traces),
            "flag_decision_patterns": self._analyze_flag_decision_patterns(
                relevant_traces
            ),
            "performance_trends": self._analyze_performance_trends(relevant_traces),
            "correlation_patterns": self._analyze_correlation_patterns(relevant_traces),
            "recommendations": [],
        }

        # Generate recommendations
        insights["recommendations"] = await self._generate_trace_recommendations(
            insights, relevant_traces
        )

        return insights

    async def _get_trace_flags(self, cognitive_load: float) -> Dict[str, bool]:
        """Get trace enrichment flags based on cognitive load."""

        # Get cognitive events flags for trace enrichment
        flags = await self.cognitive_manager.get_cognitive_events_flags(
            cognitive_load=cognitive_load
        )

        return {
            "trace_enrichment_enabled": flags.get(
                "cognitive_events.enable_trace_enrichment", False
            ),
            "neural_context_enabled": flags.get(
                "cognitive_events.enable_neural_pathway_routing", False
            ),
            "flag_decisions_enabled": True,  # Always track flag decisions
            "performance_metrics_enabled": cognitive_load
            < 0.8,  # Disable under high load
            "correlations_enabled": cognitive_load < 0.6,  # Only under low-medium load
            "detailed_events_enabled": cognitive_load < 0.5,  # Only under low load
        }

    async def _add_neural_context(
        self,
        trace: CognitiveTrace,
        component_name: str,
        cognitive_context: CognitiveFlagContext,
    ) -> None:
        """Add neural pathway context to trace."""

        # Map component to neural pathway and brain region
        component_neural_mapping = {
            "working_memory": {
                "neural_pathway": NeuralPathway.EXECUTIVE_CONTROL,
                "brain_region": BrainRegion.PREFRONTAL_CORTEX,
                "hemisphere": "bilateral",
                "cognitive_context_type": CognitiveContextType.WORKING_MEMORY,
            },
            "attention_gate": {
                "neural_pathway": NeuralPathway.ATTENTION_RELAY,
                "brain_region": BrainRegion.THALAMUS,
                "hemisphere": "bilateral",
                "cognitive_context_type": CognitiveContextType.ATTENTION_CONTROL,
            },
            "memory_steward": {
                "neural_pathway": NeuralPathway.MEMORY_FORMATION,
                "brain_region": BrainRegion.HIPPOCAMPUS,
                "hemisphere": "bilateral",
                "cognitive_context_type": CognitiveContextType.MEMORY_FORMATION,
            },
            "context_bundle": {
                "neural_pathway": NeuralPathway.RECALL_ASSEMBLY,
                "brain_region": BrainRegion.HIPPOCAMPUS,
                "hemisphere": "bilateral",
                "cognitive_context_type": CognitiveContextType.RECALL_PROCESSING,
            },
            "cognitive_events": {
                "neural_pathway": NeuralPathway.INTER_HEMISPHERIC,
                "brain_region": BrainRegion.CORPUS_CALLOSUM,
                "hemisphere": "bilateral",
                "cognitive_context_type": CognitiveContextType.EXECUTIVE_FUNCTION,
            },
        }

        neural_info = component_neural_mapping.get(component_name, {})

        trace.neural_pathway = neural_info.get("neural_pathway")
        trace.brain_region = neural_info.get("brain_region")
        trace.hemisphere = neural_info.get("hemisphere")
        trace.cognitive_context_type = neural_info.get("cognitive_context_type")

        # Add to annotations
        trace.annotations["neural_pathway"] = (
            trace.neural_pathway.value if trace.neural_pathway else None
        )
        trace.annotations["brain_region"] = (
            trace.brain_region.value if trace.brain_region else None
        )
        trace.annotations["cognitive_context_type"] = (
            trace.cognitive_context_type.value if trace.cognitive_context_type else None
        )

        self.enrichment_stats["neural_contexts_added"] += 1

    async def _add_flag_context(
        self, trace: CognitiveTrace, cognitive_context: CognitiveFlagContext
    ) -> None:
        """Add feature flag context to trace."""

        # Get all cognitive flags
        all_flags = await self.cognitive_manager.get_all_cognitive_flags(
            cognitive_context
        )

        # Flatten flags
        for component, flags in all_flags.items():
            for flag_name, enabled in flags.items():
                trace.active_flags[flag_name] = enabled

                # Track decision reason
                if enabled:
                    trace.flag_decisions[flag_name] = "enabled"
                else:
                    trace.flag_decisions[flag_name] = "disabled_by_cognitive_load"
                    trace.cognitive_overrides.append(flag_name)

        # Add flag statistics to annotations
        total_flags = len(trace.active_flags)
        enabled_flags = sum(trace.active_flags.values())

        trace.annotations["flag_statistics"] = {
            "total_flags": total_flags,
            "enabled_flags": enabled_flags,
            "disabled_flags": total_flags - enabled_flags,
            "cognitive_overrides": len(trace.cognitive_overrides),
        }

        self.enrichment_stats["flag_decisions_tracked"] += total_flags

    async def _add_performance_metrics(self, trace: CognitiveTrace) -> None:
        """Add performance metrics to trace."""

        # Simulate cache hit rates based on component
        component_cache_mapping = {
            "working_memory": ["l1_cache", "l2_cache", "l3_cache"],
            "attention_gate": ["salience_cache", "decision_cache"],
            "memory_steward": ["consolidation_cache", "retrieval_cache"],
            "context_bundle": ["semantic_cache", "temporal_cache"],
            "cognitive_events": ["routing_cache", "correlation_cache"],
        }

        cache_types = component_cache_mapping.get(
            trace.component_name, ["default_cache"]
        )

        for cache_type in cache_types:
            # Simulate cache hit rate based on cognitive load
            base_hit_rate = 0.8
            load_impact = trace.cognitive_load * 0.3
            hit_rate = max(0.1, base_hit_rate - load_impact)
            trace.cache_hit_rates[cache_type] = hit_rate

        # Add performance annotations
        trace.annotations["performance_summary"] = {
            "duration_ms": trace.duration_ms,
            "cpu_utilization": trace.cpu_utilization,
            "memory_usage_mb": trace.memory_usage_mb,
            "average_cache_hit_rate": (
                sum(trace.cache_hit_rates.values()) / len(trace.cache_hit_rates)
                if trace.cache_hit_rates
                else 0.0
            ),
        }

        self.enrichment_stats["performance_metrics_captured"] += 1

    async def _add_trace_correlations(self, trace: CognitiveTrace) -> None:
        """Add trace correlations."""

        # Look for correlations with recent traces
        recent_traces = self.completed_traces[-50:]  # Last 50 traces

        for other_trace in recent_traces:
            if other_trace.trace_id == trace.trace_id:
                continue

            correlation_strength = await self.correlate_traces(trace, other_trace)

            if correlation_strength > 0.5:
                trace.correlated_traces.append(other_trace.trace_id)
                trace.correlation_strength = max(
                    trace.correlation_strength, correlation_strength
                )

                # Track in correlation mapping
                if trace.trace_id not in self.trace_correlations:
                    self.trace_correlations[trace.trace_id] = []
                self.trace_correlations[trace.trace_id].append(other_trace.trace_id)

        if trace.correlated_traces:
            self.enrichment_stats["correlations_found"] += len(trace.correlated_traces)

    async def _add_final_enrichment(self, trace: CognitiveTrace) -> None:
        """Add final enrichment to trace."""

        # Add tags based on trace characteristics
        if trace.duration_ms and trace.duration_ms > 1000:
            trace.tags["performance"] = "slow"
        elif trace.duration_ms and trace.duration_ms < 10:
            trace.tags["performance"] = "fast"
        else:
            trace.tags["performance"] = "normal"

        if trace.cognitive_load > 0.8:
            trace.tags["cognitive_load"] = "high"
        elif trace.cognitive_load < 0.3:
            trace.tags["cognitive_load"] = "low"
        else:
            trace.tags["cognitive_load"] = "medium"

        if len(trace.cognitive_overrides) > 0:
            trace.tags["flag_overrides"] = "present"

        # Add summary annotation
        trace.annotations["enrichment_summary"] = {
            "enrichment_level": self.enrichment_config.detail_level.value,
            "neural_context_added": trace.neural_pathway is not None,
            "flag_decisions_tracked": len(trace.active_flags),
            "correlations_found": len(trace.correlated_traces),
            "events_captured": len(trace.events),
            "enrichment_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _calculate_time_overlap(
        self, trace1: CognitiveTrace, trace2: CognitiveTrace
    ) -> float:
        """Calculate time overlap between two traces."""

        if not all(
            [trace1.start_time, trace1.end_time, trace2.start_time, trace2.end_time]
        ):
            return 0.0

        # Calculate overlap
        overlap_start = max(trace1.start_time, trace2.start_time)
        overlap_end = min(trace1.end_time, trace2.end_time)

        if overlap_start >= overlap_end:
            return 0.0

        overlap_duration = (overlap_end - overlap_start).total_seconds()
        total_duration = max(
            (trace1.end_time - trace1.start_time).total_seconds(),
            (trace2.end_time - trace2.start_time).total_seconds(),
        )

        return overlap_duration / total_duration if total_duration > 0 else 0.0

    def _analyze_cognitive_load_distribution(
        self, traces: List[CognitiveTrace]
    ) -> Dict[str, Any]:
        """Analyze cognitive load distribution across traces."""

        loads = [trace.cognitive_load for trace in traces]

        return {
            "average": sum(loads) / len(loads),
            "min": min(loads),
            "max": max(loads),
            "high_load_traces": len([load for load in loads if load > 0.8]),
            "medium_load_traces": len([load for load in loads if 0.3 <= load <= 0.8]),
            "low_load_traces": len([load for load in loads if load < 0.3]),
        }

    def _analyze_neural_pathway_usage(
        self, traces: List[CognitiveTrace]
    ) -> Dict[str, int]:
        """Analyze neural pathway usage across traces."""

        pathway_counts = {}

        for trace in traces:
            if trace.neural_pathway:
                pathway = trace.neural_pathway.value
                pathway_counts[pathway] = pathway_counts.get(pathway, 0) + 1

        return pathway_counts

    def _analyze_flag_decision_patterns(
        self, traces: List[CognitiveTrace]
    ) -> Dict[str, Any]:
        """Analyze flag decision patterns across traces."""

        all_flags = {}
        override_counts = {}

        for trace in traces:
            for flag_name, enabled in trace.active_flags.items():
                if flag_name not in all_flags:
                    all_flags[flag_name] = {"enabled": 0, "disabled": 0}

                if enabled:
                    all_flags[flag_name]["enabled"] += 1
                else:
                    all_flags[flag_name]["disabled"] += 1

            for override in trace.cognitive_overrides:
                override_counts[override] = override_counts.get(override, 0) + 1

        return {
            "flag_usage": all_flags,
            "cognitive_overrides": override_counts,
            "most_overridden_flags": sorted(
                override_counts.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

    def _analyze_performance_trends(
        self, traces: List[CognitiveTrace]
    ) -> Dict[str, Any]:
        """Analyze performance trends across traces."""

        durations = [trace.duration_ms for trace in traces if trace.duration_ms]
        cpu_usage = [trace.cpu_utilization for trace in traces]
        memory_usage = [trace.memory_usage_mb for trace in traces]

        return {
            "average_duration_ms": sum(durations) / len(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "average_cpu_utilization": (
                sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0
            ),
            "average_memory_usage_mb": (
                sum(memory_usage) / len(memory_usage) if memory_usage else 0
            ),
            "slow_traces": len([d for d in durations if d > 1000]),
            "fast_traces": len([d for d in durations if d < 10]),
        }

    def _analyze_correlation_patterns(
        self, traces: List[CognitiveTrace]
    ) -> Dict[str, Any]:
        """Analyze correlation patterns across traces."""

        total_correlations = sum(len(trace.correlated_traces) for trace in traces)
        correlated_traces = len([trace for trace in traces if trace.correlated_traces])

        return {
            "total_correlations": total_correlations,
            "correlated_traces": correlated_traces,
            "correlation_rate": correlated_traces / len(traces) if traces else 0,
            "average_correlations_per_trace": (
                total_correlations / len(traces) if traces else 0
            ),
        }

    async def _generate_trace_recommendations(
        self, insights: Dict[str, Any], traces: List[CognitiveTrace]
    ) -> List[str]:
        """Generate recommendations based on trace insights."""

        recommendations = []

        # Performance recommendations
        avg_duration = insights["performance_trends"]["average_duration_ms"]
        if avg_duration > 500:
            recommendations.append(
                f"Average trace duration is high ({avg_duration:.1f}ms). Consider optimizing slow operations."
            )

        # Cognitive load recommendations
        load_dist = insights["cognitive_load_distribution"]
        if load_dist["high_load_traces"] > len(traces) * 0.3:
            recommendations.append(
                "High cognitive load detected in many traces. Consider load balancing strategies."
            )

        # Flag override recommendations
        override_patterns = insights["flag_decision_patterns"]["cognitive_overrides"]
        if override_patterns:
            most_overridden = max(override_patterns.items(), key=lambda x: x[1])
            recommendations.append(
                f"Flag '{most_overridden[0]}' frequently overridden ({most_overridden[1]} times). Review thresholds."
            )

        # Correlation recommendations
        correlation_rate = insights["correlation_patterns"]["correlation_rate"]
        if correlation_rate < 0.2:
            recommendations.append(
                "Low trace correlation rate. Components may not be well coordinated."
            )
        elif correlation_rate > 0.8:
            recommendations.append(
                "High trace correlation rate. System showing good coordination."
            )

        return recommendations

    def get_enrichment_statistics(self) -> Dict[str, Any]:
        """Get trace enrichment statistics."""

        total_traces = self.enrichment_stats["traces_enriched"]

        return {
            **self.enrichment_stats,
            "active_traces": len(self.active_traces),
            "completed_traces": len(self.completed_traces),
            "average_enrichment_time_ms": (
                self.enrichment_stats["enrichment_time_ms"] / total_traces
                if total_traces > 0
                else 0.0
            ),
            "correlation_cache_size": len(self.trace_correlations),
        }

    def clear_completed_traces(self) -> None:
        """Clear completed traces to free memory."""
        self.completed_traces.clear()
        self.trace_correlations.clear()

    def reset_statistics(self) -> None:
        """Reset enrichment statistics."""
        self.enrichment_stats = {
            "traces_enriched": 0,
            "enrichment_time_ms": 0.0,
            "correlations_found": 0,
            "flag_decisions_tracked": 0,
            "neural_contexts_added": 0,
            "performance_metrics_captured": 0,
        }
