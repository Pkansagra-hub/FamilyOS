"""Affect Policy Integration - Emotion-aware access controls."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from policy.abac import AbacContext
from policy.decision import Obligation, PolicyDecision
from storage.stores.cognitive.affect_store import AffectStore

logger = logging.getLogger(__name__)


@dataclass
class AffectPolicyConfig:
    """Configuration for affect-aware policy controls."""

    # Valence thresholds
    high_negative_valence_threshold: float = -0.6  # Strong negative emotion
    low_positive_valence_threshold: float = 0.3  # Mild positive emotion

    # Arousal thresholds
    high_arousal_threshold: float = 0.7  # Highly aroused/excited
    low_arousal_threshold: float = 0.3  # Calm/relaxed

    # Confidence thresholds
    min_confidence_threshold: float = 0.5  # Minimum confidence for affect decisions

    # Band escalation settings
    enable_affect_band_escalation: bool = True
    negative_affect_band_floor: str = "AMBER"  # Escalate to AMBER for negative affect
    high_arousal_band_floor: str = "AMBER"  # Escalate to AMBER for high arousal

    # Redaction settings
    enable_affect_redaction: bool = True
    negative_affect_redaction_categories: List[str] = field(
        default_factory=lambda: ["pii.email", "pii.phone", "sensitive.personal"]
    )

    # Temporal restrictions
    enable_temporal_affect_rules: bool = True
    night_hours_start: int = 22  # 10 PM
    night_hours_end: int = 6  # 6 AM


class AffectPolicyEngine:
    """Affect-aware policy engine for emotion-based access controls."""

    def __init__(
        self, affect_store: AffectStore, config: Optional[AffectPolicyConfig] = None
    ):
        self.affect_store = affect_store
        self.config = config or AffectPolicyConfig()

    def enrich_context_with_affect(
        self, context: AbacContext, person_id: str, space_id: str
    ) -> AbacContext:
        """Enrich ABAC context with current affect state."""
        try:
            # Get current affect state
            affect_state = self.affect_store.get_state(person_id, space_id)

            # Only use affect data if confidence is sufficient
            if affect_state.confidence >= self.config.min_confidence_threshold:
                # Update environmental attributes with affect data
                context.env.arousal = affect_state.a_ema

                # Add affect metadata to request
                if not context.request_metadata:
                    context.request_metadata = {}

                context.request_metadata.update(
                    {
                        "affect_valence": affect_state.v_ema,
                        "affect_arousal": affect_state.a_ema,
                        "affect_confidence": affect_state.confidence,
                        "affect_model_version": affect_state.model_version,
                        "affect_updated_at": affect_state.updated_at,
                    }
                )

                logger.debug(
                    f"Enriched context with affect: v={affect_state.v_ema:.2f}, "
                    f"a={affect_state.a_ema:.2f}, conf={affect_state.confidence:.2f}"
                )
            else:
                logger.debug(
                    f"Affect confidence too low: {affect_state.confidence:.2f}"
                )

        except Exception as e:
            logger.warning(f"Failed to enrich context with affect: {e}")

        return context

    def evaluate_affect_policy(
        self, context: AbacContext, action: str, person_id: str, space_id: str
    ) -> PolicyDecision:
        """Evaluate affect-aware policy and return decision with obligations."""
        decision: str = "ALLOW"
        reasons: List[str] = []
        obligations = Obligation()

        # Get affect data from context
        affect_valence = (
            context.request_metadata.get("affect_valence")
            if context.request_metadata
            else None
        )
        affect_arousal = (
            context.request_metadata.get("affect_arousal")
            if context.request_metadata
            else None
        )
        affect_confidence = (
            context.request_metadata.get("affect_confidence")
            if context.request_metadata
            else None
        )

        if affect_valence is None or affect_confidence is None:
            # No affect data available - use default policies
            logger.debug("No affect data available for policy evaluation")
            return PolicyDecision(
                decision=decision,
                reasons=["no_affect_data_available"],
                obligations=obligations,
            )

        # Only apply affect rules if confidence is sufficient
        if affect_confidence < self.config.min_confidence_threshold:
            logger.debug(f"Affect confidence too low for policy: {affect_confidence}")
            return PolicyDecision(
                decision=decision,
                reasons=["affect_confidence_insufficient"],
                obligations=obligations,
            )

        # Rule 1: High negative valence restrictions
        if affect_valence <= self.config.high_negative_valence_threshold:
            reasons.append("high_negative_affect_detected")

            if self.config.enable_affect_band_escalation:
                obligations.band_min = self.config.negative_affect_band_floor
                reasons.append(
                    f"band_escalated_to_{obligations.band_min}_negative_affect"
                )

            if self.config.enable_affect_redaction:
                obligations.redact.extend(
                    self.config.negative_affect_redaction_categories
                )
                reasons.append("redaction_applied_negative_affect")
                decision = "ALLOW_REDACTED"

        # Rule 2: High arousal restrictions
        if affect_arousal and affect_arousal >= self.config.high_arousal_threshold:
            reasons.append("high_arousal_detected")

            if self.config.enable_affect_band_escalation:
                # Use stronger band floor if not already set
                current_band = obligations.band_min or "GREEN"
                if current_band == "GREEN":
                    obligations.band_min = self.config.high_arousal_band_floor
                    reasons.append(
                        f"band_escalated_to_{obligations.band_min}_high_arousal"
                    )

        # Rule 3: Temporal affect restrictions (night hours + negative affect)
        if self.config.enable_temporal_affect_rules:
            current_hour = int(context.env.time_of_day_hours)
            is_night = (
                current_hour >= self.config.night_hours_start
                or current_hour < self.config.night_hours_end
            )

            if is_night and affect_valence < 0:
                reasons.append("negative_affect_during_night_hours")

                # Restrict certain actions during night hours with negative affect
                risky_night_actions = ["memory.project", "memory.detach", "tools.run"]
                if action in risky_night_actions:
                    obligations.band_min = "AMBER"
                    reasons.append("night_negative_affect_band_escalation")

        # Rule 4: Extreme affect states - additional protections
        if affect_valence <= -0.8 or (affect_arousal and affect_arousal >= 0.9):
            reasons.append("extreme_affect_state_detected")

            # Deny high-risk operations during extreme affect
            extreme_risk_actions = ["privacy.delete", "memory.detach"]
            if action in extreme_risk_actions:
                decision = "DENY"
                reasons.append(f"extreme_affect_denies_{action}")

        # Set audit obligation
        obligations.log_audit = True
        if reasons:
            obligations.reason_tags.extend(reasons)

        logger.debug(
            f"Affect policy evaluation: {decision} for {action} "
            f"(v={affect_valence:.2f}, a={affect_arousal or 0:.2f})"
        )

        return PolicyDecision(
            decision=decision, reasons=reasons, obligations=obligations
        )

    def get_affect_summary(self, person_id: str, space_id: str) -> Dict[str, Any]:
        """Get affect summary for policy reporting."""
        try:
            affect_state = self.affect_store.get_state(person_id, space_id)

            # Get recent affect history
            history = self.affect_store.get_valence_arousal_history(
                person_id, space_id, hours=24
            )

            # Calculate affect trends
            if history:
                recent_valences = [v for _, v, _ in history[-10:]]  # Last 10 entries
                recent_arousals = [a for _, _, a in history[-10:]]

                avg_valence = sum(recent_valences) / len(recent_valences)
                avg_arousal = sum(recent_arousals) / len(recent_arousals)

                # Detect significant changes
                trend_valence = "stable"
                trend_arousal = "stable"

                if len(recent_valences) >= 3:
                    early_valence = sum(recent_valences[:3]) / 3
                    late_valence = sum(recent_valences[-3:]) / 3

                    if late_valence - early_valence > 0.2:
                        trend_valence = "improving"
                    elif early_valence - late_valence > 0.2:
                        trend_valence = "declining"

                if len(recent_arousals) >= 3:
                    early_arousal = sum(recent_arousals[:3]) / 3
                    late_arousal = sum(recent_arousals[-3:]) / 3

                    if late_arousal - early_arousal > 0.2:
                        trend_arousal = "increasing"
                    elif early_arousal - late_arousal > 0.2:
                        trend_arousal = "decreasing"
            else:
                avg_valence = affect_state.v_ema
                avg_arousal = affect_state.a_ema
                trend_valence = "no_data"
                trend_arousal = "no_data"

            return {
                "current_state": {
                    "valence": affect_state.v_ema,
                    "arousal": affect_state.a_ema,
                    "confidence": affect_state.confidence,
                    "updated_at": affect_state.updated_at,
                },
                "24h_summary": {
                    "avg_valence": avg_valence,
                    "avg_arousal": avg_arousal,
                    "trend_valence": trend_valence,
                    "trend_arousal": trend_arousal,
                    "total_entries": len(history),
                },
                "policy_flags": {
                    "high_negative_valence": (
                        affect_state.v_ema
                        <= self.config.high_negative_valence_threshold
                    ),
                    "high_arousal": (
                        affect_state.a_ema >= self.config.high_arousal_threshold
                    ),
                    "sufficient_confidence": (
                        affect_state.confidence >= self.config.min_confidence_threshold
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Failed to get affect summary: {e}")
            return {
                "error": str(e),
                "current_state": None,
                "24h_summary": None,
                "policy_flags": None,
            }

    def update_affect_from_event(
        self, person_id: str, space_id: str, event_data: Dict[str, Any]
    ) -> Optional[str]:
        """Update affect state from an event and return annotation ID."""
        try:
            from storage.stores.cognitive.affect_store import AffectAnnotation

            # Create annotation from event data
            annotation = AffectAnnotation(
                event_id=event_data.get("event_id", f"evt-{int(time.time())}"),
                person_id=person_id,
                space_id=space_id,
                valence=event_data.get("valence", 0.0),
                arousal=event_data.get("arousal", 0.0),
                dominance=event_data.get("dominance"),
                tags=event_data.get("tags", []),
                confidence=event_data.get("confidence", 0.0),
                created_at=event_data.get("created_at", time.time()),
                context_json=event_data.get("context_json"),
            )

            # Store annotation
            annotation_id = self.affect_store.append_annotation(annotation)

            # Update EMA state
            self.affect_store.update_ema_from_annotation(annotation)

            logger.debug(f"Updated affect from event: {annotation_id}")
            return annotation_id

        except Exception as e:
            logger.error(f"Failed to update affect from event: {e}")
            return None
