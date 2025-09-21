"""
Policy Bridge for Attention Gate

Connects attention gate with the policy enforcement system
for authorization, redaction, and band compliance.

Future-ready for learning integration:
- Phase 1: Static policy evaluation
- Phase 2: Policy performance tracking
- Phase 3: Learning from policy violations
- Phase 4: Adaptive policy recommendations
"""

from datetime import datetime
from typing import Any, Dict, List, NamedTuple, Optional

from .types import GateRequest


class PolicyResult(NamedTuple):
    """Result of policy evaluation"""

    should_drop: bool
    reasons: List[str]
    obligations: List[str]
    band_restrictions: Dict[str, Any]


class PolicyBridge:
    """
    Bridge between attention gate and policy enforcement system.

    Evaluates requests against RBAC/ABAC policies, band restrictions,
    and space-specific rules before admission control.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path

        # Policy evaluation cache
        self.policy_cache: Dict[str, PolicyResult] = {}
        self.cache_ttl = 300  # 5 minutes

        # Policy violation tracking
        self.violation_history: List[Dict[str, Any]] = []

        # Learning integration (Phase 3)
        self.learning_enabled = False

    def evaluate_policy(self, request: GateRequest) -> PolicyResult:
        """
        Evaluate request against all policy constraints.

        Returns policy decision with reasons and obligations.
        """
        # Quick validation for required fields
        if not self._validate_required_fields(request):
            return PolicyResult(
                should_drop=True,
                reasons=["missing_required_policy_fields"],
                obligations=[],
                band_restrictions={},
            )

        # Check cache for recent evaluations
        cache_key = self._generate_cache_key(request)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result

        reasons = []
        obligations = []
        should_drop = False
        band_restrictions = {}

        # Band-level policy evaluation
        band_result = self._evaluate_band_policy(request)
        if band_result["should_drop"]:
            should_drop = True
            reasons.extend(band_result["reasons"])

        obligations.extend(band_result["obligations"])
        band_restrictions.update(band_result["restrictions"])

        # Space-level policy evaluation
        space_result = self._evaluate_space_policy(request)
        if space_result["should_drop"]:
            should_drop = True
            reasons.extend(space_result["reasons"])

        obligations.extend(space_result["obligations"])

        # Actor-level policy evaluation
        actor_result = self._evaluate_actor_policy(request)
        if actor_result["should_drop"]:
            should_drop = True
            reasons.extend(actor_result["reasons"])

        obligations.extend(actor_result["obligations"])

        # Content-level policy evaluation (if content provided)
        if request.content:
            content_result = self._evaluate_content_policy(request)
            if content_result["should_drop"]:
                should_drop = True
                reasons.extend(content_result["reasons"])

            obligations.extend(content_result["obligations"])

        result = PolicyResult(
            should_drop=should_drop,
            reasons=reasons,
            obligations=list(set(obligations)),  # Deduplicate
            band_restrictions=band_restrictions,
        )

        # Cache result
        self._cache_result(cache_key, result)

        # Record for learning
        self._record_policy_evaluation(request, result)

        return result

    def _validate_required_fields(self, request: GateRequest) -> bool:
        """Validate that request has required policy fields"""
        if not request.policy:
            return False

        if not request.policy.band:
            return False

        if not request.actor or not request.actor.person_id:
            return False

        if not request.space_id:
            return False

        return True

    def _evaluate_band_policy(self, request: GateRequest) -> Dict[str, Any]:
        """Evaluate band-level policy constraints"""
        band = request.policy.band
        reasons = []
        obligations = []
        restrictions = {}
        should_drop = False

        # Band restrictions by level
        if band == "BLACK":
            # BLACK band - maximum restrictions
            should_drop = True
            reasons.append("black_band_admission_denied")

        elif band == "RED":
            # RED band - restricted operations
            restrictions.update(
                {
                    "max_processing_time_ms": 5000,
                    "require_audit": True,
                    "content_redaction": "required",
                }
            )
            obligations.append("audit_red_band_request")

        elif band == "AMBER":
            # AMBER band - moderate restrictions
            restrictions.update(
                {"max_processing_time_ms": 15000, "content_filtering": "enabled"}
            )
            obligations.append("log_amber_band_request")

        elif band == "GREEN":
            # GREEN band - minimal restrictions
            restrictions.update({"max_processing_time_ms": 30000})

        else:
            # Unknown band
            should_drop = True
            reasons.append(f"unknown_band_{band}")

        return {
            "should_drop": should_drop,
            "reasons": reasons,
            "obligations": obligations,
            "restrictions": restrictions,
        }

    def _evaluate_space_policy(self, request: GateRequest) -> Dict[str, Any]:
        """Evaluate space-level policy constraints"""
        space_id = request.space_id
        reasons = []
        obligations = []
        should_drop = False

        # Space validation
        if not space_id or space_id == "":
            should_drop = True
            reasons.append("invalid_space_id")
            return {
                "should_drop": should_drop,
                "reasons": reasons,
                "obligations": obligations,
            }

        # Check space access permissions
        if not self._check_space_access(request.actor, space_id):
            should_drop = True
            reasons.append("space_access_denied")

        # Space-specific obligations
        if space_id.startswith("family:"):
            obligations.append("family_space_audit")
        elif space_id.startswith("personal:"):
            obligations.append("personal_space_privacy")
        elif space_id.startswith("shared:"):
            obligations.append("shared_space_tracking")

        return {
            "should_drop": should_drop,
            "reasons": reasons,
            "obligations": obligations,
        }

    def _evaluate_actor_policy(self, request: GateRequest) -> Dict[str, Any]:
        """Evaluate actor-level policy constraints"""
        actor = request.actor
        reasons = []
        obligations = []
        should_drop = False

        # Actor validation
        if not actor.person_id:
            should_drop = True
            reasons.append("missing_actor_person_id")

        # Check for suspended/blocked actors
        if self._is_actor_suspended(actor.person_id):
            should_drop = True
            reasons.append("actor_suspended")

        # Role-based restrictions
        actor_role = getattr(actor, "role", "user")
        if actor_role == "guest":
            # Guests have limited access
            obligations.append("guest_access_audit")
        elif actor_role == "child":
            # Child actors have special protections
            obligations.append("child_safety_compliance")
            obligations.append("parental_oversight")

        return {
            "should_drop": should_drop,
            "reasons": reasons,
            "obligations": obligations,
        }

    def _evaluate_content_policy(self, request: GateRequest) -> Dict[str, Any]:
        """Evaluate content-level policy constraints"""
        content = request.content
        reasons = []
        obligations = []
        should_drop = False

        if not content or not content.text:
            return {"should_drop": False, "reasons": [], "obligations": []}

        content_text = content.text.lower()

        # Content filtering based on band
        band = request.policy.band

        if band in ["RED", "BLACK"]:
            # Strict content filtering for sensitive bands
            if self._contains_sensitive_content(content_text):
                should_drop = True
                reasons.append("sensitive_content_blocked")

            obligations.append("content_audit_required")

        # Length restrictions
        if len(content.text) > 50000:  # 50KB limit
            should_drop = True
            reasons.append("content_too_large")

        # Check for PII in content
        if self._contains_pii(content_text):
            obligations.append("pii_redaction_required")

        return {
            "should_drop": should_drop,
            "reasons": reasons,
            "obligations": obligations,
        }

    def _check_space_access(self, actor: Any, space_id: str) -> bool:
        """Check if actor has access to space"""
        # TODO: Implement actual space access checking
        # For now, allow access to all spaces
        return True

    def _is_actor_suspended(self, person_id: str) -> bool:
        """Check if actor is suspended"""
        # TODO: Implement actual suspension checking
        # For now, no actors are suspended
        return False

    def _contains_sensitive_content(self, content: str) -> bool:
        """Check for sensitive content patterns"""
        sensitive_patterns = [
            "password",
            "secret",
            "token",
            "api_key",
            "credit card",
            "ssn",
            "social security",
        ]

        return any(pattern in content for pattern in sensitive_patterns)

    def _contains_pii(self, content: str) -> bool:
        """Check for personally identifiable information"""
        # Simple PII detection patterns
        import re

        # Email pattern
        if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", content):
            return True

        # Phone pattern
        if re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", content):
            return True

        # SSN pattern
        if re.search(r"\b\d{3}-\d{2}-\d{4}\b", content):
            return True

        return False

    def _generate_cache_key(self, request: GateRequest) -> str:
        """Generate cache key for policy evaluation"""
        return f"{request.actor.person_id}:{request.space_id}:{request.policy.band}:v1"

    def _get_cached_result(self, cache_key: str) -> Optional[PolicyResult]:
        """Get cached policy result if still valid"""
        # TODO: Implement actual caching with TTL
        # For now, no caching
        return None

    def _cache_result(self, cache_key: str, result: PolicyResult) -> None:
        """Cache policy evaluation result"""
        # TODO: Implement actual caching
        # For now, no caching
        pass

    def _record_policy_evaluation(
        self, request: GateRequest, result: PolicyResult
    ) -> None:
        """Record policy evaluation for learning"""
        if len(self.violation_history) > 1000:
            # Keep only recent evaluations
            self.violation_history = self.violation_history[-500:]

        self.violation_history.append(
            {
                "request_id": request.request_id,
                "actor_id": request.actor.person_id,
                "space_id": request.space_id,
                "band": request.policy.band,
                "dropped": result.should_drop,
                "reasons": result.reasons,
                "obligations_count": len(result.obligations),
                "timestamp": datetime.now().isoformat(),
            }
        )

    def get_policy_metrics(self) -> Dict[str, Any]:
        """Get policy evaluation metrics"""
        if not self.violation_history:
            return {"status": "no_data"}

        recent_evals = self.violation_history[-100:]

        # Calculate metrics
        total_evaluations = len(recent_evals)
        dropped_count = sum(1 for eval in recent_evals if eval["dropped"])
        drop_rate = dropped_count / total_evaluations if total_evaluations > 0 else 0.0

        # Band distribution
        band_distribution = {}
        for eval in recent_evals:
            band = eval["band"]
            band_distribution[band] = band_distribution.get(band, 0) + 1

        # Most common drop reasons
        drop_reasons = {}
        for eval in recent_evals:
            if eval["dropped"]:
                for reason in eval["reasons"]:
                    drop_reasons[reason] = drop_reasons.get(reason, 0) + 1

        return {
            "total_evaluations": total_evaluations,
            "drop_rate": drop_rate,
            "band_distribution": band_distribution,
            "top_drop_reasons": sorted(
                drop_reasons.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }
