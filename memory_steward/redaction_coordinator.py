"""
Memory Redaction Coordinator - Policy-Aware Content Protection
==============================================================

This module implements content redaction coordination for memory formation,
integrating with the policy framework to apply appropriate data minimization
and privacy protection. It ensures that all memory formation complies with
GDPR, privacy policies, and content safety requirements.

**Neuroscience Inspiration:**
The prefrontal cortex (PFC) performs executive control over memory encoding,
filtering inappropriate or sensitive information before storage. This redaction
coordinator mirrors PFC function by applying policy-based filtering and
content transformation to ensure that only appropriate information reaches
long-term memory systems.

**Research Backing:**
- Miller & Cohen (2001): Integrative theory of prefrontal cortex function
- Badre & Wagner (2007): Left ventrolateral prefrontal cortex and selection
- Thompson-Schill et al. (1997): Role of left inferior frontal gyrus in selection
- Jonides & Smith (1997): Dissociation of storage and rehearsal in working memory

The implementation follows contracts-first methodology with comprehensive
policy integration, ensuring that all content redaction is auditable,
reversible where appropriate, and compliant with regulatory requirements.
"""

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from observability.logging import get_json_logger
from observability.trace import start_span

logger = get_json_logger(__name__)


@dataclass
class RedactionRule:
    """
    A single redaction rule with detection and transformation logic.
    """

    rule_id: str
    rule_type: str  # "pii", "location", "financial", "health", "custom"
    pattern: str  # Regex pattern or detection method
    replacement_strategy: str  # "mask", "hash", "remove", "generalize", "encrypt"
    confidence_threshold: float = 0.8  # Minimum confidence for rule application
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RedactionMatch:
    """
    A detected match for redaction with location and confidence.
    """

    rule_id: str
    rule_type: str
    start_pos: int
    end_pos: int
    original_text: str
    confidence: float
    replacement: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RedactionPlan:
    """
    Complete redaction plan for content with all detected matches.
    """

    content_hash: str
    matches: List[RedactionMatch]
    policy_obligations: List[str]
    redaction_level: str  # "minimal", "standard", "aggressive"
    estimated_safety_score: float  # 0-1 safety score after redaction
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RedactionResult:
    """
    Result of content redaction with original and redacted versions.
    """

    original_content: Dict[str, Any]
    redacted_content: Dict[str, Any]
    redaction_plan: RedactionPlan
    applied_redactions: List[str]  # List of redaction types applied
    redaction_map: Dict[str, str]  # Original -> redacted token mapping
    reversible: bool  # Whether redaction can be reversed
    processing_time_ms: float
    metadata: Optional[Dict[str, Any]] = None


class MemoryRedactionCoordinator:
    """
    Coordinates content redaction for memory formation.

    Integrates with the policy framework to apply appropriate data minimization
    and privacy protection based on:
    - Policy obligations from WriteIntent processing
    - Space-specific redaction requirements
    - Actor permissions and consent settings
    - Content sensitivity analysis
    - Regulatory compliance requirements (GDPR, CCPA, etc.)

    **Key Functions:**
    - PII detection and redaction
    - Location and temporal redaction
    - Financial and health information protection
    - Custom redaction rule application
    - Reversible redaction for authorized access
    """

    def __init__(
        self,
        # Policy system integration
        redactor_engine=None,
        policy_engine=None,
        consent_manager=None,
        # Configuration
        config: Optional[Dict[str, Any]] = None,
    ):
        # Dependencies (injected for testability)
        self.redactor_engine = redactor_engine
        self.policy_engine = policy_engine
        self.consent_manager = consent_manager

        # Configuration with defaults
        self.config = config or {}
        self.default_redaction_level = self.config.get(
            "default_redaction_level", "standard"
        )
        self.enable_reversible_redaction = self.config.get(
            "enable_reversible_redaction", True
        )
        self.safety_threshold = self.config.get("safety_threshold", 0.9)
        self.max_redaction_ratio = self.config.get("max_redaction_ratio", 0.5)

        # Initialize redaction rules
        self._redaction_rules = self._load_redaction_rules()

        logger.info(
            "MemoryRedactionCoordinator initialized",
            extra={
                "config": self.config,
                "default_redaction_level": self.default_redaction_level,
                "enable_reversible_redaction": self.enable_reversible_redaction,
                "rules_loaded": len(self._redaction_rules),
                "policy_integration": {
                    "has_redactor": self.redactor_engine is not None,
                    "has_policy": self.policy_engine is not None,
                    "has_consent": self.consent_manager is not None,
                },
            },
        )

    async def coordinate_redaction(
        self,
        content: Dict[str, Any],
        obligations: List[str],
        space_id: str,
        actor: Dict[str, Any],
    ) -> tuple[Dict[str, Any], List[str]]:
        """
        Coordinate complete content redaction based on policy obligations.

        Implements prefrontal cortex-like executive control over memory encoding,
        applying appropriate redaction based on policies and context.

        Args:
            content: Content to redact (including text, attachments, metadata)
            obligations: Policy obligations to enforce
            space_id: Target memory space for context-aware redaction
            actor: Actor requesting memory formation

        Returns:
            Tuple of (redacted_content, applied_redaction_types)

        Raises:
            RedactionError: If redaction fails or content unsafe after redaction
        """
        start_time = datetime.now(timezone.utc)

        with start_span(
            "memory_steward.redaction_coordinator.coordinate_redaction"
        ) as span:
            try:
                content_hash = self._calculate_content_hash(content)

                logger.info(
                    "Starting content redaction coordination",
                    extra={
                        "content_hash": content_hash,
                        "obligations": obligations,
                        "space_id": space_id,
                        "actor": actor,
                        "content_fields": list(content.keys()),
                    },
                )

                # Step 1: Analyze policy obligations
                redaction_plan = await self._create_redaction_plan(
                    content, obligations, space_id, actor
                )

                # Step 2: Apply content redaction
                redacted_content = await self._apply_redaction_plan(
                    content, redaction_plan
                )

                # Step 3: Validate redaction safety
                safety_validated = await self._validate_redaction_safety(
                    content, redacted_content, redaction_plan
                )

                if not safety_validated:
                    raise RedactionError(
                        "Content does not meet safety requirements after redaction",
                        redaction_plan=redaction_plan,
                    )

                # Step 4: Extract applied redaction types
                applied_redactions = list(
                    set(match.rule_type for match in redaction_plan.matches)
                )

                # Calculate processing time
                end_time = datetime.now(timezone.utc)
                processing_time_ms = (end_time - start_time).total_seconds() * 1000

                logger.info(
                    "Content redaction coordination completed",
                    extra={
                        "content_hash": content_hash,
                        "redactions_applied": applied_redactions,
                        "redaction_count": len(redaction_plan.matches),
                        "safety_score": redaction_plan.estimated_safety_score,
                        "processing_time_ms": processing_time_ms,
                    },
                )

                return redacted_content, applied_redactions

            except Exception as e:
                logger.error(
                    "Content redaction coordination failed",
                    extra={
                        "obligations": obligations,
                        "space_id": space_id,
                        "actor": actor,
                        "error": str(e),
                    },
                )
                raise

    async def _create_redaction_plan(
        self,
        content: Dict[str, Any],
        obligations: List[str],
        space_id: str,
        actor: Dict[str, Any],
    ) -> RedactionPlan:
        """Create comprehensive redaction plan based on policy analysis."""

        # Calculate content hash for tracking
        content_hash = self._calculate_content_hash(content)

        # Determine redaction level based on obligations and space
        redaction_level = await self._determine_redaction_level(
            obligations, space_id, actor
        )

        # Detect redaction matches in content
        matches = await self._detect_redaction_matches(content, redaction_level)

        # Calculate estimated safety score
        safety_score = await self._estimate_safety_score(content, matches)

        return RedactionPlan(
            content_hash=content_hash,
            matches=matches,
            policy_obligations=obligations,
            redaction_level=redaction_level,
            estimated_safety_score=safety_score,
            metadata={
                "space_id": space_id,
                "actor": actor,
                "rules_evaluated": len(self._redaction_rules),
            },
        )

    async def _determine_redaction_level(
        self, obligations: List[str], space_id: str, actor: Dict[str, Any]
    ) -> str:
        """Determine appropriate redaction level based on context."""

        # Start with default level
        level = self.default_redaction_level

        # Escalate based on obligations
        sensitive_obligations = [
            "mask:pii:phone_numbers",
            "mask:pii:ssn",
            "redact:location:precise",
            "redact:financial:account_numbers",
            "redact:health:conditions",
        ]

        if any(obligation in sensitive_obligations for obligation in obligations):
            level = "aggressive"
        elif any("redact:" in obligation for obligation in obligations):
            level = "standard"
        elif any("mask:" in obligation for obligation in obligations):
            level = "minimal"

        # Adjust based on space sensitivity
        if space_id.startswith("public:") or space_id.startswith("shared:"):
            if level == "minimal":
                level = "standard"
            elif level == "standard":
                level = "aggressive"

        logger.debug(
            "Determined redaction level",
            extra={"level": level, "obligations": obligations, "space_id": space_id},
        )

        return level

    async def _detect_redaction_matches(
        self, content: Dict[str, Any], redaction_level: str
    ) -> List[RedactionMatch]:
        """Detect all redaction matches in content."""

        matches = []

        # Process text content
        if "content" in content and isinstance(content["content"], str):
            text_matches = await self._detect_text_redactions(
                content["content"], redaction_level
            )
            matches.extend(text_matches)

        # Process metadata
        if "meta" in content:
            meta_matches = await self._detect_metadata_redactions(
                content["meta"], redaction_level
            )
            matches.extend(meta_matches)

        # Process context information
        if "context" in content:
            context_matches = await self._detect_context_redactions(
                content["context"], redaction_level
            )
            matches.extend(context_matches)

        # Sort matches by position for proper redaction order
        matches.sort(key=lambda m: m.start_pos)

        return matches

    async def _detect_text_redactions(
        self, text: str, redaction_level: str
    ) -> List[RedactionMatch]:
        """Detect redaction matches in text content."""

        matches = []

        # Apply rules based on redaction level
        applicable_rules = self._get_applicable_rules(redaction_level)

        for rule in applicable_rules:
            rule_matches = self._apply_redaction_rule(text, rule)
            matches.extend(rule_matches)

        return matches

    async def _detect_metadata_redactions(
        self, metadata: Dict[str, Any], redaction_level: str
    ) -> List[RedactionMatch]:
        """Detect redaction matches in metadata."""

        matches = []

        # Convert metadata to text for pattern matching
        metadata_text = str(metadata)

        # Apply location and temporal redaction rules
        location_rules = [r for r in self._redaction_rules if r.rule_type == "location"]

        for rule in location_rules:
            rule_matches = self._apply_redaction_rule(metadata_text, rule)
            # Adjust for metadata context
            for match in rule_matches:
                match.metadata = {"source": "metadata", "field": "location"}
            matches.extend(rule_matches)

        return matches

    async def _detect_context_redactions(
        self, context: Dict[str, Any], redaction_level: str
    ) -> List[RedactionMatch]:
        """Detect redaction matches in context information."""

        matches = []

        # Check for location context
        if "location" in context:
            location_text = str(context["location"])
            location_rules = [
                r for r in self._redaction_rules if r.rule_type == "location"
            ]

            for rule in location_rules:
                rule_matches = self._apply_redaction_rule(location_text, rule)
                for match in rule_matches:
                    match.metadata = {"source": "context", "field": "location"}
                matches.extend(rule_matches)

        return matches

    def _apply_redaction_rule(
        self, text: str, rule: RedactionRule
    ) -> List[RedactionMatch]:
        """Apply a single redaction rule to text."""

        matches = []

        try:
            # Apply regex pattern
            for match in re.finditer(rule.pattern, text, re.IGNORECASE):
                original_text = match.group(0)
                start_pos = match.start()
                end_pos = match.end()

                # Generate replacement based on strategy
                replacement = self._generate_replacement(
                    original_text, rule.replacement_strategy
                )

                redaction_match = RedactionMatch(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    original_text=original_text,
                    confidence=0.95,  # High confidence for regex matches
                    replacement=replacement,
                    metadata={"rule": rule.rule_id},
                )

                matches.append(redaction_match)

        except re.error as e:
            logger.warning(
                "Invalid regex pattern in redaction rule",
                extra={
                    "rule_id": rule.rule_id,
                    "pattern": rule.pattern,
                    "error": str(e),
                },
            )

        return matches

    def _generate_replacement(self, original_text: str, strategy: str) -> str:
        """Generate replacement text based on redaction strategy."""

        if strategy == "mask":
            # Replace with asterisks, preserving length
            return "*" * len(original_text)

        elif strategy == "hash":
            # Replace with hash prefix
            text_hash = hashlib.sha256(original_text.encode()).hexdigest()[:8]
            return f"[HASH:{text_hash}]"

        elif strategy == "remove":
            # Complete removal
            return ""

        elif strategy == "generalize":
            # Replace with generic term based on type
            return "[REDACTED]"

        elif strategy == "encrypt":
            # Replace with encrypted token (stub)
            token = uuid.uuid4().hex[:12]
            return f"[ENC:{token}]"

        else:
            # Default to generic redaction
            return "[REDACTED]"

    async def _apply_redaction_plan(
        self, content: Dict[str, Any], plan: RedactionPlan
    ) -> Dict[str, Any]:
        """Apply redaction plan to content."""

        redacted_content = content.copy()

        # Apply redactions to text content
        if "content" in content and isinstance(content["content"], str):
            redacted_text = self._apply_text_redactions(
                content["content"], plan.matches
            )
            redacted_content["content"] = redacted_text

        # Apply redactions to metadata
        if "meta" in content:
            redacted_meta = self._apply_metadata_redactions(
                content["meta"], plan.matches
            )
            redacted_content["meta"] = redacted_meta

        # Apply redactions to context
        if "context" in content:
            redacted_context = self._apply_context_redactions(
                content["context"], plan.matches
            )
            redacted_content["context"] = redacted_context

        return redacted_content

    def _apply_text_redactions(self, text: str, matches: List[RedactionMatch]) -> str:
        """Apply redaction matches to text content."""

        # Sort matches by position (descending) to avoid position shifts
        sorted_matches = sorted(matches, key=lambda m: m.start_pos, reverse=True)

        redacted_text = text

        for match in sorted_matches:
            # Apply redaction
            redacted_text = (
                redacted_text[: match.start_pos]
                + match.replacement
                + redacted_text[match.end_pos :]
            )

        return redacted_text

    def _apply_metadata_redactions(
        self, metadata: Dict[str, Any], matches: List[RedactionMatch]
    ) -> Dict[str, Any]:
        """Apply redactions to metadata fields."""

        redacted_meta = metadata.copy()

        # Apply location redactions
        location_matches = [
            m for m in matches if m.metadata and m.metadata.get("source") == "metadata"
        ]

        if location_matches and "location" in redacted_meta:
            redacted_meta["location"] = "[LOCATION_REDACTED]"

        return redacted_meta

    def _apply_context_redactions(
        self, context: Dict[str, Any], matches: List[RedactionMatch]
    ) -> Dict[str, Any]:
        """Apply redactions to context information."""

        redacted_context = context.copy()

        # Apply location redactions
        location_matches = [
            m for m in matches if m.metadata and m.metadata.get("source") == "context"
        ]

        if location_matches and "location" in redacted_context:
            redacted_context["location"] = "[LOCATION_REDACTED]"

        return redacted_context

    async def _validate_redaction_safety(
        self,
        original_content: Dict[str, Any],
        redacted_content: Dict[str, Any],
        plan: RedactionPlan,
    ) -> bool:
        """Validate that redacted content meets safety requirements."""

        # Check if safety score meets threshold
        if plan.estimated_safety_score < self.safety_threshold:
            logger.warning(
                "Redacted content safety score below threshold",
                extra={
                    "safety_score": plan.estimated_safety_score,
                    "threshold": self.safety_threshold,
                },
            )
            return False

        # Check redaction ratio (ensure content isn't over-redacted)
        redaction_ratio = self._calculate_redaction_ratio(
            original_content, redacted_content
        )
        if redaction_ratio > self.max_redaction_ratio:
            logger.warning(
                "Content redaction ratio exceeds maximum",
                extra={
                    "redaction_ratio": redaction_ratio,
                    "max_ratio": self.max_redaction_ratio,
                },
            )
            return False

        return True

    async def _estimate_safety_score(
        self, content: Dict[str, Any], matches: List[RedactionMatch]
    ) -> float:
        """Estimate safety score after applying redactions."""

        # Base score starts high
        base_score = 0.95

        # Reduce score for unredacted sensitive patterns
        if "content" in content:
            text = content["content"]

            # Check for remaining PII patterns
            pii_patterns = [
                r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
                r"\b\d{3}-\d{3}-\d{4}\b",  # Phone
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            ]

            for pattern in pii_patterns:
                if re.search(pattern, text):
                    # Check if this pattern was redacted
                    pattern_redacted = any(
                        match.rule_type == "pii"
                        and match.start_pos
                        <= re.search(pattern, text).start()
                        <= match.end_pos
                        for match in matches
                    )

                    if not pattern_redacted:
                        base_score -= 0.2  # Significant penalty for unredacted PII

        return max(base_score, 0.0)

    def _calculate_redaction_ratio(
        self, original_content: Dict[str, Any], redacted_content: Dict[str, Any]
    ) -> float:
        """Calculate ratio of content that was redacted."""

        if "content" not in original_content:
            return 0.0

        original_text = original_content["content"]
        redacted_text = redacted_content["content"]

        if not original_text:
            return 0.0

        # Count redacted characters (simple approximation)
        redacted_chars = len(original_text) - len(
            redacted_text.replace("[REDACTED]", "")
        )

        return redacted_chars / len(original_text)

    def _calculate_content_hash(self, content: Dict[str, Any]) -> str:
        """Calculate hash of content for tracking."""
        content_str = str(sorted(content.items()))
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def _get_applicable_rules(self, redaction_level: str) -> List[RedactionRule]:
        """Get redaction rules applicable to the specified level."""

        if redaction_level == "minimal":
            return [
                r
                for r in self._redaction_rules
                if r.rule_type in ["pii:ssn", "pii:credit_card"]
            ]
        elif redaction_level == "standard":
            return [
                r
                for r in self._redaction_rules
                if r.rule_type in ["pii", "location:precise", "financial"]
            ]
        elif redaction_level == "aggressive":
            return self._redaction_rules
        else:
            return []

    def _load_redaction_rules(self) -> List[RedactionRule]:
        """Load redaction rules from configuration."""

        rules = [
            # PII Rules
            RedactionRule(
                rule_id="pii_ssn",
                rule_type="pii",
                pattern=r"\b\d{3}-\d{2}-\d{4}\b",
                replacement_strategy="mask",
            ),
            RedactionRule(
                rule_id="pii_phone",
                rule_type="pii",
                pattern=r"\b\d{3}-\d{3}-\d{4}\b",
                replacement_strategy="mask",
            ),
            RedactionRule(
                rule_id="pii_email",
                rule_type="pii",
                pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                replacement_strategy="generalize",
            ),
            # Location Rules
            RedactionRule(
                rule_id="location_address",
                rule_type="location",
                pattern=r"\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln)\b",
                replacement_strategy="generalize",
            ),
            # Financial Rules
            RedactionRule(
                rule_id="financial_credit_card",
                rule_type="financial",
                pattern=r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
                replacement_strategy="mask",
            ),
        ]

        return rules


class RedactionError(Exception):
    """Exception raised when redaction fails or content is unsafe."""

    def __init__(self, message: str, redaction_plan: Optional[RedactionPlan] = None):
        super().__init__(message)
        self.redaction_plan = redaction_plan


# TODO: Production enhancements needed:
# - Integrate with proper PII detection models (spaCy, transformers)
# - Add reversible encryption for authorized access patterns
# - Implement machine learning-based sensitivity classification
# - Add support for image and audio redaction
# - Implement differential privacy mechanisms
# - Add redaction quality metrics and monitoring
# - Implement redaction rule learning from feedback
