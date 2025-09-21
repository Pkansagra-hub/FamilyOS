"""
Memory Space Resolver - Dentate Gyrus Pattern Separation for Memory Spaces
========================================================================

This module implements space resolution logic for memory formation, determining
the appropriate target memory space based on content analysis, actor permissions,
and contextual signals. It mirrors the pattern separation function of the
Dentate Gyrus in creating distinct memory representations.

**Neuroscience Inspiration:**
The Dentate Gyrus (DG) performs pattern separation, creating sparse and distinct
representations for similar inputs. This prevents interference and allows for
precise memory recall. Our space resolver performs analogous pattern separation
by analyzing content and context to determine the most appropriate memory space,
preventing cross-contamination between different memory domains.

**Research Backing:**
- Leutgeb et al. (2007): Pattern separation in the dentate gyrus and CA3
- Yassa & Stark (2011): Pattern separation in the hippocampus
- Schmidt et al. (2012): A role for the dentate gyrus in memory discrimination
- Neunuebel & Knierim (2014): CA3 retrieval sequences in CA1 regions

The implementation integrates with ABAC/RBAC policy systems to ensure that
memory formation respects access control boundaries and privacy requirements.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from observability.logging import get_json_logger
from observability.trace import start_span

logger = get_json_logger(__name__)


@dataclass
class SpaceCandidate:
    """
    A candidate memory space with confidence and reasoning.

    Represents the result of pattern separation analysis for space determination.
    """

    space_id: str
    confidence: float  # 0-1 confidence in this space selection
    reasoning: List[str]  # Human-readable reasons for this selection
    access_granted: bool  # Whether actor has access to this space
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SpaceResolutionResult:
    """
    Complete result of space resolution analysis.

    Contains the selected space and alternative candidates for audit trail.
    """

    selected_space: str
    confidence: float
    candidates: List[SpaceCandidate]
    resolution_strategy: (
        str  # "explicit", "content_analysis", "social_inference", "default"
    )
    processing_time_ms: float
    metadata: Optional[Dict[str, Any]] = None


class MemorySpaceResolver:
    """
    Resolves target memory space for incoming memory formation requests.

    Implements Dentate Gyrus-inspired pattern separation to determine the most
    appropriate memory space based on:
    - Explicit space hints in content
    - Social context and participant analysis
    - Content classification and entity recognition
    - Actor permissions and default spaces
    - Policy-based access control integration

    **Key Functions:**
    - Content analysis for space determination signals
    - Social context inference (shared vs. personal)
    - Permission validation via ABAC/RBAC integration
    - Fallback strategies for ambiguous cases
    """

    def __init__(
        self,
        # Policy system integration
        abac_engine=None,
        rbac_engine=None,
        space_policy=None,
        # Configuration
        config: Optional[Dict[str, Any]] = None,
    ):
        # Policy dependencies (injected for testability)
        self.abac_engine = abac_engine
        self.rbac_engine = rbac_engine
        self.space_policy = space_policy

        # Configuration with defaults
        self.config = config or {}
        self.min_confidence_threshold = self.config.get("min_confidence_threshold", 0.6)
        self.enable_social_inference = self.config.get("enable_social_inference", True)
        self.enable_content_analysis = self.config.get("enable_content_analysis", True)
        self.default_fallback_enabled = self.config.get(
            "default_fallback_enabled", True
        )

        # Space detection patterns
        self._explicit_space_patterns = [
            # Direct space references
            r"in\s+(?:space|room|channel)\s+([a-zA-Z0-9_:-]+)",
            r"save\s+(?:to|in)\s+([a-zA-Z0-9_:-]+)",
            r"(?:shared|family|household|work|team)[:]\s*([a-zA-Z0-9_-]+)",
            # Privacy indicators
            r"(?:private|personal|just\s+for\s+me)",
            r"(?:confidential|secret|don'?t\s+share)",
            r"(?:family\s+only|household\s+only)",
            # Work/professional context
            r"(?:work|office|meeting|project|client)",
            r"(?:business|professional|company)",
        ]

        # Social context patterns
        self._social_patterns = [
            # Family/household indicators
            r"(?:mom|dad|mother|father|parent|child|kids?|family)",
            r"(?:spouse|husband|wife|partner|significant\s+other)",
            r"(?:grandma|grandpa|grandmother|grandfather|aunt|uncle|cousin)",
            r"(?:brother|sister|sibling)",
            # Friends and social
            r"(?:friend|buddy|pal|bestie)",
            r"(?:group|party|gathering|celebration)",
            # Work colleagues
            r"(?:colleague|coworker|boss|manager|team|teammate)",
            r"(?:client|customer|vendor|supplier)",
        ]

        logger.info(
            "MemorySpaceResolver initialized",
            extra={
                "config": self.config,
                "min_confidence_threshold": self.min_confidence_threshold,
                "enable_social_inference": self.enable_social_inference,
                "enable_content_analysis": self.enable_content_analysis,
                "policy_integration": {
                    "has_abac": self.abac_engine is not None,
                    "has_rbac": self.rbac_engine is not None,
                    "has_space_policy": self.space_policy is not None,
                },
            },
        )

    async def resolve_space(
        self,
        actor: Dict[str, Any],
        content: str,
        context: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Resolve target memory space for content.

        Implements Dentate Gyrus pattern separation to determine the most
        appropriate memory space based on content analysis and context.

        Args:
            actor: Actor information with permissions
            content: Text content to analyze for space signals
            context: Additional context (location, activity, etc.)
            metadata: Optional metadata for analysis

        Returns:
            Selected space ID

        Raises:
            ValueError: If no valid space can be determined
            PermissionError: If actor lacks access to determined space
        """
        start_time = datetime.now(timezone.utc)

        with start_span("memory_steward.space_resolver.resolve_space") as span:
            span.set_attribute("actor.person_id", actor.get("person_id", "unknown"))
            span.set_attribute("content_length", len(content))
            span.set_attribute("has_context", bool(context))

            try:
                logger.info(
                    "Starting space resolution",
                    extra={
                        "actor": actor,
                        "content_length": len(content),
                        "context": context,
                        "metadata": metadata,
                    },
                )

                # Step 1: Explicit space detection
                explicit_candidates = await self._detect_explicit_spaces(
                    content, context
                )

                # Step 2: Content-based analysis
                content_candidates = []
                if self.enable_content_analysis and not explicit_candidates:
                    content_candidates = await self._analyze_content_for_spaces(
                        content, context, actor
                    )

                # Step 3: Social context inference
                social_candidates = []
                if self.enable_social_inference and not explicit_candidates:
                    social_candidates = await self._infer_social_spaces(
                        content, context, actor
                    )

                # Step 4: Combine all candidates
                all_candidates = (
                    explicit_candidates + content_candidates + social_candidates
                )

                # Step 5: Permission validation
                validated_candidates = await self._validate_permissions(
                    all_candidates, actor
                )

                # Step 6: Selection strategy
                result = await self._select_final_space(
                    validated_candidates, actor, content, context
                )

                # Calculate processing time
                end_time = datetime.now(timezone.utc)
                processing_time_ms = (end_time - start_time).total_seconds() * 1000
                result.processing_time_ms = processing_time_ms

                span.set_attribute("selected_space", result.selected_space)
                span.set_attribute("resolution_strategy", result.resolution_strategy)
                span.set_attribute("confidence", result.confidence)
                span.set_attribute("candidates_evaluated", len(result.candidates))

                logger.info(
                    "Space resolution completed",
                    extra={
                        "selected_space": result.selected_space,
                        "confidence": result.confidence,
                        "strategy": result.resolution_strategy,
                        "candidates_evaluated": len(result.candidates),
                        "processing_time_ms": processing_time_ms,
                    },
                )

                return result.selected_space

            except Exception as e:
                logger.error(
                    "Space resolution failed",
                    extra={
                        "actor": actor,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise

    async def validate_space_access(
        self, space_id: str, actor: Dict[str, Any], content: str
    ) -> str:
        """
        Validate that actor has access to specified space.

        Args:
            space_id: Space to validate access for
            actor: Actor requesting access
            content: Content being stored (for policy evaluation)

        Returns:
            Validated space ID

        Raises:
            PermissionError: If access is denied
        """
        with start_span("memory_steward.space_resolver.validate_space_access") as span:
            span.set_attribute("space_id", space_id)
            span.set_attribute("actor.person_id", actor.get("person_id", "unknown"))

            try:
                # Check RBAC permissions
                if self.rbac_engine:
                    rbac_permitted = await self._check_rbac_access(space_id, actor)
                    if not rbac_permitted:
                        raise PermissionError(f"RBAC denied access to space {space_id}")

                # Check ABAC permissions
                if self.abac_engine:
                    abac_permitted = await self._check_abac_access(
                        space_id, actor, content
                    )
                    if not abac_permitted:
                        raise PermissionError(f"ABAC denied access to space {space_id}")

                # Check space-specific policies
                if self.space_policy:
                    policy_permitted = await self._check_space_policy(
                        space_id, actor, content
                    )
                    if not policy_permitted:
                        raise PermissionError(
                            f"Space policy denied access to space {space_id}"
                        )

                logger.debug(
                    "Space access validated",
                    extra={"space_id": space_id, "actor": actor},
                )

                span.set_attribute("access_granted", True)
                return space_id

            except PermissionError:
                span.set_attribute("access_granted", False)
                raise
            except Exception as e:
                logger.error(
                    "Space access validation failed",
                    extra={"space_id": space_id, "actor": actor, "error": str(e)},
                )
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise

    async def _detect_explicit_spaces(
        self, content: str, context: Dict[str, Any]
    ) -> List[SpaceCandidate]:
        """Detect explicitly mentioned spaces in content."""
        candidates = []
        content_lower = content.lower()

        # Check for explicit space patterns
        for pattern in self._explicit_space_patterns:
            matches = re.finditer(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                if match.groups():
                    # Space ID mentioned explicitly
                    space_id = match.group(1).strip()
                    candidates.append(
                        SpaceCandidate(
                            space_id=space_id,
                            confidence=0.95,  # High confidence for explicit mentions
                            reasoning=[
                                f"Explicitly mentioned in content: '{match.group(0)}'"
                            ],
                            access_granted=True,  # Will be validated later
                        )
                    )
                else:
                    # Privacy/sharing indicator
                    if "private" in match.group(0) or "personal" in match.group(0):
                        candidates.append(
                            SpaceCandidate(
                                space_id="personal",
                                confidence=0.9,
                                reasoning=[f"Privacy indicator: '{match.group(0)}'"],
                                access_granted=True,
                            )
                        )
                    elif "family" in match.group(0) or "household" in match.group(0):
                        candidates.append(
                            SpaceCandidate(
                                space_id="shared:household",
                                confidence=0.85,
                                reasoning=[f"Family indicator: '{match.group(0)}'"],
                                access_granted=True,
                            )
                        )
                    elif "work" in match.group(0) or "business" in match.group(0):
                        candidates.append(
                            SpaceCandidate(
                                space_id="work:default",
                                confidence=0.8,
                                reasoning=[f"Work indicator: '{match.group(0)}'"],
                                access_granted=True,
                            )
                        )

        return candidates

    async def _analyze_content_for_spaces(
        self, content: str, context: Dict[str, Any], actor: Dict[str, Any]
    ) -> List[SpaceCandidate]:
        """Analyze content for space determination signals."""
        candidates = []
        content_lower = content.lower()

        # Entity-based space inference
        entities = self._extract_entities(content)

        # Time-based context
        time_context = context.get("temporal", {})
        location_context = context.get("location", "")

        # Score different space types based on content
        scores = {"personal": 0.0, "shared:household": 0.0, "work:default": 0.0}

        # Personal space indicators
        personal_indicators = ["i", "me", "my", "myself", "personal", "private"]
        personal_score = sum(1 for word in personal_indicators if word in content_lower)
        scores["personal"] += personal_score * 0.1

        # Family/household indicators
        family_score = sum(
            1
            for pattern in self._social_patterns[:4]
            for match in re.finditer(pattern, content_lower)
        )
        scores["shared:household"] += family_score * 0.2

        # Work indicators
        work_indicators = ["work", "office", "meeting", "project", "client", "business"]
        work_score = sum(1 for word in work_indicators if word in content_lower)
        scores["work:default"] += work_score * 0.15

        # Location context boost
        if location_context:
            if "home" in location_context.lower():
                scores["shared:household"] += 0.3
            elif (
                "office" in location_context.lower()
                or "work" in location_context.lower()
            ):
                scores["work:default"] += 0.3

        # Create candidates from scores
        for space_id, score in scores.items():
            if score > 0.2:  # Minimum threshold
                confidence = min(score, 0.8)  # Cap at 0.8 for content analysis
                reasoning = [f"Content analysis score: {score:.2f}"]

                if space_id == "personal" and personal_score > 0:
                    reasoning.append(f"Personal pronouns: {personal_score}")
                elif space_id == "shared:household" and family_score > 0:
                    reasoning.append(f"Family references: {family_score}")
                elif space_id == "work:default" and work_score > 0:
                    reasoning.append(f"Work references: {work_score}")

                candidates.append(
                    SpaceCandidate(
                        space_id=space_id,
                        confidence=confidence,
                        reasoning=reasoning,
                        access_granted=True,
                    )
                )

        return candidates

    async def _infer_social_spaces(
        self, content: str, context: Dict[str, Any], actor: Dict[str, Any]
    ) -> List[SpaceCandidate]:
        """Infer spaces based on social context."""
        candidates = []

        # Extract social signals
        social_entities = self._extract_social_entities(content)

        if social_entities:
            # Determine space based on social relationship types
            has_family = any(
                rel in ["family", "parent", "child", "spouse"]
                for rel in social_entities
            )
            has_friends = any(rel in ["friend", "social"] for rel in social_entities)
            has_work = any(rel in ["colleague", "work"] for rel in social_entities)

            if has_family:
                candidates.append(
                    SpaceCandidate(
                        space_id="shared:household",
                        confidence=0.75,
                        reasoning=[f"Family relationships detected: {social_entities}"],
                        access_granted=True,
                    )
                )

            if has_work:
                candidates.append(
                    SpaceCandidate(
                        space_id="work:default",
                        confidence=0.7,
                        reasoning=[f"Work relationships detected: {social_entities}"],
                        access_granted=True,
                    )
                )

            if has_friends and not has_family and not has_work:
                candidates.append(
                    SpaceCandidate(
                        space_id="social:friends",
                        confidence=0.65,
                        reasoning=[f"Friend relationships detected: {social_entities}"],
                        access_granted=True,
                    )
                )

        return candidates

    async def _validate_permissions(
        self, candidates: List[SpaceCandidate], actor: Dict[str, Any]
    ) -> List[SpaceCandidate]:
        """Validate actor permissions for candidate spaces."""
        validated = []

        for candidate in candidates:
            try:
                # Validate access (this will raise if denied)
                await self.validate_space_access(
                    candidate.space_id, actor, ""  # Empty content for permission check
                )
                candidate.access_granted = True
                validated.append(candidate)

            except PermissionError as e:
                logger.debug(
                    "Permission denied for candidate space",
                    extra={
                        "space_id": candidate.space_id,
                        "actor": actor,
                        "error": str(e),
                    },
                )
                candidate.access_granted = False
                candidate.reasoning.append(f"Access denied: {str(e)}")
                # Still include in candidates for audit trail
                validated.append(candidate)

        return validated

    async def _select_final_space(
        self,
        candidates: List[SpaceCandidate],
        actor: Dict[str, Any],
        content: str,
        context: Dict[str, Any],
    ) -> SpaceResolutionResult:
        """Select final space from validated candidates."""

        # Filter to only accessible candidates
        accessible = [c for c in candidates if c.access_granted]

        if accessible:
            # Select highest confidence accessible candidate
            best = max(accessible, key=lambda c: c.confidence)

            # Ensure minimum confidence threshold
            if best.confidence >= self.min_confidence_threshold:
                return SpaceResolutionResult(
                    selected_space=best.space_id,
                    confidence=best.confidence,
                    candidates=candidates,
                    resolution_strategy=(
                        "content_analysis" if candidates else "explicit"
                    ),
                )

        # Fallback to default space if enabled
        if self.default_fallback_enabled:
            default_space = self._get_default_space(actor)

            # Validate default space access
            try:
                await self.validate_space_access(default_space, actor, content)

                return SpaceResolutionResult(
                    selected_space=default_space,
                    confidence=0.5,  # Low confidence for fallback
                    candidates=candidates,
                    resolution_strategy="default_fallback",
                )

            except PermissionError:
                pass

        # No valid space found
        raise ValueError("No accessible memory space found for content")

    def _get_default_space(self, actor: Dict[str, Any]) -> str:
        """Get default memory space for actor."""
        # Use personal space as ultimate fallback
        person_id = actor.get("person_id", "unknown")
        return f"personal:{person_id}"

    def _extract_entities(self, content: str) -> List[str]:
        """Extract entities for space analysis (stub implementation)."""
        # TODO: Replace with proper NER system
        entities = []
        words = content.lower().split()

        # Simple entity detection
        for word in words:
            if word in ["mom", "dad", "family", "work", "office", "home"]:
                entities.append(word)

        return entities

    def _extract_social_entities(self, content: str) -> List[str]:
        """Extract social relationship entities."""
        relationships = []
        content_lower = content.lower()

        # Family relationships
        family_terms = [
            "mom",
            "dad",
            "mother",
            "father",
            "parent",
            "child",
            "kids",
            "spouse",
            "husband",
            "wife",
            "family",
            "grandma",
            "grandpa",
        ]
        if any(term in content_lower for term in family_terms):
            relationships.append("family")

        # Work relationships
        work_terms = ["colleague", "coworker", "boss", "manager", "client", "customer"]
        if any(term in content_lower for term in work_terms):
            relationships.append("work")

        # Friend relationships
        friend_terms = ["friend", "buddy", "pal"]
        if any(term in content_lower for term in friend_terms):
            relationships.append("friend")

        return relationships

    async def _check_rbac_access(self, space_id: str, actor: Dict[str, Any]) -> bool:
        """Check RBAC permissions for space access."""
        if not self.rbac_engine:
            return True  # No RBAC engine, allow access

        # TODO: Integrate with actual RBAC engine
        return True

    async def _check_abac_access(
        self, space_id: str, actor: Dict[str, Any], content: str
    ) -> bool:
        """Check ABAC permissions for space access."""
        if not self.abac_engine:
            return True  # No ABAC engine, allow access

        # TODO: Integrate with actual ABAC engine
        return True

    async def _check_space_policy(
        self, space_id: str, actor: Dict[str, Any], content: str
    ) -> bool:
        """Check space-specific policies."""
        if not self.space_policy:
            return True  # No space policy, allow access

        # TODO: Integrate with actual space policy engine
        return True


# TODO: Production enhancements needed:
# - Integrate with proper NER system for entity extraction
# - Add machine learning model for space classification
# - Implement caching for permission checks
# - Add support for custom space resolution rules
# - Implement space creation workflow for new spaces
# - Add confidence threshold tuning based on historical accuracy
# - Implement space recommendation system for ambiguous cases
