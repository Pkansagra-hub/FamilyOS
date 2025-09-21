"""
Attention Gate Integration
==========================

Feature flag integration for Attention Gate system.
Provides thalamic relay-aware flag evaluation for attention control operations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from ..flag_manager import CognitiveFlagManager


class AttentionState(Enum):
    """Attention gate states for thalamic control."""

    ADMIT = "admit"
    DEFER = "defer"
    BOOST = "boost"
    DROP = "drop"


@dataclass
class AttentionGateMetrics:
    """Attention gate performance metrics for flag evaluation."""

    # Queue metrics
    attention_queue_depth: int = 0
    queue_processing_rate: float = 0.0
    average_wait_time_ms: float = 0.0

    # Load metrics
    cognitive_load: float = 0.0
    thalamus_relay_load: float = 0.0
    attention_switching_frequency: float = 0.0

    # Performance metrics
    gate_latency_ms: float = 0.0
    admission_rate: float = 0.0
    drop_rate: float = 0.0

    # Salience metrics
    average_salience_score: float = 0.0
    salience_variance: float = 0.0
    boost_utilization: float = 0.0


class AttentionGateFlagAdapter:
    """
    Feature flag adapter for Attention Gate system.

    Provides cognitive-aware flag evaluation for:
    - Thalamic admission control (ADMIT/DEFER/BOOST/DROP)
    - Detailed salience analysis
    - Advanced backpressure management
    - Salience boosting algorithms
    - Dropout protection mechanisms
    """

    def __init__(self, cognitive_manager: CognitiveFlagManager):
        self.cognitive_manager = cognitive_manager
        self.current_metrics = AttentionGateMetrics()

        # Flag mappings to specific attention gate features
        self.flag_features = {
            "attention_gate.enable_admission_control": "admission_control",
            "attention_gate.enable_detailed_analysis": "detailed_analysis",
            "attention_gate.enable_backpressure_advanced": "backpressure_advanced",
            "attention_gate.enable_salience_boosting": "salience_boosting",
            "attention_gate.enable_dropout_protection": "dropout_protection",
        }

    async def get_admission_control_flags(
        self,
        queue_depth: int = 0,
        cognitive_load: float = 0.0,
        thalamus_load: float = 0.0,
    ) -> Dict[str, bool]:
        """Get admission control flags based on queue state."""

        # Update metrics
        self.current_metrics.attention_queue_depth = queue_depth
        self.current_metrics.cognitive_load = cognitive_load
        self.current_metrics.thalamus_relay_load = thalamus_load

        flags = await self.cognitive_manager.get_attention_gate_flags(
            cognitive_load=cognitive_load,
            attention_queue_depth=queue_depth,
            thalamus_relay_load=thalamus_load,
            processing_latency_ms=self.current_metrics.gate_latency_ms,
        )

        # Filter to admission control flags
        admission_flags = {
            "admission_control": flags.get(
                "attention_gate.enable_admission_control", False
            ),
            "detailed_analysis": flags.get(
                "attention_gate.enable_detailed_analysis", False
            ),
            "backpressure_advanced": flags.get(
                "attention_gate.enable_backpressure_advanced", False
            ),
        }

        return admission_flags

    async def get_salience_flags(
        self,
        cognitive_load: float = 0.0,
        salience_variance: float = 0.0,
        boost_demand: float = 0.0,
    ) -> Dict[str, bool]:
        """Get salience processing flags based on cognitive state."""

        # Update metrics
        self.current_metrics.cognitive_load = cognitive_load
        self.current_metrics.salience_variance = salience_variance
        self.current_metrics.boost_utilization = boost_demand

        # Convert salience metrics to attention processing load
        processing_latency = (
            salience_variance * 10.0
        )  # Higher variance = more processing time

        flags = await self.cognitive_manager.get_attention_gate_flags(
            cognitive_load=cognitive_load,
            attention_queue_depth=self.current_metrics.attention_queue_depth,
            thalamus_relay_load=cognitive_load,
            processing_latency_ms=processing_latency,
        )

        # Filter to salience-related flags
        salience_flags = {
            "salience_boosting": flags.get(
                "attention_gate.enable_salience_boosting", False
            ),
            "detailed_analysis": flags.get(
                "attention_gate.enable_detailed_analysis", False
            ),
            "dropout_protection": flags.get(
                "attention_gate.enable_dropout_protection", False
            ),
        }

        return salience_flags

    async def should_enable_detailed_analysis(
        self, cognitive_load: float, queue_depth: int, processing_budget_ms: float
    ) -> bool:
        """Determine if detailed salience analysis should be enabled."""

        admission_flags = await self.get_admission_control_flags(
            queue_depth=queue_depth,
            cognitive_load=cognitive_load,
            thalamus_load=cognitive_load,
        )

        # Detailed analysis requires admission control and low cognitive load
        return (
            admission_flags.get("detailed_analysis", False)
            and processing_budget_ms > 5.0
        )  # Need at least 5ms budget

    async def get_admission_decision(
        self,
        item_salience: float,
        cognitive_load: float,
        queue_depth: int,
        urgency: float = 0.0,
    ) -> Dict[str, Any]:
        """Get admission decision for an attention item."""

        flags = await self.get_admission_control_flags(
            queue_depth=queue_depth,
            cognitive_load=cognitive_load,
            thalamus_load=cognitive_load,
        )

        if not flags.get("admission_control", False):
            # Basic admission - always admit if queue has space
            if queue_depth < 50:
                decision = AttentionState.ADMIT
            else:
                decision = AttentionState.DROP

            return {
                "decision": decision.value,
                "reason": "Basic admission control",
                "salience_threshold": 0.5,
                "flags_used": flags,
            }

        # Advanced admission control with cognitive awareness

        # Calculate dynamic thresholds based on load
        base_threshold = 0.3
        cognitive_adjustment = cognitive_load * 0.4  # Higher load = higher threshold
        queue_adjustment = min(0.3, queue_depth / 200.0)  # Queue pressure

        salience_threshold = base_threshold + cognitive_adjustment + queue_adjustment

        # Decision logic
        if urgency > 0.8:  # Emergency items
            decision = AttentionState.ADMIT
            reason = "Emergency urgency override"
        elif item_salience >= salience_threshold + 0.3:  # High salience
            if flags.get("salience_boosting", False):
                decision = AttentionState.BOOST
                reason = "High salience with boost"
            else:
                decision = AttentionState.ADMIT
                reason = "High salience"
        elif item_salience >= salience_threshold:  # Meets threshold
            if queue_depth < 100:
                decision = AttentionState.ADMIT
                reason = "Meets threshold, queue available"
            else:
                decision = AttentionState.DEFER
                reason = "Meets threshold, queue full - defer"
        elif item_salience >= salience_threshold - 0.2:  # Close to threshold
            if cognitive_load < 0.5 and queue_depth < 50:
                decision = AttentionState.ADMIT
                reason = "Low load, queue available - admit borderline"
            else:
                decision = AttentionState.DEFER
                reason = "Borderline salience - defer"
        else:  # Below threshold
            if flags.get("dropout_protection", False) and urgency > 0.3:
                decision = AttentionState.DEFER
                reason = "Dropout protection - defer instead of drop"
            else:
                decision = AttentionState.DROP
                reason = "Below salience threshold"

        return {
            "decision": decision.value,
            "reason": reason,
            "salience_threshold": salience_threshold,
            "item_salience": item_salience,
            "cognitive_load": cognitive_load,
            "queue_depth": queue_depth,
            "flags_used": flags,
        }

    async def get_backpressure_configuration(
        self, cognitive_load: float, queue_depth: int, processing_rate: float
    ) -> Dict[str, Any]:
        """Get backpressure management configuration."""

        flags = await self.get_admission_control_flags(
            queue_depth=queue_depth,
            cognitive_load=cognitive_load,
            thalamus_load=cognitive_load,
        )

        advanced_backpressure = flags.get("backpressure_advanced", False)

        if not advanced_backpressure:
            # Basic backpressure - simple queue limits
            return {
                "enabled": True,
                "strategy": "basic",
                "queue_limit": 100,
                "admission_rate_limit": 10.0,
                "predictive_scaling": False,
                "reason": "Basic backpressure management",
            }

        # Advanced backpressure with predictive scaling

        # Calculate dynamic limits based on cognitive state
        base_queue_limit = 200
        cognitive_reduction = int(cognitive_load * 100)  # Reduce limit under load
        queue_limit = max(50, base_queue_limit - cognitive_reduction)

        # Calculate admission rate limit
        base_rate = 20.0
        load_factor = 1.0 - (cognitive_load * 0.5)  # Reduce rate under load
        admission_rate_limit = base_rate * load_factor

        # Predictive scaling based on trends
        queue_velocity = queue_depth - getattr(self, "_last_queue_depth", queue_depth)
        processing_velocity = processing_rate - getattr(
            self, "_last_processing_rate", processing_rate
        )

        # Store for next comparison
        self._last_queue_depth = queue_depth
        self._last_processing_rate = processing_rate

        # Predictive adjustments
        if queue_velocity > 5:  # Queue growing rapidly
            admission_rate_limit *= 0.8  # Reduce admission rate
            queue_limit = int(queue_limit * 0.9)  # Reduce queue limit
        elif queue_velocity < -5:  # Queue shrinking
            admission_rate_limit *= 1.2  # Allow more admissions

        return {
            "enabled": True,
            "strategy": "advanced_predictive",
            "queue_limit": queue_limit,
            "admission_rate_limit": admission_rate_limit,
            "predictive_scaling": True,
            "queue_velocity": queue_velocity,
            "processing_velocity": processing_velocity,
            "cognitive_load_factor": load_factor,
            "reason": f"Advanced backpressure for cognitive load {cognitive_load:.2f}",
        }

    async def get_boost_strategy(
        self,
        cognitive_load: float,
        available_boost_budget: float,
        high_priority_count: int,
    ) -> Dict[str, Any]:
        """Get salience boost strategy configuration."""

        salience_flags = await self.get_salience_flags(
            cognitive_load=cognitive_load,
            boost_demand=high_priority_count / 20.0,  # Normalize to 0-1
        )

        boost_enabled = salience_flags.get("salience_boosting", False)

        if not boost_enabled or available_boost_budget <= 0:
            return {
                "enabled": False,
                "strategy": "none",
                "boost_multiplier": 1.0,
                "boost_budget": 0.0,
                "reason": "Boost disabled or no budget available",
            }

        # Configure boost strategy based on cognitive load and budget
        if cognitive_load > 0.8:
            # High load - conservative boosting
            strategy = "conservative"
            boost_multiplier = 1.2
            budget_usage = min(0.3, available_boost_budget)
        elif cognitive_load > 0.5:
            # Medium load - balanced boosting
            strategy = "balanced"
            boost_multiplier = 1.5
            budget_usage = min(0.6, available_boost_budget)
        else:
            # Low load - aggressive boosting
            strategy = "aggressive"
            boost_multiplier = 2.0
            budget_usage = available_boost_budget

        return {
            "enabled": True,
            "strategy": strategy,
            "boost_multiplier": boost_multiplier,
            "boost_budget": budget_usage,
            "target_count": min(high_priority_count, int(budget_usage * 10)),
            "reason": f"Using {strategy} boost strategy for load {cognitive_load:.2f}",
        }

    def update_metrics(self, metrics: AttentionGateMetrics) -> None:
        """Update current attention gate metrics."""
        self.current_metrics = metrics

    def get_current_metrics(self) -> AttentionGateMetrics:
        """Get current attention gate metrics."""
        return self.current_metrics

    async def get_adaptive_configuration(self) -> Dict[str, Any]:
        """Get complete adaptive configuration for attention gate."""

        # Get all attention gate flags
        flags = await self.cognitive_manager.get_attention_gate_flags(
            cognitive_load=self.current_metrics.cognitive_load,
            attention_queue_depth=self.current_metrics.attention_queue_depth,
            thalamus_relay_load=self.current_metrics.thalamus_relay_load,
            processing_latency_ms=self.current_metrics.gate_latency_ms,
        )

        # Get specific configurations
        backpressure_config = await self.get_backpressure_configuration(
            cognitive_load=self.current_metrics.cognitive_load,
            queue_depth=self.current_metrics.attention_queue_depth,
            processing_rate=self.current_metrics.queue_processing_rate,
        )

        boost_config = await self.get_boost_strategy(
            cognitive_load=self.current_metrics.cognitive_load,
            available_boost_budget=1.0 - self.current_metrics.cognitive_load,
            high_priority_count=int(self.current_metrics.attention_queue_depth * 0.1),
        )

        return {
            "flags": flags,
            "configurations": {
                "backpressure": backpressure_config,
                "boost_strategy": boost_config,
                "admission_thresholds": {
                    "base_salience_threshold": 0.3,
                    "cognitive_adjustment": self.current_metrics.cognitive_load * 0.4,
                    "queue_adjustment": min(
                        0.3, self.current_metrics.attention_queue_depth / 200.0
                    ),
                },
            },
            "metrics": self.current_metrics,
            "adaptive_rules": {
                "description": "Attention gate adaptive configuration",
                "cognitive_load_threshold": 0.8,
                "queue_depth_threshold": 100,
                "optimization_target": "attention_efficiency",
            },
        }
