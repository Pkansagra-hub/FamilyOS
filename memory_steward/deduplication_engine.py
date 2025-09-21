"""
Memory Deduplication Engine - CA3 Pattern Completion for Memory Consolidation
=============================================================================

This module implements content-based deduplication for memory formation,
using CA3-like pattern completion to identify similar memories and merge
them intelligently. It prevents memory fragmentation while preserving
important contextual variations and temporal progressions.

**Neuroscience Inspiration:**
The CA3 region of the hippocampus performs pattern completion, using
recurrent connections to retrieve complete memories from partial cues.
This system also enables memory consolidation by linking related experiences
and building coherent memory networks. Our deduplication engine mirrors
these functions by identifying similar content and deciding whether to
merge, link, or maintain separate memories.

**Research Backing:**
- Marr (1971): Simple memory: a theory for archicortex
- Treves & Rolls (1994): Computational analysis of the role of the hippocampus
- Hasselmo et al. (1995): Dynamics of learning and recall at excitatory recurrent synapses
- Rolls (2013): The mechanisms for pattern completion and pattern separation in the hippocampus
- Yassa & Stark (2011): Pattern separation in the hippocampus

The implementation integrates with the existing hippocampus system for
similarity detection while adding intelligent merging strategies and
temporal coherence analysis.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from hippocampus.api import HippocampusAPI
from hippocampus.types import CompletionCandidate, HippocampalEncoding
from observability.logging import get_json_logger
from observability.trace import start_span

logger = get_json_logger(__name__)


@dataclass
class SimilarityMatch:
    """
    A detected similarity match with scoring breakdown.
    """

    memory_id: str
    event_id: str
    similarity_score: float  # Combined similarity score (0-1)
    similarity_breakdown: Dict[str, float]  # Individual similarity components
    temporal_distance_hours: float
    content_overlap_ratio: float
    entity_overlap_ratio: float
    merge_recommendation: str  # "merge", "link", "separate"
    confidence: float  # Confidence in recommendation
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DeduplicationStrategy:
    """
    Strategy for handling similar memories.
    """

    strategy_type: (
        str  # "merge_content", "append_context", "temporal_update", "link_only"
    )
    merge_threshold: float  # Similarity threshold for merging
    temporal_window_hours: float  # Time window for considering duplicates
    preserve_variations: bool  # Whether to preserve content variations
    max_merge_candidates: int  # Maximum memories to consider for merging
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DeduplicationResult:
    """
    Result of deduplication analysis and execution.
    """

    strategy: str
    merged_with: List[str]  # Memory IDs that were merged
    linked_to: List[str]  # Memory IDs that were linked
    similarity_score: float  # Highest similarity score found
    temporal_coherence: float  # Temporal coherence score
    content_preservation_ratio: float  # Ratio of original content preserved
    processing_time_ms: float
    metadata: Optional[Dict[str, Any]] = None


class MemoryDeduplicationEngine:
    """
    Implements CA3-like pattern completion for memory deduplication.

    Uses the existing hippocampus system for similarity detection and
    implements intelligent merging strategies to prevent memory fragmentation
    while preserving important variations and temporal progressions.

    **Key Functions:**
    - Similarity detection using hippocampal encoding
    - Intelligent merge vs. link decisions
    - Temporal coherence analysis
    - Content preservation strategies
    - Memory network building
    """

    def __init__(
        self,
        # Dependencies
        hippocampus_api: Optional[HippocampusAPI] = None,
        memory_store=None,
        # Configuration
        config: Optional[Dict[str, Any]] = None,
    ):
        # Dependencies (injected for testability)
        self.hippocampus_api = hippocampus_api or HippocampusAPI()
        self.memory_store = memory_store

        # Configuration with defaults
        self.config = config or {}
        self.similarity_threshold = self.config.get("similarity_threshold", 0.8)
        self.merge_threshold = self.config.get("merge_threshold", 0.9)
        self.temporal_window_hours = self.config.get(
            "temporal_window_hours", 168
        )  # 1 week
        self.max_candidates = self.config.get("max_candidates", 10)
        self.enable_semantic_similarity = self.config.get(
            "enable_semantic_similarity", True
        )
        self.preserve_temporal_variations = self.config.get(
            "preserve_temporal_variations", True
        )

        # Deduplication strategies
        self._strategies = self._load_deduplication_strategies()

        logger.info(
            "MemoryDeduplicationEngine initialized",
            extra={
                "config": self.config,
                "similarity_threshold": self.similarity_threshold,
                "merge_threshold": self.merge_threshold,
                "temporal_window_hours": self.temporal_window_hours,
                "strategies_loaded": len(self._strategies),
                "dependencies": {
                    "has_hippocampus": self.hippocampus_api is not None,
                    "has_memory_store": self.memory_store is not None,
                },
            },
        )

    async def check_and_merge(
        self, encoding: HippocampalEncoding, space_id: str
    ) -> Dict[str, Any]:
        """
        Check for similar memories and apply intelligent deduplication.

        Implements CA3-like pattern completion to identify similar memories
        and determine the best strategy for consolidation.

        Args:
            encoding: New hippocampal encoding to check for duplicates
            space_id: Memory space to search within

        Returns:
            DeduplicationResult with applied strategy and merge information
        """
        start_time = datetime.now(timezone.utc)

        with start_span("memory_steward.deduplication_engine.check_and_merge") as span:
            span.set_attribute("space_id", space_id)
            span.set_attribute("event_id", encoding.event_id)
            span.set_attribute("novelty", encoding.novelty)

            try:
                logger.info(
                    "Starting memory deduplication analysis",
                    extra={
                        "event_id": encoding.event_id,
                        "space_id": space_id,
                        "novelty": encoding.novelty,
                        "near_duplicates": len(encoding.near_duplicates),
                    },
                )

                # Step 1: Find similar memories using hippocampal recall
                similarity_matches = await self._find_similar_memories(
                    encoding, space_id
                )

                # Step 2: Analyze temporal coherence
                temporal_analysis = await self._analyze_temporal_coherence(
                    encoding, similarity_matches
                )

                # Step 3: Determine deduplication strategy
                strategy = await self._determine_deduplication_strategy(
                    encoding, similarity_matches, temporal_analysis
                )

                # Step 4: Execute deduplication strategy
                result = await self._execute_deduplication_strategy(
                    encoding, similarity_matches, strategy
                )

                # Calculate processing time
                end_time = datetime.now(timezone.utc)
                processing_time_ms = (end_time - start_time).total_seconds() * 1000
                result.processing_time_ms = processing_time_ms

                span.set_attribute("strategy", result.strategy)
                span.set_attribute("merged_count", len(result.merged_with))
                span.set_attribute("linked_count", len(result.linked_to))
                span.set_attribute("similarity_score", result.similarity_score)

                logger.info(
                    "Memory deduplication completed",
                    extra={
                        "event_id": encoding.event_id,
                        "strategy": result.strategy,
                        "merged_with": result.merged_with,
                        "linked_to": result.linked_to,
                        "similarity_score": result.similarity_score,
                        "processing_time_ms": processing_time_ms,
                    },
                )

                # Convert to dictionary format expected by orchestrator
                return {
                    "strategy": result.strategy,
                    "merged_with": result.merged_with,
                    "linked_to": result.linked_to,
                    "similarity_score": result.similarity_score,
                    "temporal_coherence": result.temporal_coherence,
                    "content_preservation_ratio": result.content_preservation_ratio,
                    "processing_time_ms": result.processing_time_ms,
                    "metadata": result.metadata,
                }

            except Exception as e:
                logger.error(
                    "Memory deduplication failed",
                    extra={
                        "event_id": encoding.event_id,
                        "space_id": space_id,
                        "error": str(e),
                    },
                )
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise

    async def _find_similar_memories(
        self, encoding: HippocampalEncoding, space_id: str
    ) -> List[SimilarityMatch]:
        """Find similar memories using hippocampal pattern completion."""

        similarity_matches = []

        # Extract content for similarity search
        content_text = encoding.metadata.get("content", "") if encoding.metadata else ""

        if not content_text:
            logger.debug("No content available for similarity search")
            return similarity_matches

        try:
            # Use hippocampus API for pattern completion
            candidates = await self.hippocampus_api.recall_by_cue(
                space_id=space_id,
                cue_text=content_text,
                k=self.max_candidates,
                use_vectors=self.enable_semantic_similarity,
            )

            # Convert candidates to similarity matches
            for candidate in candidates:
                if candidate.score >= self.similarity_threshold:
                    # Calculate additional similarity metrics
                    similarity_breakdown = await self._calculate_similarity_breakdown(
                        encoding, candidate
                    )

                    # Calculate temporal distance
                    temporal_distance = await self._calculate_temporal_distance(
                        encoding, candidate
                    )

                    # Generate merge recommendation
                    merge_recommendation, confidence = (
                        await self._generate_merge_recommendation(
                            encoding, candidate, similarity_breakdown, temporal_distance
                        )
                    )

                    similarity_match = SimilarityMatch(
                        memory_id=candidate.event_id,  # Using event_id as memory_id for now
                        event_id=candidate.event_id,
                        similarity_score=candidate.score,
                        similarity_breakdown=similarity_breakdown,
                        temporal_distance_hours=temporal_distance,
                        content_overlap_ratio=similarity_breakdown.get(
                            "content_overlap", 0.0
                        ),
                        entity_overlap_ratio=similarity_breakdown.get(
                            "entity_overlap", 0.0
                        ),
                        merge_recommendation=merge_recommendation,
                        confidence=confidence,
                        metadata=candidate.metadata,
                    )

                    similarity_matches.append(similarity_match)

            logger.debug(
                "Found similar memories",
                extra={
                    "candidates_found": len(candidates),
                    "similarity_matches": len(similarity_matches),
                    "threshold": self.similarity_threshold,
                },
            )

        except Exception as e:
            logger.warning(
                "Similarity search failed",
                extra={"error": str(e), "space_id": space_id},
            )

        return similarity_matches

    async def _calculate_similarity_breakdown(
        self, encoding: HippocampalEncoding, candidate: CompletionCandidate
    ) -> Dict[str, float]:
        """Calculate detailed similarity breakdown."""

        breakdown = {
            "overall": candidate.score,
            "content_overlap": 0.0,
            "entity_overlap": 0.0,
            "temporal_proximity": 0.0,
            "structural_similarity": 0.0,
        }

        # Content overlap (simple token-based for now)
        if encoding.metadata and candidate.metadata:
            encoding_content = encoding.metadata.get("content", "")
            candidate_content = candidate.metadata.get("content", "")

            if encoding_content and candidate_content:
                encoding_tokens = set(encoding_content.lower().split())
                candidate_tokens = set(candidate_content.lower().split())

                if encoding_tokens or candidate_tokens:
                    overlap = len(encoding_tokens & candidate_tokens)
                    total = len(encoding_tokens | candidate_tokens)
                    breakdown["content_overlap"] = overlap / total if total > 0 else 0.0

        # Entity overlap (stub - would use proper NER in production)
        breakdown["entity_overlap"] = (
            breakdown["content_overlap"] * 0.8
        )  # Approximation

        # Temporal proximity
        time_diff_hours = abs(
            (encoding.ts - datetime.now(timezone.utc)).total_seconds() / 3600
        )
        breakdown["temporal_proximity"] = max(
            0.0, 1.0 - (time_diff_hours / 168)
        )  # 1 week decay

        # Structural similarity (based on hippocampal encoding)
        if hasattr(encoding, "simhash_hex") and hasattr(candidate, "simhash_hex"):
            # Calculate Hamming distance for structural similarity
            breakdown["structural_similarity"] = (
                candidate.score
            )  # Use overall score as proxy

        return breakdown

    async def _calculate_temporal_distance(
        self, encoding: HippocampalEncoding, candidate: CompletionCandidate
    ) -> float:
        """Calculate temporal distance between memories in hours."""

        # For now, use a default temporal distance
        # In production, this would retrieve actual timestamps from storage
        default_distance = 24.0  # 24 hours default

        if encoding.metadata and candidate.metadata:
            # Try to extract timestamps from metadata
            encoding_time = encoding.ts
            candidate_time_str = candidate.metadata.get("timestamp")

            if candidate_time_str:
                try:
                    candidate_time = datetime.fromisoformat(
                        candidate_time_str.replace("Z", "+00:00")
                    )
                    time_diff = abs(
                        (encoding_time - candidate_time).total_seconds() / 3600
                    )
                    return time_diff
                except (ValueError, TypeError):
                    pass

        return default_distance

    async def _generate_merge_recommendation(
        self,
        encoding: HippocampalEncoding,
        candidate: CompletionCandidate,
        similarity_breakdown: Dict[str, float],
        temporal_distance: float,
    ) -> Tuple[str, float]:
        """Generate merge recommendation with confidence."""

        # High similarity and recent temporal proximity -> merge
        if (
            similarity_breakdown["overall"] >= self.merge_threshold
            and temporal_distance <= 24.0
        ):  # Within 24 hours
            return "merge", 0.9

        # High content overlap but distant in time -> link
        elif (
            similarity_breakdown["content_overlap"] >= 0.8
            and temporal_distance <= self.temporal_window_hours
        ):
            return "link", 0.7

        # Moderate similarity -> append context
        elif similarity_breakdown["overall"] >= 0.7:
            return "append_context", 0.6

        # Low similarity -> keep separate
        else:
            return "separate", 0.8

    async def _analyze_temporal_coherence(
        self, encoding: HippocampalEncoding, similarity_matches: List[SimilarityMatch]
    ) -> Dict[str, Any]:
        """Analyze temporal coherence patterns."""

        if not similarity_matches:
            return {"coherence_score": 1.0, "temporal_clusters": []}

        # Group matches by temporal proximity
        temporal_clusters = []
        current_cluster = []

        sorted_matches = sorted(
            similarity_matches, key=lambda m: m.temporal_distance_hours
        )

        for match in sorted_matches:
            if (
                not current_cluster
                or match.temporal_distance_hours
                - current_cluster[-1].temporal_distance_hours
                <= 12.0
            ):
                current_cluster.append(match)
            else:
                if current_cluster:
                    temporal_clusters.append(current_cluster)
                current_cluster = [match]

        if current_cluster:
            temporal_clusters.append(current_cluster)

        # Calculate coherence score
        coherence_score = 1.0
        if len(temporal_clusters) > 1:
            # Penalize for temporal fragmentation
            coherence_score -= 0.1 * (len(temporal_clusters) - 1)
            coherence_score = max(0.0, coherence_score)

        return {
            "coherence_score": coherence_score,
            "temporal_clusters": temporal_clusters,
            "cluster_count": len(temporal_clusters),
        }

    async def _determine_deduplication_strategy(
        self,
        encoding: HippocampalEncoding,
        similarity_matches: List[SimilarityMatch],
        temporal_analysis: Dict[str, Any],
    ) -> DeduplicationStrategy:
        """Determine the best deduplication strategy."""

        if not similarity_matches:
            return self._strategies["no_duplicates"]

        # Find highest similarity match
        best_match = max(similarity_matches, key=lambda m: m.similarity_score)

        # Strategy selection based on similarity and recommendations
        if (
            best_match.merge_recommendation == "merge"
            and best_match.similarity_score >= self.merge_threshold
        ):
            return self._strategies["high_similarity_merge"]

        elif best_match.merge_recommendation == "link":
            return self._strategies["moderate_similarity_link"]

        elif best_match.merge_recommendation == "append_context":
            return self._strategies["context_append"]

        else:
            return self._strategies["low_similarity_separate"]

    async def _execute_deduplication_strategy(
        self,
        encoding: HippocampalEncoding,
        similarity_matches: List[SimilarityMatch],
        strategy: DeduplicationStrategy,
    ) -> DeduplicationResult:
        """Execute the determined deduplication strategy."""

        result = DeduplicationResult(
            strategy=strategy.strategy_type,
            merged_with=[],
            linked_to=[],
            similarity_score=0.0,
            temporal_coherence=1.0,
            content_preservation_ratio=1.0,
            processing_time_ms=0.0,
        )

        if not similarity_matches:
            return result

        # Set similarity score from best match
        best_match = max(similarity_matches, key=lambda m: m.similarity_score)
        result.similarity_score = best_match.similarity_score

        # Execute strategy
        if strategy.strategy_type == "high_similarity_merge":
            # Merge with most similar memory
            candidates_to_merge = [
                m
                for m in similarity_matches
                if m.similarity_score >= strategy.merge_threshold
            ][: strategy.max_merge_candidates]
            result.merged_with = [m.memory_id for m in candidates_to_merge]
            result.content_preservation_ratio = 0.9  # High preservation in merge

        elif strategy.strategy_type == "moderate_similarity_link":
            # Link to similar memories without merging
            candidates_to_link = similarity_matches[: strategy.max_merge_candidates]
            result.linked_to = [m.memory_id for m in candidates_to_link]
            result.content_preservation_ratio = 1.0  # Full preservation in linking

        elif strategy.strategy_type == "context_append":
            # Append context to existing memory
            primary_candidate = similarity_matches[0]
            result.merged_with = [primary_candidate.memory_id]
            result.content_preservation_ratio = (
                0.95  # High preservation with context append
            )

        # Calculate temporal coherence
        if similarity_matches:
            temporal_distances = [m.temporal_distance_hours for m in similarity_matches]
            avg_distance = sum(temporal_distances) / len(temporal_distances)
            result.temporal_coherence = max(
                0.0, 1.0 - (avg_distance / self.temporal_window_hours)
            )

        return result

    def _load_deduplication_strategies(self) -> Dict[str, DeduplicationStrategy]:
        """Load deduplication strategies."""

        strategies = {
            "no_duplicates": DeduplicationStrategy(
                strategy_type="no_duplicates",
                merge_threshold=0.0,
                temporal_window_hours=0.0,
                preserve_variations=True,
                max_merge_candidates=0,
            ),
            "high_similarity_merge": DeduplicationStrategy(
                strategy_type="high_similarity_merge",
                merge_threshold=self.merge_threshold,
                temporal_window_hours=24.0,  # 24 hours for high similarity merge
                preserve_variations=False,
                max_merge_candidates=1,
            ),
            "moderate_similarity_link": DeduplicationStrategy(
                strategy_type="moderate_similarity_link",
                merge_threshold=0.7,
                temporal_window_hours=self.temporal_window_hours,
                preserve_variations=True,
                max_merge_candidates=3,
            ),
            "context_append": DeduplicationStrategy(
                strategy_type="context_append",
                merge_threshold=0.8,
                temporal_window_hours=72.0,  # 3 days for context append
                preserve_variations=True,
                max_merge_candidates=1,
            ),
            "low_similarity_separate": DeduplicationStrategy(
                strategy_type="low_similarity_separate",
                merge_threshold=0.0,
                temporal_window_hours=0.0,
                preserve_variations=True,
                max_merge_candidates=0,
            ),
        }

        return strategies

    async def get_deduplication_stats(self, space_id: str) -> Dict[str, Any]:
        """Get deduplication statistics for a memory space."""

        # This would query the memory store for actual statistics
        # For now, return placeholder stats
        return {
            "space_id": space_id,
            "total_memories": 0,
            "merged_memories": 0,
            "linked_memories": 0,
            "merge_ratio": 0.0,
            "avg_similarity_score": 0.0,
            "temporal_coherence": 1.0,
        }

    async def optimize_memory_network(self, space_id: str) -> Dict[str, Any]:
        """Optimize memory network by analyzing and improving connections."""

        # This would implement network optimization algorithms
        # For now, return placeholder optimization result
        return {
            "space_id": space_id,
            "optimizations_applied": [],
            "network_density_improvement": 0.0,
            "retrieval_efficiency_gain": 0.0,
        }


class DeduplicationError(Exception):
    """Exception raised when deduplication fails."""

    pass


# TODO: Production enhancements needed:
# - Integrate with proper semantic similarity models (sentence transformers)
# - Implement graph-based memory network analysis
# - Add learning from user feedback on merge decisions
# - Implement incremental deduplication for large memory spaces
# - Add support for multimedia content deduplication
# - Implement memory consolidation scheduling
# - Add deduplication quality metrics and monitoring
