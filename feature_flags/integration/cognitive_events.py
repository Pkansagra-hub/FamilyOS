"""
Cognitive Events Integration
============================

Feature flag integration for Cognitive Event Router system.
Provides corpus callosum-aware flag evaluation for neural pathway routing operations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from ..flag_manager import CognitiveFlagManager


class RoutingStrategy(Enum):
    """Neural pathway routing strategies."""

    DIRECT = "direct"
    BRAIN_REGION_AFFINITY = "brain_region_affinity"
    LOAD_BALANCED = "load_balanced"
    COGNITIVE_CORRELATION = "cognitive_correlation"
    HEMISPHERE_AWARE = "hemisphere_aware"


class EventPriority(Enum):
    """Cognitive event priorities."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class CognitiveEventsMetrics:
    """Cognitive events performance metrics for flag evaluation."""

    # Event metrics
    events_per_second: float = 0.0
    average_event_size_kb: float = 0.0
    event_queue_depth: int = 0

    # Routing metrics
    routing_latency_ms: float = 0.0
    routing_accuracy: float = 0.0
    cross_hemisphere_events: int = 0

    # Load metrics
    cognitive_load: float = 0.0
    inter_hemispheric_load: float = 0.0
    corpus_callosum_utilization: float = 0.0

    # Performance metrics
    event_throughput: float = 0.0
    routing_efficiency: float = 0.0
    load_balancing_score: float = 0.0

    # Brain region metrics
    left_hemisphere_load: float = 0.0
    right_hemisphere_load: float = 0.0
    prefrontal_activity: float = 0.0
    temporal_lobe_activity: float = 0.0


class CognitiveEventsFlagAdapter:
    """
    Feature flag adapter for Cognitive Event Router system.

    Provides cognitive-aware flag evaluation for:
    - Neural pathway routing algorithms
    - Brain region affinity processing
    - Cognitive correlation analysis
    - Event trace enrichment
    - Load balancing across hemispheres
    """

    def __init__(self, cognitive_manager: CognitiveFlagManager):
        self.cognitive_manager = cognitive_manager
        self.current_metrics = CognitiveEventsMetrics()

        # Flag mappings to specific cognitive events features
        self.flag_features = {
            "cognitive_events.enable_neural_pathway_routing": "neural_pathway_routing",
            "cognitive_events.enable_brain_region_affinity": "brain_region_affinity",
            "cognitive_events.enable_cognitive_correlation": "cognitive_correlation",
            "cognitive_events.enable_trace_enrichment": "trace_enrichment",
            "cognitive_events.enable_load_balancing": "load_balancing",
        }

    async def get_routing_flags(
        self,
        cognitive_load: float = 0.0,
        inter_hemispheric_load: float = 0.0,
        event_throughput: float = 0.0,
    ) -> Dict[str, bool]:
        """Get neural pathway routing flags based on cognitive state."""

        # Update metrics
        self.current_metrics.cognitive_load = cognitive_load
        self.current_metrics.inter_hemispheric_load = inter_hemispheric_load
        self.current_metrics.event_throughput = event_throughput

        flags = await self.cognitive_manager.get_cognitive_events_flags(
            cognitive_load=cognitive_load,
            inter_hemispheric_load=inter_hemispheric_load,
            event_throughput=event_throughput,
            routing_complexity=self.current_metrics.routing_latency_ms / 10.0,
        )

        # Filter to routing-related flags
        routing_flags = {
            "neural_pathway_routing": flags.get(
                "cognitive_events.enable_neural_pathway_routing", False
            ),
            "brain_region_affinity": flags.get(
                "cognitive_events.enable_brain_region_affinity", False
            ),
            "load_balancing": flags.get(
                "cognitive_events.enable_load_balancing", False
            ),
        }

        return routing_flags

    async def get_enrichment_flags(
        self,
        cognitive_load: float = 0.0,
        trace_complexity: float = 0.0,
        correlation_demand: float = 0.0,
    ) -> Dict[str, bool]:
        """Get event enrichment flags based on processing requirements."""

        # Update metrics
        self.current_metrics.cognitive_load = cognitive_load

        flags = await self.cognitive_manager.get_cognitive_events_flags(
            cognitive_load=cognitive_load,
            inter_hemispheric_load=self.current_metrics.inter_hemispheric_load,
            event_throughput=self.current_metrics.event_throughput,
            routing_complexity=trace_complexity,
        )

        # Filter to enrichment-related flags
        enrichment_flags = {
            "cognitive_correlation": flags.get(
                "cognitive_events.enable_cognitive_correlation", False
            ),
            "trace_enrichment": flags.get(
                "cognitive_events.enable_trace_enrichment", False
            ),
        }

        return enrichment_flags

    async def get_routing_strategy(
        self,
        event_type: str,
        cognitive_load: float,
        target_brain_regions: Dict[str, float],
        hemisphere_preference: str = "bilateral",
    ) -> Dict[str, Any]:
        """Get appropriate neural pathway routing strategy."""

        routing_flags = await self.get_routing_flags(
            cognitive_load=cognitive_load,
            inter_hemispheric_load=self.current_metrics.inter_hemispheric_load,
            event_throughput=self.current_metrics.event_throughput,
        )

        neural_routing = routing_flags.get("neural_pathway_routing", False)
        region_affinity = routing_flags.get("brain_region_affinity", False)
        load_balancing = routing_flags.get("load_balancing", False)

        if not neural_routing:
            return {
                "strategy": RoutingStrategy.DIRECT.value,
                "target_regions": ["default"],
                "routing_weights": {"default": 1.0},
                "reason": "Neural pathway routing disabled - using direct routing",
            }

        # Determine strategy based on cognitive load and flags
        if cognitive_load > 0.8:
            # High load - use simple direct routing
            strategy = RoutingStrategy.DIRECT
            primary_region = max(target_brain_regions.items(), key=lambda x: x[1])[0]
            routing_weights = {primary_region: 1.0}
            reason = "Direct routing for high cognitive load"

        elif cognitive_load > 0.5 and load_balancing:
            # Medium load with load balancing - distribute across hemispheres
            strategy = RoutingStrategy.LOAD_BALANCED

            # Calculate hemisphere loads
            left_load = self.current_metrics.left_hemisphere_load
            right_load = self.current_metrics.right_hemisphere_load

            # Prefer less loaded hemisphere
            if hemisphere_preference == "bilateral":
                if left_load < right_load:
                    hemisphere_bias = 0.7  # Favor left
                elif right_load < left_load:
                    hemisphere_bias = 0.3  # Favor right
                else:
                    hemisphere_bias = 0.5  # Balanced
            elif hemisphere_preference == "left":
                hemisphere_bias = 0.8
            elif hemisphere_preference == "right":
                hemisphere_bias = 0.2
            else:
                hemisphere_bias = 0.5

            # Distribute weights based on hemisphere bias
            routing_weights = {}
            for region, affinity in target_brain_regions.items():
                if "left" in region.lower():
                    routing_weights[region] = affinity * hemisphere_bias
                elif "right" in region.lower():
                    routing_weights[region] = affinity * (1.0 - hemisphere_bias)
                else:
                    routing_weights[region] = affinity * 0.5

            reason = (
                f"Load balanced routing with {hemisphere_bias:.1f} left hemisphere bias"
            )

        elif region_affinity:
            # Use brain region affinity routing
            strategy = RoutingStrategy.BRAIN_REGION_AFFINITY

            # Weight regions by affinity and current activity
            routing_weights = {}
            for region, affinity in target_brain_regions.items():
                # Get current activity for region (simulated)
                activity_factor = getattr(
                    self.current_metrics, f"{region.lower()}_activity", 0.5
                )
                # Lower activity regions get higher weights (less congested)
                congestion_factor = 1.0 - activity_factor
                routing_weights[region] = affinity * congestion_factor

            reason = "Brain region affinity routing with congestion awareness"

        else:
            # Low load - use hemisphere-aware routing
            strategy = RoutingStrategy.HEMISPHERE_AWARE

            # Sophisticated routing considering hemisphere specialization
            routing_weights = {}
            for region, affinity in target_brain_regions.items():
                # Apply hemisphere specialization knowledge
                if region.lower() in ["language", "speech", "logic", "analysis"]:
                    # Left hemisphere specialization
                    hemisphere_factor = 1.2 if "left" in region.lower() else 0.8
                elif region.lower() in ["spatial", "creative", "holistic", "pattern"]:
                    # Right hemisphere specialization
                    hemisphere_factor = 1.2 if "right" in region.lower() else 0.8
                else:
                    hemisphere_factor = 1.0

                routing_weights[region] = affinity * hemisphere_factor

            reason = "Hemisphere-aware routing with specialization optimization"

        # Normalize weights
        total_weight = sum(routing_weights.values())
        if total_weight > 0:
            routing_weights = {
                region: weight / total_weight
                for region, weight in routing_weights.items()
            }

        return {
            "strategy": strategy.value,
            "target_regions": list(routing_weights.keys()),
            "routing_weights": routing_weights,
            "hemisphere_preference": hemisphere_preference,
            "cognitive_load": cognitive_load,
            "reason": reason,
        }

    async def get_event_priority(
        self,
        event_type: str,
        cognitive_load: float,
        urgency: float = 0.0,
        source_importance: float = 0.5,
    ) -> Dict[str, Any]:
        """Determine event priority based on cognitive state."""

        routing_flags = await self.get_routing_flags(
            cognitive_load=cognitive_load,
            inter_hemispheric_load=self.current_metrics.inter_hemispheric_load,
            event_throughput=self.current_metrics.event_throughput,
        )

        advanced_routing = routing_flags.get("neural_pathway_routing", False)

        # Base priority calculation
        base_priority_score = (
            (urgency * 0.4) + (source_importance * 0.3) + (0.3)
        )  # 0.3 default

        # Adjust for cognitive load
        if cognitive_load > 0.8:
            # High load - only critical events get high priority
            if urgency > 0.9:
                priority = EventPriority.CRITICAL
                processing_delay_ms = 0
            elif urgency > 0.7:
                priority = EventPriority.HIGH
                processing_delay_ms = 10
            else:
                priority = EventPriority.LOW
                processing_delay_ms = 100

            reason = "High cognitive load - prioritizing only urgent events"

        elif cognitive_load > 0.5:
            # Medium load - normal priority handling
            if base_priority_score > 0.8:
                priority = EventPriority.HIGH
                processing_delay_ms = 5
            elif base_priority_score > 0.5:
                priority = EventPriority.NORMAL
                processing_delay_ms = 20
            else:
                priority = EventPriority.LOW
                processing_delay_ms = 50

            reason = "Medium cognitive load - standard priority handling"

        else:
            # Low load - enhanced priority discrimination
            if advanced_routing:
                if base_priority_score > 0.9:
                    priority = EventPriority.CRITICAL
                    processing_delay_ms = 0
                elif base_priority_score > 0.7:
                    priority = EventPriority.HIGH
                    processing_delay_ms = 2
                elif base_priority_score > 0.4:
                    priority = EventPriority.NORMAL
                    processing_delay_ms = 10
                elif base_priority_score > 0.2:
                    priority = EventPriority.LOW
                    processing_delay_ms = 30
                else:
                    priority = EventPriority.BACKGROUND
                    processing_delay_ms = 200

                reason = "Low cognitive load - enhanced priority discrimination"
            else:
                # Standard priority levels
                if base_priority_score > 0.7:
                    priority = EventPriority.HIGH
                    processing_delay_ms = 5
                elif base_priority_score > 0.4:
                    priority = EventPriority.NORMAL
                    processing_delay_ms = 15
                else:
                    priority = EventPriority.LOW
                    processing_delay_ms = 40

                reason = "Standard priority handling"

        return {
            "priority": priority.value,
            "priority_score": base_priority_score,
            "processing_delay_ms": processing_delay_ms,
            "event_type": event_type,
            "cognitive_load": cognitive_load,
            "urgency": urgency,
            "source_importance": source_importance,
            "reason": reason,
        }

    async def get_correlation_configuration(
        self,
        cognitive_load: float,
        event_volume: int,
        correlation_window_ms: float = 1000.0,
    ) -> Dict[str, Any]:
        """Get cognitive correlation analysis configuration."""

        enrichment_flags = await self.get_enrichment_flags(
            cognitive_load=cognitive_load,
            correlation_demand=event_volume / 100.0,  # Normalize volume
        )

        correlation_enabled = enrichment_flags.get("cognitive_correlation", False)

        if not correlation_enabled or event_volume < 10:
            return {
                "enabled": False,
                "correlation_window_ms": 0,
                "max_correlations": 0,
                "reason": "Correlation disabled or insufficient event volume",
            }

        # Configure correlation based on cognitive load
        if cognitive_load > 0.8:
            # High load - minimal correlation
            correlation_window_ms = min(500.0, correlation_window_ms)
            max_correlations = 3
            correlation_threshold = 0.8  # High threshold
            reason = "Minimal correlation for high cognitive load"

        elif cognitive_load > 0.5:
            # Medium load - moderate correlation
            correlation_window_ms = min(1000.0, correlation_window_ms)
            max_correlations = 5
            correlation_threshold = 0.6
            reason = "Moderate correlation for medium cognitive load"

        else:
            # Low load - comprehensive correlation
            max_correlations = 10
            correlation_threshold = 0.4
            reason = "Comprehensive correlation for low cognitive load"

        # Adjust based on event volume
        volume_factor = min(2.0, event_volume / 50.0)
        adjusted_correlations = int(max_correlations * volume_factor)

        return {
            "enabled": True,
            "correlation_window_ms": correlation_window_ms,
            "max_correlations": adjusted_correlations,
            "correlation_threshold": correlation_threshold,
            "event_volume": event_volume,
            "cognitive_load": cognitive_load,
            "reason": reason,
        }

    async def get_trace_enrichment_config(
        self, cognitive_load: float, trace_detail_level: str = "medium"
    ) -> Dict[str, Any]:
        """Get event trace enrichment configuration."""

        enrichment_flags = await self.get_enrichment_flags(
            cognitive_load=cognitive_load,
            trace_complexity=0.5 if trace_detail_level == "medium" else 0.8,
        )

        trace_enabled = enrichment_flags.get("trace_enrichment", False)

        if not trace_enabled:
            return {
                "enabled": False,
                "detail_level": "none",
                "enrichment_fields": [],
                "reason": "Trace enrichment disabled",
            }

        # Configure enrichment based on cognitive load
        if cognitive_load > 0.8:
            # High load - minimal enrichment
            detail_level = "minimal"
            enrichment_fields = ["timestamp", "event_type", "source"]
            processing_overhead_ms = 1.0
            reason = "Minimal trace enrichment for high cognitive load"

        elif cognitive_load > 0.5:
            # Medium load - standard enrichment
            detail_level = "standard"
            enrichment_fields = [
                "timestamp",
                "event_type",
                "source",
                "target_region",
                "cognitive_context",
                "priority",
            ]
            processing_overhead_ms = 3.0
            reason = "Standard trace enrichment for medium cognitive load"

        else:
            # Low load - comprehensive enrichment
            detail_level = "comprehensive"
            enrichment_fields = [
                "timestamp",
                "event_type",
                "source",
                "target_region",
                "cognitive_context",
                "priority",
                "routing_path",
                "correlations",
                "hemisphere_activity",
                "neural_pathway",
                "processing_latency",
            ]
            processing_overhead_ms = 8.0
            reason = "Comprehensive trace enrichment for low cognitive load"

        return {
            "enabled": True,
            "detail_level": detail_level,
            "enrichment_fields": enrichment_fields,
            "processing_overhead_ms": processing_overhead_ms,
            "cognitive_load": cognitive_load,
            "reason": reason,
        }

    def update_metrics(self, metrics: CognitiveEventsMetrics) -> None:
        """Update current cognitive events metrics."""
        self.current_metrics = metrics

    def get_current_metrics(self) -> CognitiveEventsMetrics:
        """Get current cognitive events metrics."""
        return self.current_metrics

    async def get_adaptive_configuration(self) -> Dict[str, Any]:
        """Get complete adaptive configuration for cognitive events."""

        # Get all cognitive events flags
        flags = await self.cognitive_manager.get_cognitive_events_flags(
            cognitive_load=self.current_metrics.cognitive_load,
            inter_hemispheric_load=self.current_metrics.inter_hemispheric_load,
            event_throughput=self.current_metrics.event_throughput,
            routing_complexity=self.current_metrics.routing_latency_ms / 10.0,
        )

        # Get specific configurations
        routing_config = await self.get_routing_strategy(
            event_type="default",
            cognitive_load=self.current_metrics.cognitive_load,
            target_brain_regions={
                "prefrontal_cortex": 0.8,
                "temporal_lobe": 0.6,
                "hippocampus": 0.7,
            },
            hemisphere_preference="bilateral",
        )

        correlation_config = await self.get_correlation_configuration(
            cognitive_load=self.current_metrics.cognitive_load,
            event_volume=int(self.current_metrics.events_per_second * 10),
            correlation_window_ms=1000.0,
        )

        trace_config = await self.get_trace_enrichment_config(
            cognitive_load=self.current_metrics.cognitive_load,
            trace_detail_level="medium",
        )

        return {
            "flags": flags,
            "configurations": {
                "routing": routing_config,
                "correlation": correlation_config,
                "trace_enrichment": trace_config,
                "performance_thresholds": {
                    "max_routing_latency_ms": 10.0,
                    "max_event_queue_depth": 1000,
                    "max_correlation_window_ms": 2000.0,
                },
            },
            "metrics": self.current_metrics,
            "adaptive_rules": {
                "description": "Cognitive events adaptive configuration",
                "cognitive_load_threshold": 0.8,
                "inter_hemispheric_threshold": 0.7,
                "optimization_target": "routing_efficiency",
            },
        }
