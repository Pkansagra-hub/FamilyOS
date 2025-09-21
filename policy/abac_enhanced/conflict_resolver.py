"""
Policy Conflict Resolution Engine for ABAC Enhanced System
Implements Issue #27.3: Contract-compliant multi-strategy conflict resolution

This module provides comprehensive conflict detection and resolution capabilities
for the enhanced ABAC system, following the policy-conflict-resolution.yaml contract.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of policy conflicts as defined in contract"""

    DECISION_CONFLICT = "decision_conflict"
    BAND_CONFLICT = "band_conflict"
    OBLIGATION_CONFLICT = "obligation_conflict"
    PRIORITY_CONFLICT = "priority_conflict"
    TEMPORAL_CONFLICT = "temporal_conflict"
    SCOPE_CONFLICT = "scope_conflict"


class ConflictSeverity(Enum):
    """Conflict severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionStrategy(Enum):
    """Available conflict resolution strategies"""

    PRIORITY_RESOLUTION = "priority_resolution"
    DENY_WINS = "deny_wins"
    MOST_RESTRICTIVE_WINS = "most_restrictive_wins"
    WEIGHTED_SCORING = "weighted_scoring"
    CONSENSUS_BUILDING = "consensus_building"


class Band(Enum):
    """Security band levels"""

    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    BLACK = "BLACK"


@dataclass
class PolicyEvaluation:
    """Individual policy evaluation result"""

    policy_id: str
    decision: str  # ALLOW, DENY, ALLOW_REDACTED
    band: Band
    confidence: float
    reasons: List[str]
    obligations: Dict[str, Any]
    evaluation_time_ms: float
    priority: int = 0


@dataclass
class ConflictDetection:
    """Detected conflict information"""

    conflict_type: ConflictType
    severity: ConflictSeverity
    conflicting_policies: List[str]
    description: str
    evidence: Dict[str, Any]
    detected_at: str


@dataclass
class ConflictResolution:
    """Conflict resolution result"""

    strategy_used: ResolutionStrategy
    final_decision: str
    final_band: Band
    final_obligations: Dict[str, Any]
    confidence_score: float
    reasoning: str
    resolution_time_ms: float
    conflicts_resolved: List[ConflictDetection]


@dataclass
class ResolutionRecord:
    """Complete conflict resolution audit record"""

    timestamp: str
    request_id: str
    conflict_type: str
    conflicting_policies: List[str]
    resolution_strategy: str
    final_decision: str
    final_band: str
    final_obligations: Dict[str, Any]
    reasoning: str
    confidence_score: float
    performance_metrics: Dict[str, Any]


class ConflictResolver:
    """
    Enhanced ABAC Conflict Resolution Engine

    Implements comprehensive conflict detection and resolution following
    the policy-conflict-resolution.yaml contract specifications.
    """

    def __init__(self, enable_caching: bool = True):
        self.enable_caching = enable_caching
        self.conflict_pattern_cache = {}
        self.resolution_cache = {}
        self.cache_timestamps = {}

        # Contract-defined weights and thresholds
        self.scoring_weights = {
            "safety_weight": 0.4,
            "security_weight": 0.3,
            "usability_weight": 0.2,
            "performance_weight": 0.1,
        }

        self.band_context_weights = {
            "actor_context": 0.35,
            "device_context": 0.25,
            "environment_context": 0.25,
            "temporal_context": 0.15,
        }

        # Performance thresholds from contract
        self.target_resolution_time_ms = 500
        self.maximum_resolution_time_ms = 1500

    def resolve_conflicts(
        self,
        policy_evaluations: List[PolicyEvaluation],
        request_context: Dict[str, Any],
    ) -> ConflictResolution:
        """
        Main conflict resolution entry point

        Args:
            policy_evaluations: List of individual policy evaluation results
            request_context: Full request context for resolution decisions

        Returns:
            ConflictResolution with final decision and reasoning
        """
        start_time = time.time()

        try:
            # Phase 1: Conflict Detection (500ms timeout)
            conflicts = self._detect_conflicts(policy_evaluations)

            if not conflicts:
                # No conflicts - return consensus or primary result
                return self._build_consensus_result(policy_evaluations, start_time)

            # Phase 2: Conflict Analysis (800ms timeout)
            resolution_strategy = self._select_resolution_strategy(
                conflicts, request_context
            )

            # Phase 3: Conflict Resolution (300ms timeout)
            resolution = self._apply_resolution_strategy(
                resolution_strategy, policy_evaluations, conflicts, request_context
            )

            resolution.resolution_time_ms = (time.time() - start_time) * 1000
            resolution.conflicts_resolved = conflicts

            # Log resolution for monitoring
            self._log_resolution(resolution, request_context)

            return resolution

        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            return self._fallback_resolution(start_time)

    def _detect_conflicts(
        self, evaluations: List[PolicyEvaluation]
    ) -> List[ConflictDetection]:
        """Detect conflicts between policy evaluations"""
        conflicts = []

        if len(evaluations) < 2:
            return conflicts

        # Decision conflicts
        decisions = set(eval.decision for eval in evaluations)
        if len(decisions) > 1:
            conflicts.append(
                ConflictDetection(
                    conflict_type=ConflictType.DECISION_CONFLICT,
                    severity=ConflictSeverity.HIGH,
                    conflicting_policies=[eval.policy_id for eval in evaluations],
                    description=f"Conflicting decisions: {', '.join(decisions)}",
                    evidence={"decisions": list(decisions)},
                    detected_at=datetime.now(timezone.utc).isoformat(),
                )
            )

        # Band conflicts
        bands = set(eval.band for eval in evaluations)
        if len(bands) > 1:
            conflicts.append(
                ConflictDetection(
                    conflict_type=ConflictType.BAND_CONFLICT,
                    severity=ConflictSeverity.MEDIUM,
                    conflicting_policies=[eval.policy_id for eval in evaluations],
                    description=f"Conflicting bands: {', '.join(band.value for band in bands)}",
                    evidence={"bands": [band.value for band in bands]},
                    detected_at=datetime.now(timezone.utc).isoformat(),
                )
            )

        # Obligation conflicts
        obligation_conflicts = self._detect_obligation_conflicts(evaluations)
        conflicts.extend(obligation_conflicts)

        # Priority conflicts
        priority_conflicts = self._detect_priority_conflicts(evaluations)
        conflicts.extend(priority_conflicts)

        return conflicts

    def _detect_obligation_conflicts(
        self, evaluations: List[PolicyEvaluation]
    ) -> List[ConflictDetection]:
        """Detect conflicts in policy obligations"""
        conflicts = []

        # Collect all obligations
        all_obligations = {}
        for eval in evaluations:
            for key, value in eval.obligations.items():
                if key not in all_obligations:
                    all_obligations[key] = []
                all_obligations[key].append((eval.policy_id, value))

        # Check for incompatible obligations (contract-defined)
        incompatible_pairs = [
            ("content_redaction", "full_access_required"),
            ("time_limits", "unlimited_access"),
        ]

        for key, values in all_obligations.items():
            if len(values) > 1:
                # Check for value conflicts
                unique_values = set(str(v[1]) for v in values)
                if len(unique_values) > 1:
                    # Check if these are incompatible
                    for pair in incompatible_pairs:
                        if any(pair[0] in str(v) for v in unique_values) and any(
                            pair[1] in str(v) for v in unique_values
                        ):
                            conflicts.append(
                                ConflictDetection(
                                    conflict_type=ConflictType.OBLIGATION_CONFLICT,
                                    severity=ConflictSeverity.MEDIUM,
                                    conflicting_policies=[v[0] for v in values],
                                    description=f"Incompatible obligations for {key}: {unique_values}",
                                    evidence={
                                        "obligation_key": key,
                                        "values": list(unique_values),
                                    },
                                    detected_at=datetime.now(timezone.utc).isoformat(),
                                )
                            )

        return conflicts

    def _detect_priority_conflicts(
        self, evaluations: List[PolicyEvaluation]
    ) -> List[ConflictDetection]:
        """Detect priority-based conflicts"""
        conflicts = []

        # Group by priority
        priority_groups = {}
        for eval in evaluations:
            priority = eval.priority
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(eval)

        # Check for conflicts within same priority level
        for priority, evals in priority_groups.items():
            if len(evals) > 1:
                decisions = set(eval.decision for eval in evals)
                if len(decisions) > 1:
                    conflicts.append(
                        ConflictDetection(
                            conflict_type=ConflictType.PRIORITY_CONFLICT,
                            severity=ConflictSeverity.LOW,
                            conflicting_policies=[eval.policy_id for eval in evals],
                            description=f"Same priority ({priority}) but different decisions: {decisions}",
                            evidence={
                                "priority": priority,
                                "decisions": list(decisions),
                            },
                            detected_at=datetime.now(timezone.utc).isoformat(),
                        )
                    )

        return conflicts

    def _select_resolution_strategy(
        self, conflicts: List[ConflictDetection], context: Dict[str, Any]
    ) -> ResolutionStrategy:
        """Select appropriate resolution strategy based on conflicts and context"""

        # Emergency override check
        if (
            context.get("urgency") == "emergency"
            or context.get("security_alert_level") == "critical"
        ):
            return ResolutionStrategy.PRIORITY_RESOLUTION

        # Safety-first for minors
        if (
            context.get("actor", {}).get("is_minor")
            or context.get("safety_pressure", 0) > 0.5
        ):
            return ResolutionStrategy.MOST_RESTRICTIVE_WINS

        # Security precedence for untrusted devices
        if context.get("device", {}).get("trust") == "untrusted":
            return ResolutionStrategy.MOST_RESTRICTIVE_WINS

        # High severity conflicts use deny-wins strategy
        high_severity_conflicts = [
            c for c in conflicts if c.severity == ConflictSeverity.HIGH
        ]
        if high_severity_conflicts:
            return ResolutionStrategy.DENY_WINS

        # Multiple medium conflicts use weighted scoring
        medium_conflicts = [
            c for c in conflicts if c.severity == ConflictSeverity.MEDIUM
        ]
        if len(medium_conflicts) > 1:
            return ResolutionStrategy.WEIGHTED_SCORING

        # Default to consensus building for low conflicts
        return ResolutionStrategy.CONSENSUS_BUILDING

    def _apply_resolution_strategy(
        self,
        strategy: ResolutionStrategy,
        evaluations: List[PolicyEvaluation],
        conflicts: List[ConflictDetection],
        context: Dict[str, Any],
    ) -> ConflictResolution:
        """Apply selected resolution strategy"""

        if strategy == ResolutionStrategy.DENY_WINS:
            return self._apply_deny_wins(evaluations, conflicts)
        elif strategy == ResolutionStrategy.MOST_RESTRICTIVE_WINS:
            return self._apply_most_restrictive(evaluations, conflicts)
        elif strategy == ResolutionStrategy.WEIGHTED_SCORING:
            return self._apply_weighted_scoring(evaluations, conflicts, context)
        elif strategy == ResolutionStrategy.CONSENSUS_BUILDING:
            return self._apply_consensus_building(evaluations, conflicts)
        elif strategy == ResolutionStrategy.PRIORITY_RESOLUTION:
            return self._apply_priority_resolution(evaluations, conflicts, context)
        else:
            # Fallback to most restrictive
            return self._apply_most_restrictive(evaluations, conflicts)

    def _apply_deny_wins(
        self, evaluations: List[PolicyEvaluation], conflicts: List[ConflictDetection]
    ) -> ConflictResolution:
        """Apply deny-wins resolution strategy"""

        # Find any DENY decisions
        deny_evals = [e for e in evaluations if e.decision == "DENY"]
        if deny_evals:
            primary_eval = max(deny_evals, key=lambda e: e.confidence)
            return ConflictResolution(
                strategy_used=ResolutionStrategy.DENY_WINS,
                final_decision="DENY",
                final_band=self._select_most_restrictive_band(evaluations),
                final_obligations=primary_eval.obligations,
                confidence_score=primary_eval.confidence,
                reasoning="Policy conflict resolved in favor of security - deny wins strategy applied",
                resolution_time_ms=0.0,
                conflicts_resolved=[],
            )

        # No explicit denies, fall back to most restrictive
        return self._apply_most_restrictive(evaluations, conflicts)

    def _apply_most_restrictive(
        self, evaluations: List[PolicyEvaluation], conflicts: List[ConflictDetection]
    ) -> ConflictResolution:
        """Apply most restrictive resolution strategy"""

        # Decision precedence: DENY > ALLOW_REDACTED > ALLOW
        decision_precedence = {"DENY": 3, "ALLOW_REDACTED": 2, "ALLOW": 1}

        # Find most restrictive decision
        max_restrictive = max(
            evaluations, key=lambda e: decision_precedence.get(e.decision, 0)
        )

        # Find most restrictive band
        restrictive_band = self._select_most_restrictive_band(evaluations)

        # Merge obligations (favor restrictive)
        merged_obligations = self._merge_obligations_restrictive(evaluations)

        return ConflictResolution(
            strategy_used=ResolutionStrategy.MOST_RESTRICTIVE_WINS,
            final_decision=max_restrictive.decision,
            final_band=restrictive_band,
            final_obligations=merged_obligations,
            confidence_score=min(
                e.confidence for e in evaluations
            ),  # Conservative confidence
            reasoning=f"Policy conflict resolved using most restrictive approach: {max_restrictive.decision}/{restrictive_band.value}",
            resolution_time_ms=0.0,
            conflicts_resolved=[],
        )

    def _apply_weighted_scoring(
        self,
        evaluations: List[PolicyEvaluation],
        conflicts: List[ConflictDetection],
        context: Dict[str, Any],
    ) -> ConflictResolution:
        """Apply weighted scoring resolution strategy"""

        scored_evaluations = []

        for eval in evaluations:
            # Calculate weighted score based on contract weights
            safety_score = self._calculate_safety_score(eval, context)
            security_score = self._calculate_security_score(eval, context)
            usability_score = self._calculate_usability_score(eval)
            performance_score = self._calculate_performance_score(eval)

            weighted_score = (
                safety_score * self.scoring_weights["safety_weight"]
                + security_score * self.scoring_weights["security_weight"]
                + usability_score * self.scoring_weights["usability_weight"]
                + performance_score * self.scoring_weights["performance_weight"]
            )

            scored_evaluations.append((eval, weighted_score))

        # Select highest scoring evaluation
        best_eval, best_score = max(scored_evaluations, key=lambda x: x[1])

        return ConflictResolution(
            strategy_used=ResolutionStrategy.WEIGHTED_SCORING,
            final_decision=best_eval.decision,
            final_band=best_eval.band,
            final_obligations=best_eval.obligations,
            confidence_score=best_eval.confidence
            * (best_score / 1.0),  # Adjust by score
            reasoning=f"Policy conflict resolved using weighted scoring (score: {best_score:.3f})",
            resolution_time_ms=0.0,
            conflicts_resolved=[],
        )

    def _apply_consensus_building(
        self, evaluations: List[PolicyEvaluation], conflicts: List[ConflictDetection]
    ) -> ConflictResolution:
        """Apply consensus building resolution strategy"""

        # Find common elements
        decisions = [e.decision for e in evaluations]
        bands = [e.band for e in evaluations]

        # Look for compromise decision
        if "DENY" in decisions and "ALLOW" in decisions:
            compromise_decision = "ALLOW_REDACTED"
        else:
            # Use most common decision
            compromise_decision = max(set(decisions), key=decisions.count)

        # Compromise band (average with safety buffer)
        band_values = {"GREEN": 1, "AMBER": 2, "RED": 3, "BLACK": 4}
        avg_band_value = sum(band_values[b.value] for b in bands) / len(bands)
        compromise_band_value = min(4, int(avg_band_value) + 1)  # Round up for safety

        band_reverse = {1: Band.GREEN, 2: Band.AMBER, 3: Band.RED, 4: Band.BLACK}
        compromise_band = band_reverse[compromise_band_value]

        # Merge compatible obligations
        merged_obligations = self._merge_obligations_compatible(evaluations)

        return ConflictResolution(
            strategy_used=ResolutionStrategy.CONSENSUS_BUILDING,
            final_decision=compromise_decision,
            final_band=compromise_band,
            final_obligations=merged_obligations,
            confidence_score=sum(e.confidence for e in evaluations) / len(evaluations),
            reasoning=f"Policy conflict resolved through consensus building: {compromise_decision}/{compromise_band.value}",
            resolution_time_ms=0.0,
            conflicts_resolved=[],
        )

    def _apply_priority_resolution(
        self,
        evaluations: List[PolicyEvaluation],
        conflicts: List[ConflictDetection],
        context: Dict[str, Any],
    ) -> ConflictResolution:
        """Apply priority-based resolution strategy"""

        # Sort by priority (higher number = higher priority)
        sorted_evals = sorted(evaluations, key=lambda e: e.priority, reverse=True)
        highest_priority_eval = sorted_evals[0]

        # Emergency override logic
        if context.get("urgency") == "emergency":
            reasoning = "Emergency override applied - highest priority policy selected"
        elif context.get("actor", {}).get("is_minor"):
            reasoning = (
                "Safety-first priority for minor - highest priority policy selected"
            )
        else:
            reasoning = f"Priority-based resolution - policy priority {highest_priority_eval.priority} selected"

        return ConflictResolution(
            strategy_used=ResolutionStrategy.PRIORITY_RESOLUTION,
            final_decision=highest_priority_eval.decision,
            final_band=highest_priority_eval.band,
            final_obligations=highest_priority_eval.obligations,
            confidence_score=highest_priority_eval.confidence,
            reasoning=reasoning,
            resolution_time_ms=0.0,
            conflicts_resolved=[],
        )

    def _select_most_restrictive_band(
        self, evaluations: List[PolicyEvaluation]
    ) -> Band:
        """Select most restrictive band from evaluations"""
        band_order = [Band.GREEN, Band.AMBER, Band.RED, Band.BLACK]
        max_band_idx = max(band_order.index(eval.band) for eval in evaluations)
        return band_order[max_band_idx]

    def _merge_obligations_restrictive(
        self, evaluations: List[PolicyEvaluation]
    ) -> Dict[str, Any]:
        """Merge obligations favoring restrictive options"""
        merged = {}

        for eval in evaluations:
            for key, value in eval.obligations.items():
                if key not in merged:
                    merged[key] = value
                else:
                    # Favor more restrictive option
                    if key == "time_limit" and isinstance(value, (int, float)):
                        merged[key] = min(merged[key], value)
                    elif key == "redact" and isinstance(value, bool):
                        merged[key] = merged[key] or value  # True is more restrictive
                    elif key == "monitor" and isinstance(value, bool):
                        merged[key] = (
                            merged[key] or value
                        )  # More monitoring is more restrictive
                    elif isinstance(value, list):
                        # Combine lists and remove duplicates
                        if isinstance(merged[key], list):
                            merged[key] = list(set(merged[key] + value))

        return merged

    def _merge_obligations_compatible(
        self, evaluations: List[PolicyEvaluation]
    ) -> Dict[str, Any]:
        """Merge compatible obligations from all evaluations"""
        merged = {}

        # Contract-defined compatible obligation types
        compatible_groups = [
            ["content_redaction", "enhanced_monitoring"],
            ["time_limits", "activity_tracking"],
            ["adult_notification", "enhanced_logging"],
        ]

        for eval in evaluations:
            for key, value in eval.obligations.items():
                if key not in merged:
                    merged[key] = value
                else:
                    # Check if compatible
                    compatible = False
                    for group in compatible_groups:
                        if key in group:
                            compatible = True
                            break

                    if compatible:
                        # Merge compatible obligations
                        if isinstance(value, list) and isinstance(merged[key], list):
                            merged[key] = list(set(merged[key] + value))
                        elif isinstance(value, bool):
                            merged[key] = merged[key] or value
                        elif isinstance(value, (int, float)):
                            merged[key] = max(
                                merged[key], value
                            )  # More permissive for compatible

        return merged

    def _calculate_safety_score(
        self, eval: PolicyEvaluation, context: Dict[str, Any]
    ) -> float:
        """Calculate safety score for weighted evaluation"""
        score = 0.0

        # Base safety from decision type
        if eval.decision == "DENY":
            score += 0.4
        elif eval.decision == "ALLOW_REDACTED":
            score += 0.6
        else:  # ALLOW
            score += 0.8

        # Adjust for minor protection
        if context.get("actor", {}).get("is_minor") and eval.band in [
            Band.AMBER,
            Band.RED,
        ]:
            score += 0.2

        # Adjust for family context
        if context.get("family_conflict_hint"):
            score += 0.1 if eval.band != Band.GREEN else -0.2

        return min(1.0, score)

    def _calculate_security_score(
        self, eval: PolicyEvaluation, context: Dict[str, Any]
    ) -> float:
        """Calculate security score for weighted evaluation"""
        score = 0.0

        # Base security from band
        band_scores = {Band.GREEN: 0.3, Band.AMBER: 0.5, Band.RED: 0.8, Band.BLACK: 1.0}
        score += band_scores.get(eval.band, 0.5)

        # Adjust for device trust
        device_trust = context.get("device", {}).get("trust", "trusted")
        if device_trust == "untrusted" and eval.band in [Band.RED, Band.BLACK]:
            score += 0.2

        return min(1.0, score)

    def _calculate_usability_score(self, eval: PolicyEvaluation) -> float:
        """Calculate usability score for weighted evaluation"""
        # More permissive decisions have higher usability
        if eval.decision == "ALLOW":
            return 1.0
        elif eval.decision == "ALLOW_REDACTED":
            return 0.6
        else:  # DENY
            return 0.2

    def _calculate_performance_score(self, eval: PolicyEvaluation) -> float:
        """Calculate performance score for weighted evaluation"""
        # Faster evaluations score higher
        if eval.evaluation_time_ms < 10:
            return 1.0
        elif eval.evaluation_time_ms < 50:
            return 0.8
        elif eval.evaluation_time_ms < 100:
            return 0.6
        else:
            return 0.4

    def _build_consensus_result(
        self, evaluations: List[PolicyEvaluation], start_time: float
    ) -> ConflictResolution:
        """Build consensus result when no conflicts detected"""
        if len(evaluations) == 1:
            eval = evaluations[0]
            return ConflictResolution(
                strategy_used=ResolutionStrategy.CONSENSUS_BUILDING,
                final_decision=eval.decision,
                final_band=eval.band,
                final_obligations=eval.obligations,
                confidence_score=eval.confidence,
                reasoning="No conflicts detected - single policy result used",
                resolution_time_ms=(time.time() - start_time) * 1000,
                conflicts_resolved=[],
            )

        # Multiple evaluations but no conflicts - use highest confidence
        best_eval = max(evaluations, key=lambda e: e.confidence)
        return ConflictResolution(
            strategy_used=ResolutionStrategy.CONSENSUS_BUILDING,
            final_decision=best_eval.decision,
            final_band=best_eval.band,
            final_obligations=best_eval.obligations,
            confidence_score=best_eval.confidence,
            reasoning="No conflicts detected - highest confidence policy result used",
            resolution_time_ms=(time.time() - start_time) * 1000,
            conflicts_resolved=[],
        )

    def _fallback_resolution(self, start_time: float) -> ConflictResolution:
        """Fallback resolution when conflict resolution fails"""
        return ConflictResolution(
            strategy_used=ResolutionStrategy.DENY_WINS,
            final_decision="DENY",
            final_band=Band.RED,
            final_obligations={"reason": "conflict_resolution_failure", "audit": True},
            confidence_score=0.3,
            reasoning="Conflict resolution failed - applying fail-safe default (DENY/RED)",
            resolution_time_ms=(time.time() - start_time) * 1000,
            conflicts_resolved=[],
        )

    def _log_resolution(self, resolution: ConflictResolution, context: Dict[str, Any]):
        """Log conflict resolution for monitoring and analysis"""
        logger.info(
            f"Conflict resolution: {resolution.strategy_used.value} -> "
            f"{resolution.final_decision}/{resolution.final_band.value} "
            f"(confidence={resolution.confidence_score:.2f}, "
            f"{resolution.resolution_time_ms:.1f}ms)"
        )

        if resolution.conflicts_resolved:
            logger.debug(
                f"Resolved {len(resolution.conflicts_resolved)} conflicts: "
                f"{[c.conflict_type.value for c in resolution.conflicts_resolved]}"
            )
