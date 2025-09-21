"""
Attention Gate Salience Calculator

Future-ready salience calculation supporting:
- Phase 1: Explainable linear formulas (production-safe)
- Phase 2: Temperature scaling and calibration
- Phase 3: Online learning and weight adaptation
- Phase 4: Neural models with safety guardrails

Designed for admission control rather than general cognitive salience.
"""

import math
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from .config import get_config
from .types import GateRequest, SalienceFeatures, SalienceWeights


@dataclass
class SalienceResult:
    """Complete salience calculation result with tracing"""

    raw_score: float
    calibrated_priority: float
    features: SalienceFeatures
    weights: SalienceWeights
    execution_time_ms: float
    confidence: float = 1.0
    uncertainty: float = 0.0


class SalienceCalculator:
    """
    Admission-focused salience calculator with learning integration.

    Unlike core/salience.py (global workspace), this focuses on smart-path
    admission control with backpressure and policy-aware scoring.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path

        # Feature extractors (pluggable for future extensions)
        self.feature_extractors = {
            "urgency": self._extract_urgency,
            "novelty": self._extract_novelty,
            "value": self._extract_value,
            "risk": self._extract_risk,
            "cost": self._extract_cost,
            "social_risk": self._extract_social_risk,
            "affect_arousal": self._extract_affect_arousal,
            "affect_valence": self._extract_affect_valence,
            "context_bump": self._extract_context_bump,
            "temporal_fit": self._extract_temporal_fit,
        }

        # Learning integration hooks
        self.adaptation_hooks = []
        self.outcome_callbacks = []

    def calculate_salience(self, request: GateRequest) -> SalienceResult:
        """
        Calculate admission salience with full tracing.

        Returns calibrated priority score with complete feature breakdown
        for explainability and learning integration.
        """
        start_time = time.perf_counter()

        # Get current configuration (supports hot-reloading)
        config = get_config()

        # Extract features
        features = self._extract_features(request)

        # Get weights (may be adapted by learning)
        weights = config.salience_weights

        # Calculate raw score
        raw_score = self._calculate_raw_score(features, weights)

        # Apply calibration (Phase 2: light learning)
        calibrated_priority = self._apply_calibration(raw_score, weights)

        # Calculate confidence and uncertainty
        confidence, uncertainty = self._calculate_confidence(features, weights)

        execution_time = (time.perf_counter() - start_time) * 1000

        return SalienceResult(
            raw_score=raw_score,
            calibrated_priority=calibrated_priority,
            features=features,
            weights=weights,
            execution_time_ms=execution_time,
            confidence=confidence,
            uncertainty=uncertainty,
        )

    def _extract_features(self, request: GateRequest) -> SalienceFeatures:
        """Extract all salience features from request"""
        features = SalienceFeatures()

        # Extract each feature using registered extractors
        for feature_name, extractor in self.feature_extractors.items():
            try:
                feature_value = extractor(request)
                setattr(features, feature_name, feature_value)
            except Exception:
                # Graceful degradation - log error but continue
                # In production, would use proper logging
                feature_value = 0.0
                setattr(features, feature_name, feature_value)

        # Store raw features for extensibility
        features.raw_features = {
            name: getattr(features, name) for name in self.feature_extractors.keys()
        }

        return features

    def _calculate_raw_score(
        self, features: SalienceFeatures, weights: SalienceWeights
    ) -> float:
        """
        Calculate raw salience score using explainable linear model.

        Formula: S = w_u*urgency + w_n*novelty + w_v*value - w_r*risk
                   + w_a*affect_arousal - w_c*cost - w_s*social_risk + bias
        """
        score = (
            weights.urgency * features.urgency
            + weights.novelty * features.novelty
            + weights.value * features.value
            + weights.affect_arousal * features.affect_arousal
            + weights.affect_valence * features.affect_valence
            + weights.context_bump * features.context_bump
            + weights.temporal_fit * features.temporal_fit
            + weights.personal_relevance * features.personal_relevance
            + weights.goal_alignment * features.goal_alignment
            + weights.bias
            - weights.risk * features.risk
            - weights.cost * features.cost
            - weights.social_risk * features.social_risk
        )

        return score

    def _apply_calibration(self, raw_score: float, weights: SalienceWeights) -> float:
        """
        Apply calibration to convert raw score to [0,1] priority.

        Supports:
        - Temperature scaling: σ(score/T)
        - Platt scaling: σ(A*score + B)
        - Future: learned calibration functions
        """
        # Temperature scaling
        temperature_scaled = raw_score / weights.temperature

        # Platt scaling
        platt_scaled = weights.platt_a * temperature_scaled + weights.platt_b

        # Sigmoid to [0,1]
        calibrated = self._sigmoid(platt_scaled)

        # Clip to ensure bounds
        return max(0.0, min(1.0, calibrated))

    def _calculate_confidence(
        self, features: SalienceFeatures, weights: SalienceWeights
    ) -> Tuple[float, float]:
        """
        Calculate confidence and uncertainty for learning integration.

        Higher confidence = more reliable salience estimate
        Higher uncertainty = more potential for learning
        """
        # Base confidence on feature completeness
        total_features = len(self.feature_extractors)
        available_features = sum(
            1
            for name in self.feature_extractors.keys()
            if getattr(features, name, 0.0) > 0.0
        )
        feature_completeness = available_features / total_features

        # Confidence decreases with extreme values (might be outliers)
        extremity_penalty = 0.0
        for name in self.feature_extractors.keys():
            value = getattr(features, name, 0.0)
            if value > 0.8 or value < 0.2:  # Extreme values
                extremity_penalty += 0.1

        confidence = feature_completeness - min(0.3, extremity_penalty)
        uncertainty = 1.0 - confidence

        return max(0.1, confidence), max(0.0, uncertainty)

    @staticmethod
    def _sigmoid(x: float) -> float:
        """Numerically stable sigmoid function"""
        if x >= 0:
            exp_neg_x = math.exp(-x)
            return 1 / (1 + exp_neg_x)
        else:
            exp_x = math.exp(x)
            return exp_x / (1 + exp_x)

    # Feature Extraction Methods
    # These are designed to be explainable and replaceable for learning

    def _extract_urgency(self, request: GateRequest) -> float:
        """
        Extract urgency signal from request.

        Considers: deadlines, explicit urgency tags, temporal proximity
        """
        urgency = 0.0

        # Check for explicit urgency indicators
        payload = request.payload
        text = payload.get("text", "").lower()

        # Temporal urgency patterns
        urgent_patterns = [
            "asap",
            "urgent",
            "emergency",
            "now",
            "immediately",
            "today",
            "tonight",
            "this morning",
            "deadline",
        ]

        for pattern in urgent_patterns:
            if pattern in text:
                urgency += 0.3

        # Deadline proximity (if available in hints)
        hints = payload.get("hints", {})
        if "deadline" in hints:
            # Would calculate time to deadline here
            # For now, assume presence indicates urgency
            urgency += 0.4

        # Affect arousal can indicate urgency
        if request.affect and request.affect.arousal > 0.7:
            urgency += 0.2

        # QoS constraints indicate urgency
        if request.qos and request.qos.budget_ms < 10:
            urgency += 0.1

        return min(1.0, urgency)

    def _extract_novelty(self, request: GateRequest) -> float:
        """
        Extract novelty signal - how different from recent requests.

        Simple implementation - would integrate with deduplication system.
        """
        novelty = 0.5  # Default medium novelty

        # Check context for recent similar requests
        if request.context:
            recent_similar = request.context.recent_similar_requests
            if recent_similar == 0:
                novelty = 1.0  # Completely novel
            elif recent_similar < 3:
                novelty = 0.7  # Somewhat novel
            else:
                novelty = 0.2  # Likely duplicate

        # Longer text often indicates more novel content
        text_length = len(request.payload.get("text", ""))
        if text_length > 100:
            novelty += 0.1
        elif text_length < 20:
            novelty -= 0.1

        return max(0.0, min(1.0, novelty))

    def _extract_value(self, request: GateRequest) -> float:
        """
        Extract estimated value/importance of request.

        Simple heuristics - would integrate with learned value models.
        """
        value = 0.5  # Default medium value

        payload = request.payload
        text = payload.get("text", "").lower()

        # High-value action types
        high_value_patterns = [
            "save",
            "remember",
            "note",
            "important",
            "critical",
            "meeting",
            "appointment",
            "deadline",
            "project",
        ]

        for pattern in high_value_patterns:
            if pattern in text:
                value += 0.2

        # Low-value patterns
        low_value_patterns = ["test", "hello", "hi", "thanks", "ok"]

        for pattern in low_value_patterns:
            if pattern in text:
                value -= 0.2

        # Attachments often indicate higher value
        if payload.get("attachments"):
            value += 0.1

        return max(0.0, min(1.0, value))

    def _extract_risk(self, request: GateRequest) -> float:
        """
        Extract policy and safety risk.

        Higher risk = more likely to be deferred or dropped.
        """
        risk = 0.0

        # Policy band risk
        band = request.policy.band
        if band == "BLACK":
            risk += 0.8
        elif band == "RED":
            risk += 0.6
        elif band == "AMBER":
            risk += 0.3
        # GREEN adds no risk

        # Check for risky content patterns
        text = request.payload.get("text", "").lower()
        risky_patterns = ["share", "send", "email", "post", "publish", "external"]

        for pattern in risky_patterns:
            if pattern in text:
                risk += 0.2

        # Device trust affects risk
        device_trust = request.policy.abac.get("device_trust", "medium")
        if device_trust == "low":
            risk += 0.3
        elif device_trust == "high":
            risk -= 0.1

        return max(0.0, min(1.0, risk))

    def _extract_cost(self, request: GateRequest) -> float:
        """
        Extract computational cost estimate.

        Higher cost = more likely to be deferred in resource constraints.
        """
        cost = 0.3  # Default moderate cost

        # Text length affects processing cost
        text_length = len(request.payload.get("text", ""))
        if text_length > 500:
            cost += 0.3
        elif text_length > 200:
            cost += 0.1

        # Attachments increase cost
        attachments = request.payload.get("attachments", [])
        cost += min(0.4, len(attachments) * 0.1)

        # QoS constraints
        if request.qos:
            if request.qos.device_thermal == "Hot":
                cost += 0.2
            elif request.qos.device_thermal == "Critical":
                cost += 0.4

        return max(0.0, min(1.0, cost))

    def _extract_social_risk(self, request: GateRequest) -> float:
        """
        Extract social/family context risk.

        Higher social risk when children present, family conflict risk, etc.
        """
        social_risk = 0.0

        # Child presence increases social risk for some content
        if request.context and request.context.child_present:
            text = request.payload.get("text", "").lower()

            # Adult-oriented content with children present
            adult_patterns = ["work", "stress", "money", "politics"]
            for pattern in adult_patterns:
                if pattern in text:
                    social_risk += 0.2

        # Time of day affects social appropriateness
        if request.context and request.context.time_of_day:
            if request.context.time_of_day in ["late_night", "early_morning"]:
                social_risk += 0.1

        return max(0.0, min(1.0, social_risk))

    def _extract_affect_arousal(self, request: GateRequest) -> float:
        """Extract affect arousal for priority boosting"""
        if request.affect:
            return request.affect.arousal
        return 0.0

    def _extract_affect_valence(self, request: GateRequest) -> float:
        """Extract affect valence for mood-aware processing"""
        if request.affect:
            return (request.affect.valence + 1.0) / 2.0  # Convert [-1,1] to [0,1]
        return 0.5  # Neutral

    def _extract_context_bump(self, request: GateRequest) -> float:
        """Extract context-specific priority adjustments"""
        bump = 0.0

        # Urgent intent tag
        if request.affect and "urgent" in request.affect.tags:
            bump += 0.15

        # Late night penalty (unless urgent)
        if (
            request.context
            and request.context.time_of_day == "late_night"
            and (not request.affect or "urgent" not in request.affect.tags)
        ):
            bump -= 0.05

        return bump

    def _extract_temporal_fit(self, request: GateRequest) -> float:
        """
        Extract temporal/circadian fitness.

        Simple implementation - would integrate with temporal module.
        """
        # Default medium fit
        temporal_fit = 0.5

        if request.context and request.context.time_of_day:
            time_of_day = request.context.time_of_day

            # Peak productive hours
            if time_of_day in ["morning", "afternoon"]:
                temporal_fit = 0.8
            # Less optimal hours
            elif time_of_day in ["early_morning", "late_night"]:
                temporal_fit = 0.3
            # Evening - moderate
            elif time_of_day == "evening":
                temporal_fit = 0.6

        return temporal_fit

    # Learning Integration Methods (Future Phases)

    def register_adaptation_hook(self, hook_func):
        """Register hook for learning adaptations"""
        self.adaptation_hooks.append(hook_func)

    def register_outcome_callback(self, callback_func):
        """Register callback for outcome learning"""
        self.outcome_callbacks.append(callback_func)

    def record_outcome(self, request_id: str, outcome: str, metrics: Dict[str, Any]):
        """
        Record outcome for learning integration.

        Phase 3: This will feed into learning system for weight adaptation.
        """
        for callback in self.outcome_callbacks:
            try:
                callback(request_id, outcome, metrics)
            except Exception:
                # Log error but don't fail the system
                pass

    def adapt_weights(self, adaptation_update: Dict[str, Any]):
        """
        Apply weight adaptation from learning system.

        Phase 3: This enables online learning while maintaining safety.
        """
        for hook in self.adaptation_hooks:
            try:
                hook(adaptation_update)
            except Exception:
                # Log error but don't apply unsafe adaptations
                pass


# Factory function for dependency injection
def create_salience_calculator(config_path: Optional[str] = None) -> SalienceCalculator:
    """Create salience calculator with configuration"""
    return SalienceCalculator(config_path)
