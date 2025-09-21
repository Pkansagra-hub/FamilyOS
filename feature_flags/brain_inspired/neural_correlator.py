"""
Neural Pathway Correlator
=========================

Advanced neural pathway correlation analysis for MemoryOS.
Provides brain-inspired correlation detection across cognitive components
with neural pathway routing and cognitive trace enrichment.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from ..flag_manager import CognitiveFlagContext, CognitiveFlagManager


class CorrelationType(Enum):
    """Types of neural pathway correlations."""

    TEMPORAL = "temporal"  # Time-based correlations
    SPATIAL = "spatial"  # Brain region correlations
    CAUSAL = "causal"  # Cause-effect relationships
    SEMANTIC = "semantic"  # Meaning-based correlations
    FUNCTIONAL = "functional"  # Function-based correlations


class NeuralPathway(Enum):
    """Major neural pathways in MemoryOS."""

    EXECUTIVE_CONTROL = "executive_control"
    ATTENTION_RELAY = "attention_relay"
    MEMORY_FORMATION = "memory_formation"
    RECALL_ASSEMBLY = "recall_assembly"
    INTER_HEMISPHERIC = "inter_hemispheric"
    SENSORY_PROCESSING = "sensory_processing"
    MOTOR_OUTPUT = "motor_output"
    EMOTIONAL_REGULATION = "emotional_regulation"


class BrainRegion(Enum):
    """Brain regions for correlation analysis."""

    PREFRONTAL_CORTEX = "prefrontal_cortex"
    HIPPOCAMPUS = "hippocampus"
    THALAMUS = "thalamus"
    CORPUS_CALLOSUM = "corpus_callosum"
    TEMPORAL_LOBE = "temporal_lobe"
    PARIETAL_LOBE = "parietal_lobe"
    OCCIPITAL_LOBE = "occipital_lobe"
    CEREBELLUM = "cerebellum"


@dataclass
class NeuralEvent:
    """Represents a neural pathway event for correlation analysis."""

    # Event identification
    event_id: str
    event_type: str
    source_component: str

    # Timing information
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float = 0.0

    # Neural pathway context
    neural_pathway: Optional[NeuralPathway] = None
    brain_region: Optional[BrainRegion] = None
    hemisphere: Optional[str] = None  # left, right, bilateral

    # Cognitive context
    cognitive_load: float = 0.0
    working_memory_load: float = 0.0
    attention_queue_depth: int = 0

    # Event data
    event_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Correlation tracking
    correlated_events: Set[str] = field(default_factory=set)
    correlation_strength: float = 0.0


@dataclass
class CorrelationResult:
    """Results of neural pathway correlation analysis."""

    correlation_id: str
    correlation_type: CorrelationType
    correlation_strength: float
    confidence_score: float

    # Events involved
    primary_event: NeuralEvent
    correlated_events: List[NeuralEvent]

    # Pathway analysis
    neural_pathway_pattern: List[NeuralPathway]
    brain_region_pattern: List[BrainRegion]
    hemisphere_activity: Dict[str, float]

    # Timing analysis
    temporal_window_ms: float
    average_latency_ms: float
    sequence_probability: float

    # Cognitive impact
    cognitive_load_impact: float
    performance_correlation: float
    adaptive_behavior_score: float


class NeuralPathwayCorrelator:
    """
    Advanced neural pathway correlation analyzer.

    Provides brain-inspired correlation detection including:
    - Temporal correlation analysis
    - Spatial brain region correlations
    - Causal relationship detection
    - Semantic similarity correlations
    - Functional pathway analysis
    """

    def __init__(self, cognitive_manager: CognitiveFlagManager):
        self.cognitive_manager = cognitive_manager
        self.event_buffer: List[NeuralEvent] = []
        self.correlation_cache: Dict[str, CorrelationResult] = {}

        # Configuration
        self.max_buffer_size = 1000
        self.correlation_window_ms = 5000.0  # 5 second window
        self.min_correlation_strength = 0.3

        # Statistics
        self.correlation_stats = {
            "events_processed": 0,
            "correlations_found": 0,
            "cache_hits": 0,
            "temporal_correlations": 0,
            "spatial_correlations": 0,
            "causal_correlations": 0,
        }

    async def add_neural_event(self, event: NeuralEvent) -> None:
        """Add a neural event for correlation analysis."""

        # Check if correlation analysis is enabled
        correlation_flags = await self._get_correlation_flags(event.cognitive_load)

        if not correlation_flags.get("neural_correlation_enabled", False):
            return

        # Add to buffer
        self.event_buffer.append(event)
        self.correlation_stats["events_processed"] += 1

        # Maintain buffer size
        if len(self.event_buffer) > self.max_buffer_size:
            self.event_buffer.pop(0)

        # Trigger correlation analysis if enabled
        if correlation_flags.get("real_time_analysis", False):
            await self._analyze_correlations_for_event(event)

    async def analyze_temporal_correlations(
        self, time_window_ms: float = None, min_strength: float = None
    ) -> List[CorrelationResult]:
        """Analyze temporal correlations in recent events."""

        window = time_window_ms or self.correlation_window_ms
        strength_threshold = min_strength or self.min_correlation_strength

        correlations = []
        current_time = datetime.now(timezone.utc)

        # Filter events within time window
        recent_events = [
            event
            for event in self.event_buffer
            if (current_time - event.timestamp).total_seconds() * 1000 <= window
        ]

        if len(recent_events) < 2:
            return correlations

        # Analyze temporal patterns
        for i, primary_event in enumerate(recent_events[:-1]):
            for j, secondary_event in enumerate(recent_events[i + 1 :], i + 1):

                # Calculate temporal correlation
                correlation = await self._calculate_temporal_correlation(
                    primary_event, secondary_event
                )

                if correlation.correlation_strength >= strength_threshold:
                    correlations.append(correlation)
                    self.correlation_stats["temporal_correlations"] += 1

        return correlations

    async def analyze_spatial_correlations(
        self, brain_regions: List[BrainRegion] = None
    ) -> List[CorrelationResult]:
        """Analyze spatial correlations between brain regions."""

        target_regions = brain_regions or list(BrainRegion)
        correlations = []

        # Group events by brain region
        region_events = {}
        for event in self.event_buffer:
            if event.brain_region and event.brain_region in target_regions:
                if event.brain_region not in region_events:
                    region_events[event.brain_region] = []
                region_events[event.brain_region].append(event)

        # Analyze cross-region correlations
        region_pairs = [
            (r1, r2)
            for i, r1 in enumerate(region_events.keys())
            for r2 in list(region_events.keys())[i + 1 :]
        ]

        for region1, region2 in region_pairs:
            events1 = region_events[region1]
            events2 = region_events[region2]

            correlation = await self._calculate_spatial_correlation(
                events1, events2, region1, region2
            )

            if correlation.correlation_strength >= self.min_correlation_strength:
                correlations.append(correlation)
                self.correlation_stats["spatial_correlations"] += 1

        return correlations

    async def analyze_causal_relationships(
        self, cognitive_load: float = 0.0
    ) -> List[CorrelationResult]:
        """Analyze causal relationships between neural events."""

        # Check if causal analysis is enabled
        correlation_flags = await self._get_correlation_flags(cognitive_load)

        if not correlation_flags.get("causal_analysis_enabled", False):
            return []

        correlations = []

        # Sort events by timestamp for causal analysis
        sorted_events = sorted(self.event_buffer, key=lambda e: e.timestamp)

        # Look for causal patterns
        for i, cause_event in enumerate(sorted_events[:-1]):
            for effect_event in sorted_events[
                i + 1 : i + 10
            ]:  # Look ahead 10 events max

                # Calculate causal correlation
                correlation = await self._calculate_causal_correlation(
                    cause_event, effect_event
                )

                if correlation.correlation_strength >= self.min_correlation_strength:
                    correlations.append(correlation)
                    self.correlation_stats["causal_correlations"] += 1

        return correlations

    async def analyze_pathway_efficiency(
        self, pathway: NeuralPathway, cognitive_context: CognitiveFlagContext
    ) -> Dict[str, Any]:
        """Analyze efficiency of a specific neural pathway."""

        # Filter events for this pathway
        pathway_events = [
            event for event in self.event_buffer if event.neural_pathway == pathway
        ]

        if not pathway_events:
            return {
                "pathway": pathway.value,
                "efficiency_score": 0.0,
                "event_count": 0,
                "analysis": "No events found for pathway",
            }

        # Calculate efficiency metrics
        total_duration = sum(event.duration_ms for event in pathway_events)
        average_duration = total_duration / len(pathway_events)

        # Calculate load correlation
        load_correlation = await self._calculate_load_correlation(
            pathway_events, cognitive_context
        )

        # Calculate efficiency score
        efficiency_score = await self._calculate_pathway_efficiency_score(
            pathway_events, average_duration, load_correlation
        )

        return {
            "pathway": pathway.value,
            "efficiency_score": efficiency_score,
            "event_count": len(pathway_events),
            "average_duration_ms": average_duration,
            "total_duration_ms": total_duration,
            "load_correlation": load_correlation,
            "cognitive_load_impact": cognitive_context.cognitive_load,
            "recommendations": await self._generate_pathway_recommendations(
                pathway, efficiency_score, cognitive_context
            ),
        }

    async def get_correlation_insights(
        self, correlation_type: CorrelationType = None
    ) -> Dict[str, Any]:
        """Get insights from correlation analysis."""

        all_correlations = []

        if correlation_type is None or correlation_type == CorrelationType.TEMPORAL:
            temporal = await self.analyze_temporal_correlations()
            all_correlations.extend(temporal)

        if correlation_type is None or correlation_type == CorrelationType.SPATIAL:
            spatial = await self.analyze_spatial_correlations()
            all_correlations.extend(spatial)

        if correlation_type is None or correlation_type == CorrelationType.CAUSAL:
            causal = await self.analyze_causal_relationships()
            all_correlations.extend(causal)

        # Generate insights
        insights = {
            "total_correlations": len(all_correlations),
            "correlation_types": {},
            "strongest_correlations": [],
            "pathway_patterns": {},
            "brain_region_activity": {},
            "cognitive_load_patterns": {},
            "recommendations": [],
        }

        # Analyze correlation types
        for correlation in all_correlations:
            corr_type = correlation.correlation_type.value
            if corr_type not in insights["correlation_types"]:
                insights["correlation_types"][corr_type] = 0
            insights["correlation_types"][corr_type] += 1

        # Find strongest correlations
        insights["strongest_correlations"] = sorted(
            all_correlations, key=lambda c: c.correlation_strength, reverse=True
        )[:5]

        # Analyze pathway patterns
        for correlation in all_correlations:
            for pathway in correlation.neural_pathway_pattern:
                pathway_name = pathway.value
                if pathway_name not in insights["pathway_patterns"]:
                    insights["pathway_patterns"][pathway_name] = {
                        "count": 0,
                        "avg_strength": 0.0,
                        "strengths": [],
                    }
                insights["pathway_patterns"][pathway_name]["count"] += 1
                insights["pathway_patterns"][pathway_name]["strengths"].append(
                    correlation.correlation_strength
                )

        # Calculate average strengths
        for pathway_name, data in insights["pathway_patterns"].items():
            data["avg_strength"] = sum(data["strengths"]) / len(data["strengths"])

        # Generate recommendations
        insights["recommendations"] = (
            await self._generate_correlation_insights_recommendations(
                all_correlations, insights
            )
        )

        return insights

    async def _get_correlation_flags(self, cognitive_load: float) -> Dict[str, bool]:
        """Get correlation analysis flags based on cognitive load."""

        # Get cognitive events flags for correlation analysis
        flags = await self.cognitive_manager.get_cognitive_events_flags(
            cognitive_load=cognitive_load
        )

        return {
            "neural_correlation_enabled": flags.get(
                "cognitive_events.enable_neural_pathway_routing", False
            ),
            "real_time_analysis": flags.get(
                "cognitive_events.enable_cognitive_correlation", False
            ),
            "causal_analysis_enabled": cognitive_load < 0.7,  # Disable under high load
            "advanced_features": cognitive_load
            < 0.5,  # Enable advanced features under low load
        }

    async def _calculate_temporal_correlation(
        self, event1: NeuralEvent, event2: NeuralEvent
    ) -> CorrelationResult:
        """Calculate temporal correlation between two events."""

        # Calculate time difference
        time_diff = abs((event2.timestamp - event1.timestamp).total_seconds() * 1000)

        # Base correlation on temporal proximity
        max_time_diff = self.correlation_window_ms
        temporal_strength = max(0.0, 1.0 - (time_diff / max_time_diff))

        # Adjust for event type similarity
        type_similarity = 1.0 if event1.event_type == event2.event_type else 0.3

        # Adjust for component similarity
        component_similarity = (
            1.0 if event1.source_component == event2.source_component else 0.5
        )

        # Adjust for neural pathway similarity
        pathway_similarity = 1.0
        if event1.neural_pathway and event2.neural_pathway:
            pathway_similarity = (
                1.0 if event1.neural_pathway == event2.neural_pathway else 0.6
            )

        # Calculate overall correlation strength
        correlation_strength = (
            temporal_strength * 0.4
            + type_similarity * 0.2
            + component_similarity * 0.2
            + pathway_similarity * 0.2
        )

        # Calculate confidence based on data quality
        confidence = min(1.0, correlation_strength * 1.2)

        return CorrelationResult(
            correlation_id=f"temporal_{event1.event_id}_{event2.event_id}_{int(time.time())}",
            correlation_type=CorrelationType.TEMPORAL,
            correlation_strength=correlation_strength,
            confidence_score=confidence,
            primary_event=event1,
            correlated_events=[event2],
            neural_pathway_pattern=[
                p for p in [event1.neural_pathway, event2.neural_pathway] if p
            ],
            brain_region_pattern=[
                r for r in [event1.brain_region, event2.brain_region] if r
            ],
            hemisphere_activity=self._calculate_hemisphere_activity([event1, event2]),
            temporal_window_ms=time_diff,
            average_latency_ms=time_diff,
            sequence_probability=correlation_strength,
            cognitive_load_impact=abs(event1.cognitive_load - event2.cognitive_load),
            performance_correlation=1.0
            - abs(event1.cognitive_load - event2.cognitive_load),
            adaptive_behavior_score=correlation_strength * confidence,
        )

    async def _calculate_spatial_correlation(
        self,
        events1: List[NeuralEvent],
        events2: List[NeuralEvent],
        region1: BrainRegion,
        region2: BrainRegion,
    ) -> CorrelationResult:
        """Calculate spatial correlation between brain regions."""

        # Calculate activity correlation between regions
        activity1 = len(events1)
        activity2 = len(events2)

        # Normalize activity levels
        max_activity = max(activity1, activity2)
        if max_activity == 0:
            activity_correlation = 0.0
        else:
            activity_correlation = min(activity1, activity2) / max_activity

        # Calculate timing correlation
        if events1 and events2:
            avg_time1 = sum((e.timestamp.timestamp() for e in events1)) / len(events1)
            avg_time2 = sum((e.timestamp.timestamp() for e in events2)) / len(events2)
            time_diff = abs(avg_time1 - avg_time2) * 1000  # Convert to ms

            timing_correlation = max(
                0.0, 1.0 - (time_diff / self.correlation_window_ms)
            )
        else:
            timing_correlation = 0.0

        # Calculate cognitive load correlation
        if events1 and events2:
            avg_load1 = sum(e.cognitive_load for e in events1) / len(events1)
            avg_load2 = sum(e.cognitive_load for e in events2) / len(events2)
            load_correlation = 1.0 - abs(avg_load1 - avg_load2)
        else:
            load_correlation = 0.0

        # Overall spatial correlation
        spatial_strength = (
            activity_correlation * 0.4
            + timing_correlation * 0.4
            + load_correlation * 0.2
        )

        return CorrelationResult(
            correlation_id=f"spatial_{region1.value}_{region2.value}_{int(time.time())}",
            correlation_type=CorrelationType.SPATIAL,
            correlation_strength=spatial_strength,
            confidence_score=min(1.0, spatial_strength * 1.1),
            primary_event=events1[0] if events1 else events2[0],
            correlated_events=events1 + events2,
            neural_pathway_pattern=[],
            brain_region_pattern=[region1, region2],
            hemisphere_activity=self._calculate_hemisphere_activity(events1 + events2),
            temporal_window_ms=self.correlation_window_ms,
            average_latency_ms=0.0,
            sequence_probability=spatial_strength,
            cognitive_load_impact=(
                abs(avg_load1 - avg_load2) if events1 and events2 else 0.0
            ),
            performance_correlation=load_correlation,
            adaptive_behavior_score=spatial_strength * min(1.0, spatial_strength * 1.1),
        )

    async def _calculate_causal_correlation(
        self, cause_event: NeuralEvent, effect_event: NeuralEvent
    ) -> CorrelationResult:
        """Calculate causal correlation between events."""

        # Time difference (cause must precede effect)
        time_diff = (
            effect_event.timestamp - cause_event.timestamp
        ).total_seconds() * 1000

        if time_diff <= 0:  # Effect cannot precede cause
            return CorrelationResult(
                correlation_id=f"causal_invalid_{cause_event.event_id}_{effect_event.event_id}",
                correlation_type=CorrelationType.CAUSAL,
                correlation_strength=0.0,
                confidence_score=0.0,
                primary_event=cause_event,
                correlated_events=[effect_event],
                neural_pathway_pattern=[],
                brain_region_pattern=[],
                hemisphere_activity={},
                temporal_window_ms=0.0,
                average_latency_ms=0.0,
                sequence_probability=0.0,
                cognitive_load_impact=0.0,
                performance_correlation=0.0,
                adaptive_behavior_score=0.0,
            )

        # Calculate causal likelihood based on temporal proximity
        causal_window = 2000.0  # 2 second causal window
        temporal_likelihood = max(0.0, 1.0 - (time_diff / causal_window))

        # Calculate semantic similarity
        semantic_similarity = await self._calculate_semantic_similarity(
            cause_event, effect_event
        )

        # Calculate pathway connectivity
        pathway_connectivity = await self._calculate_pathway_connectivity(
            cause_event.neural_pathway, effect_event.neural_pathway
        )

        # Calculate causal strength
        causal_strength = (
            temporal_likelihood * 0.4
            + semantic_similarity * 0.3
            + pathway_connectivity * 0.3
        )

        # Confidence based on multiple factors
        confidence = min(1.0, causal_strength * 1.2 * temporal_likelihood)

        return CorrelationResult(
            correlation_id=f"causal_{cause_event.event_id}_{effect_event.event_id}_{int(time.time())}",
            correlation_type=CorrelationType.CAUSAL,
            correlation_strength=causal_strength,
            confidence_score=confidence,
            primary_event=cause_event,
            correlated_events=[effect_event],
            neural_pathway_pattern=[
                p
                for p in [cause_event.neural_pathway, effect_event.neural_pathway]
                if p
            ],
            brain_region_pattern=[
                r for r in [cause_event.brain_region, effect_event.brain_region] if r
            ],
            hemisphere_activity=self._calculate_hemisphere_activity(
                [cause_event, effect_event]
            ),
            temporal_window_ms=time_diff,
            average_latency_ms=time_diff,
            sequence_probability=causal_strength,
            cognitive_load_impact=abs(
                cause_event.cognitive_load - effect_event.cognitive_load
            ),
            performance_correlation=1.0
            - abs(cause_event.cognitive_load - effect_event.cognitive_load),
            adaptive_behavior_score=causal_strength * confidence,
        )

    def _calculate_hemisphere_activity(
        self, events: List[NeuralEvent]
    ) -> Dict[str, float]:
        """Calculate hemisphere activity distribution."""

        hemisphere_counts = {"left": 0, "right": 0, "bilateral": 0, "unknown": 0}

        for event in events:
            hemisphere = event.hemisphere or "unknown"
            hemisphere_counts[hemisphere] += 1

        total_events = len(events)
        if total_events == 0:
            return {k: 0.0 for k in hemisphere_counts}

        return {k: v / total_events for k, v in hemisphere_counts.items()}

    async def _calculate_semantic_similarity(
        self, event1: NeuralEvent, event2: NeuralEvent
    ) -> float:
        """Calculate semantic similarity between events."""

        # Simple semantic similarity based on event types and components
        type_similarity = 1.0 if event1.event_type == event2.event_type else 0.3
        component_similarity = (
            1.0 if event1.source_component == event2.source_component else 0.5
        )

        # Calculate data similarity (simplified)
        data_similarity = 0.5  # Default similarity

        return (type_similarity + component_similarity + data_similarity) / 3.0

    async def _calculate_pathway_connectivity(
        self, pathway1: Optional[NeuralPathway], pathway2: Optional[NeuralPathway]
    ) -> float:
        """Calculate connectivity strength between neural pathways."""

        if not pathway1 or not pathway2:
            return 0.5  # Default connectivity

        if pathway1 == pathway2:
            return 1.0  # Same pathway

        # Define pathway connectivity matrix (simplified)
        connectivity_matrix = {
            (NeuralPathway.EXECUTIVE_CONTROL, NeuralPathway.ATTENTION_RELAY): 0.8,
            (NeuralPathway.ATTENTION_RELAY, NeuralPathway.MEMORY_FORMATION): 0.7,
            (NeuralPathway.MEMORY_FORMATION, NeuralPathway.RECALL_ASSEMBLY): 0.9,
            (NeuralPathway.EXECUTIVE_CONTROL, NeuralPathway.MEMORY_FORMATION): 0.6,
            (NeuralPathway.INTER_HEMISPHERIC, NeuralPathway.EXECUTIVE_CONTROL): 0.7,
        }

        # Check both directions
        connectivity = connectivity_matrix.get(
            (pathway1, pathway2), connectivity_matrix.get((pathway2, pathway1), 0.3)
        )

        return connectivity

    async def _calculate_load_correlation(
        self, events: List[NeuralEvent], cognitive_context: CognitiveFlagContext
    ) -> float:
        """Calculate correlation between events and cognitive load."""

        if not events:
            return 0.0

        avg_event_load = sum(event.cognitive_load for event in events) / len(events)
        current_load = cognitive_context.cognitive_load

        # Calculate correlation (inverse of difference)
        load_correlation = 1.0 - abs(avg_event_load - current_load)

        return max(0.0, load_correlation)

    async def _calculate_pathway_efficiency_score(
        self,
        events: List[NeuralEvent],
        average_duration: float,
        load_correlation: float,
    ) -> float:
        """Calculate efficiency score for a neural pathway."""

        # Base efficiency on duration (shorter is better)
        duration_efficiency = max(
            0.0, 1.0 - (average_duration / 1000.0)
        )  # Normalize to 1 second

        # Load efficiency based on correlation
        load_efficiency = load_correlation

        # Event frequency efficiency
        event_frequency = len(events)
        frequency_efficiency = min(
            1.0, event_frequency / 50.0
        )  # Normalize to 50 events

        # Overall efficiency
        efficiency_score = (
            duration_efficiency * 0.4
            + load_efficiency * 0.3
            + frequency_efficiency * 0.3
        )

        return efficiency_score

    async def _generate_pathway_recommendations(
        self,
        pathway: NeuralPathway,
        efficiency_score: float,
        cognitive_context: CognitiveFlagContext,
    ) -> List[str]:
        """Generate recommendations for pathway optimization."""

        recommendations = []

        if efficiency_score < 0.3:
            recommendations.append(
                f"Low efficiency detected for {pathway.value} pathway"
            )
            recommendations.append(
                "Consider reducing cognitive load or optimizing component performance"
            )

        if efficiency_score < 0.5:
            recommendations.append(
                "Enable performance monitoring for detailed analysis"
            )

        if cognitive_context.cognitive_load > 0.8:
            recommendations.append(
                "High cognitive load may be impacting pathway efficiency"
            )
            recommendations.append("Consider enabling adaptive load balancing")

        if efficiency_score > 0.8:
            recommendations.append(f"{pathway.value} pathway performing optimally")
            recommendations.append(
                "Current configuration is well-suited for this workload"
            )

        return recommendations

    async def _generate_correlation_insights_recommendations(
        self, correlations: List[CorrelationResult], insights: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on correlation insights."""

        recommendations = []

        if insights["total_correlations"] == 0:
            recommendations.append("No significant correlations detected")
            recommendations.append(
                "Consider increasing correlation window or reducing thresholds"
            )
            return recommendations

        # Analyze correlation strength distribution
        strong_correlations = [c for c in correlations if c.correlation_strength > 0.7]
        weak_correlations = [c for c in correlations if c.correlation_strength < 0.4]

        if len(strong_correlations) > len(correlations) * 0.3:
            recommendations.append("High number of strong correlations detected")
            recommendations.append("System showing good neural pathway coordination")

        if len(weak_correlations) > len(correlations) * 0.5:
            recommendations.append("Many weak correlations detected")
            recommendations.append("Consider optimizing component coordination")

        # Pathway-specific recommendations
        pathway_patterns = insights["pathway_patterns"]
        for pathway, data in pathway_patterns.items():
            if data["avg_strength"] > 0.7:
                recommendations.append(
                    f"{pathway} pathway showing strong correlation patterns"
                )
            elif data["avg_strength"] < 0.4:
                recommendations.append(f"{pathway} pathway may need optimization")

        return recommendations

    async def _analyze_correlations_for_event(self, event: NeuralEvent) -> None:
        """Analyze correlations for a new event in real-time."""

        # Look for correlations with recent events
        recent_events = [
            e
            for e in self.event_buffer[-10:]  # Last 10 events
            if e.event_id != event.event_id
        ]

        for recent_event in recent_events:
            correlation = await self._calculate_temporal_correlation(
                recent_event, event
            )

            if correlation.correlation_strength >= self.min_correlation_strength:
                # Cache the correlation
                self.correlation_cache[correlation.correlation_id] = correlation
                self.correlation_stats["correlations_found"] += 1

    def get_correlation_statistics(self) -> Dict[str, Any]:
        """Get correlation analysis statistics."""

        total_events = self.correlation_stats["events_processed"]
        total_correlations = self.correlation_stats["correlations_found"]

        return {
            "events_processed": total_events,
            "correlations_found": total_correlations,
            "correlation_rate": (
                total_correlations / total_events if total_events > 0 else 0.0
            ),
            "cache_size": len(self.correlation_cache),
            "buffer_size": len(self.event_buffer),
            "temporal_correlations": self.correlation_stats["temporal_correlations"],
            "spatial_correlations": self.correlation_stats["spatial_correlations"],
            "causal_correlations": self.correlation_stats["causal_correlations"],
            "cache_hit_rate": (
                self.correlation_stats["cache_hits"] / total_events
                if total_events > 0
                else 0.0
            ),
        }

    def clear_correlation_cache(self) -> None:
        """Clear the correlation cache."""
        self.correlation_cache.clear()

    def reset_statistics(self) -> None:
        """Reset correlation statistics."""
        self.correlation_stats = {
            "events_processed": 0,
            "correlations_found": 0,
            "cache_hits": 0,
            "temporal_correlations": 0,
            "spatial_correlations": 0,
            "causal_correlations": 0,
        }
