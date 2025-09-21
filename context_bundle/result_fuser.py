"""
Result Fusion Engine - Hippocampal CA1 Integration for Multi-Store Results
===========================================================================

This module implements intelligent result fusion across heterogeneous storage
systems, using Maximal Marginal Relevance (MMR) diversification, cross-store
deduplication, and sophisticated scoring strategies. It mirrors the CA1 region's
role in integrating pattern-completed outputs from CA3 with cortical inputs.

**Neuroscience Inspiration:**
The CA1 region of the hippocampus acts as a convergence zone that integrates
outputs from CA3 recurrent networks with direct cortical inputs, creating
coherent episodic representations. This fusion engine mirrors CA1's integration
function by combining diverse memory sources into unified, coherent context
bundles while maintaining quality and diversity.

**Research Backing:**
- Squire & Kandel (2009): CA1 as convergence zone for hippocampal-cortical integration
- Lisman & Grace (2005): The hippocampal-VTA loop: controlling the entry of information
- Hasselmo et al. (2002): Dynamics of learning and recall at excitatory recurrent synapses
- Carbonell & Goldstein (1998): Information retrieval using MMR

The implementation provides sophisticated result combination with diversity
optimization, cross-store deduplication, temporal weighting, and confidence
modeling for high-quality context assembly.
"""

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from observability.logging import get_json_logger
from observability.trace import start_span

logger = get_json_logger(__name__)


@dataclass
class FusionStrategy:
    """
    Strategy configuration for result fusion.
    """

    strategy_type: str  # "mmr_diversification", "temporal_weighted", "entity_focused"
    lambda_diversity: float = 0.3  # MMR diversity parameter
    temporal_weight: float = 0.7  # Temporal relevance weight
    entity_boost: float = 0.2  # Entity matching boost
    max_results: int = 20
    deduplication_threshold: float = 0.85
    confidence_threshold: float = 0.1


@dataclass
class FusedResult:
    """
    Individual result after fusion processing.
    """

    content_id: str
    content: str
    final_score: float
    confidence: float
    source_store: str
    original_score: float
    mmr_score: Optional[float] = None
    temporal_boost: Optional[float] = None
    diversity_penalty: Optional[float] = None
    deduplication_merged: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class FusionMetadata:
    """
    Metadata about the fusion process.
    """

    total_input_results: int
    final_result_count: int
    deduplication_removed: int
    mmr_iterations: int
    fusion_strategy: str
    processing_time_ms: float
    quality_scores: Dict[str, float]


class ResultFusionEngine:
    """
    Implements intelligent multi-store result fusion with CA1-inspired integration.

    Coordinates the fusion of results from heterogeneous storage systems using
    sophisticated algorithms for deduplication, diversification, and quality
    optimization to create coherent context bundles.

    **Key Functions:**
    - Cross-store result normalization and deduplication
    - Maximal Marginal Relevance (MMR) diversification
    - Temporal weighting and recency bias application
    - Confidence modeling and quality assessment
    - Entity-based relevance boosting
    """

    def __init__(
        self,
        # Configuration
        config: Optional[Dict[str, Any]] = None,
    ):
        # Configuration with defaults
        self.config = config or {}
        self.default_mmr_lambda = self.config.get("default_mmr_lambda", 0.3)
        self.similarity_threshold = self.config.get("similarity_threshold", 0.85)
        self.min_confidence = self.config.get("min_confidence", 0.1)
        self.temporal_decay_hours = self.config.get(
            "temporal_decay_hours", 168
        )  # 1 week
        self.max_fusion_results = self.config.get("max_fusion_results", 50)

        # Embedding dimension for similarity calculation (placeholder)
        self.embedding_dim = self.config.get("embedding_dim", 128)

        logger.info(
            "ResultFusionEngine initialized",
            extra={
                "config": self.config,
                "default_mmr_lambda": self.default_mmr_lambda,
                "similarity_threshold": self.similarity_threshold,
                "temporal_decay_hours": self.temporal_decay_hours,
            },
        )

    async def fuse_multi_store_results(
        self,
        store_results: Dict[str, Any],
        fusion_strategy: Dict[str, Any],
        preferences: Dict[str, Any],
        mmr_lambda: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fuse results from multiple stores using CA1-inspired integration.

        Implements the complete fusion workflow:
        1. Result normalization and preparation
        2. Cross-store deduplication
        3. Diversity optimization via MMR
        4. Temporal and entity weighting
        5. Final scoring and ranking

        Args:
            store_results: Results from multiple storage systems
            fusion_strategy: Strategy configuration for fusion
            preferences: User preferences for result assembly
            mmr_lambda: Override for diversity parameter

        Returns:
            List of fused and optimized results
        """
        start_time = datetime.now(timezone.utc)

        with start_span("context_bundle.result_fuser.fuse_multi_store_results") as span:
            try:
                # Extract and count input results
                all_results = []
                total_input_count = 0

                for store_name, store_result in store_results.items():
                    if store_result.status == "success":
                        for result in store_result.results:
                            all_results.append(result)
                            total_input_count += 1

                if span:
                    span.set_attribute("total_input_results", total_input_count)
                    span.set_attribute("input_stores", len(store_results))

                logger.info(
                    "Starting multi-store result fusion",
                    extra={
                        "total_input_results": total_input_count,
                        "stores": list(store_results.keys()),
                        "fusion_strategy": fusion_strategy.get(
                            "type", "mmr_diversification"
                        ),
                    },
                )

                if not all_results:
                    logger.warning("No results to fuse")
                    return []

                # Step 1: Normalize results across stores
                normalized_results = await self._normalize_cross_store_results(
                    all_results
                )

                # Step 2: Cross-store deduplication
                deduplicated_results = await self._deduplicate_cross_store_results(
                    normalized_results, self.similarity_threshold
                )

                # Step 3: Apply fusion strategy
                strategy_type = fusion_strategy.get("type", "mmr_diversification")
                lambda_param = mmr_lambda or fusion_strategy.get(
                    "lambda_diversity", self.default_mmr_lambda
                )
                max_results = preferences.get("max_results", 20)

                if strategy_type == "mmr_diversification":
                    fused_results = await self._apply_mmr_diversification(
                        deduplicated_results, lambda_param, max_results
                    )
                elif strategy_type == "temporal_weighted":
                    fused_results = await self._apply_temporal_weighting(
                        deduplicated_results, fusion_strategy, max_results
                    )
                elif strategy_type == "entity_focused":
                    fused_results = await self._apply_entity_focused_fusion(
                        deduplicated_results, fusion_strategy, max_results
                    )
                else:
                    # Default to simple relevance ranking
                    fused_results = await self._apply_relevance_ranking(
                        deduplicated_results, max_results
                    )

                # Step 4: Apply temporal and contextual boosts
                boosted_results = await self._apply_contextual_boosts(
                    fused_results, preferences
                )

                # Step 5: Final quality filtering and confidence adjustment
                final_results = await self._apply_quality_filtering(
                    boosted_results, self.min_confidence
                )

                # Calculate processing metrics
                end_time = datetime.now(timezone.utc)
                processing_time_ms = (end_time - start_time).total_seconds() * 1000

                if span:
                    span.set_attribute("final_result_count", len(final_results))
                    span.set_attribute(
                        "deduplication_removed",
                        total_input_count - len(deduplicated_results),
                    )
                    span.set_attribute("processing_time_ms", processing_time_ms)

                logger.info(
                    "Multi-store result fusion completed",
                    extra={
                        "input_results": total_input_count,
                        "deduplicated_results": len(deduplicated_results),
                        "final_results": len(final_results),
                        "deduplication_removed": total_input_count
                        - len(deduplicated_results),
                        "processing_time_ms": processing_time_ms,
                        "fusion_strategy": strategy_type,
                    },
                )

                return final_results

            except Exception as e:
                logger.error(
                    "Multi-store result fusion failed",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "fusion_strategy": fusion_strategy.get("type", "unknown"),
                    },
                )
                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))
                raise

    async def _normalize_cross_store_results(
        self, all_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Normalize results from different stores to common format."""

        normalized_results = []

        for result in all_results:
            # Create normalized result structure
            normalized = {
                "content_id": result.get(
                    "content_id", f"unknown_{len(normalized_results)}"
                ),
                "content": result.get("content", ""),
                "relevance_score": result.get("relevance_score", 0.5),
                "confidence": result.get("confidence", 0.5),
                "source_store": result.get("source_store", "unknown"),
                "temporal_context": result.get("temporal_context"),
                "entities": result.get("entities", []),
                "metadata": result.get("metadata", {}),
                "original_metadata": result,  # Preserve original for reference
            }

            # Normalize scores to 0-1 range
            normalized["relevance_score"] = max(
                0.0, min(1.0, normalized["relevance_score"])
            )
            normalized["confidence"] = max(0.0, min(1.0, normalized["confidence"]))

            # Generate content embedding placeholder for similarity calculation
            normalized["content_embedding"] = self._generate_content_embedding(
                normalized["content"]
            )

            normalized_results.append(normalized)

        logger.debug(
            "Cross-store result normalization completed",
            extra={"normalized_count": len(normalized_results)},
        )

        return normalized_results

    async def _deduplicate_cross_store_results(
        self, results: List[Dict[str, Any]], similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """Remove duplicates across different stores based on content similarity."""

        if not results:
            return []

        # Group similar results
        similarity_groups = []
        processed_indices = set()

        for i, result1 in enumerate(results):
            if i in processed_indices:
                continue

            # Start new similarity group
            group = [result1]
            processed_indices.add(i)

            # Find similar results
            for j, result2 in enumerate(results[i + 1 :], i + 1):
                if j in processed_indices:
                    continue

                similarity = self._calculate_content_similarity(
                    result1["content_embedding"], result2["content_embedding"]
                )

                if similarity >= similarity_threshold:
                    group.append(result2)
                    processed_indices.add(j)

            similarity_groups.append(group)

        # Select best representative from each group
        deduplicated_results = []
        deduplication_count = 0

        for group in similarity_groups:
            if len(group) == 1:
                deduplicated_results.append(group[0])
            else:
                # Merge group into single result
                merged_result = await self._merge_similar_results(group)
                deduplicated_results.append(merged_result)
                deduplication_count += len(group) - 1

        logger.debug(
            "Cross-store deduplication completed",
            extra={
                "input_results": len(results),
                "similarity_groups": len(similarity_groups),
                "deduplicated_results": len(deduplicated_results),
                "removed_duplicates": deduplication_count,
            },
        )

        return deduplicated_results

    async def _apply_mmr_diversification(
        self, results: List[Dict[str, Any]], lambda_diversity: float, max_results: int
    ) -> List[Dict[str, Any]]:
        """Apply Maximal Marginal Relevance for diversity optimization."""

        if not results or max_results <= 0:
            return []

        # Sort by relevance initially
        sorted_results = sorted(
            results, key=lambda x: x["relevance_score"], reverse=True
        )

        # MMR selection
        selected = []
        remaining = sorted_results[:]

        # Select highest relevance result first
        if remaining:
            best_initial = remaining.pop(0)
            selected.append(best_initial)

        # Iteratively select based on MMR score
        iteration_count = 0
        while len(selected) < max_results and remaining:
            iteration_count += 1

            mmr_scores = []

            for candidate in remaining:
                relevance = candidate["relevance_score"]

                # Calculate maximum similarity to already selected results
                max_similarity = 0.0
                for selected_result in selected:
                    similarity = self._calculate_content_similarity(
                        candidate["content_embedding"],
                        selected_result["content_embedding"],
                    )
                    max_similarity = max(max_similarity, similarity)

                # MMR formula: λ * Rel(d,Q) - (1-λ) * max[Sim(d,d')]
                mmr_score = (
                    lambda_diversity * relevance
                    - (1 - lambda_diversity) * max_similarity
                )

                mmr_scores.append((candidate, mmr_score, max_similarity))

            # Select candidate with highest MMR score
            if mmr_scores:
                best_candidate, best_score, candidate_max_similarity = max(
                    mmr_scores, key=lambda x: x[1]
                )
                best_candidate["mmr_score"] = best_score
                best_candidate["diversity_penalty"] = (
                    1 - lambda_diversity
                ) * candidate_max_similarity
                selected.append(best_candidate)
                remaining.remove(best_candidate)

        logger.debug(
            "MMR diversification completed",
            extra={
                "input_results": len(results),
                "selected_results": len(selected),
                "mmr_iterations": iteration_count,
                "lambda_diversity": lambda_diversity,
            },
        )

        return selected

    async def _apply_temporal_weighting(
        self,
        results: List[Dict[str, Any]],
        fusion_strategy: Dict[str, Any],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Apply temporal weighting to prioritize recent content."""

        temporal_weight = fusion_strategy.get("temporal_weight", 0.7)
        current_time = datetime.now(timezone.utc)

        # Apply temporal boosting
        for result in results:
            temporal_context = result.get("temporal_context")
            temporal_boost = 0.0

            if temporal_context:
                try:
                    if isinstance(temporal_context, str):
                        content_time = datetime.fromisoformat(
                            temporal_context.replace("Z", "+00:00")
                        )
                    else:
                        content_time = temporal_context

                    # Calculate time difference in hours
                    time_diff_hours = (
                        current_time - content_time
                    ).total_seconds() / 3600

                    # Apply exponential decay
                    temporal_boost = math.exp(
                        -time_diff_hours / self.temporal_decay_hours
                    )

                except (ValueError, TypeError):
                    temporal_boost = 0.5  # Default for unparseable timestamps

            # Combine relevance with temporal weight
            original_score = result["relevance_score"]
            temporal_adjusted_score = (
                1 - temporal_weight
            ) * original_score + temporal_weight * temporal_boost

            result["final_score"] = temporal_adjusted_score
            result["temporal_boost"] = temporal_boost

        # Sort by final score and limit results
        weighted_results = sorted(
            results, key=lambda x: x["final_score"], reverse=True
        )[:max_results]

        logger.debug(
            "Temporal weighting applied",
            extra={
                "input_results": len(results),
                "final_results": len(weighted_results),
                "temporal_weight": temporal_weight,
            },
        )

        return weighted_results

    async def _apply_entity_focused_fusion(
        self,
        results: List[Dict[str, Any]],
        fusion_strategy: Dict[str, Any],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Apply entity-focused fusion with entity matching boost."""

        entity_boost = fusion_strategy.get("entity_boost", 0.2)
        target_entities = fusion_strategy.get("target_entities", [])

        # Apply entity boosting
        for result in results:
            result_entities = set(result.get("entities", []))
            target_entity_set = set(target_entities)

            # Calculate entity overlap
            entity_overlap = len(result_entities & target_entity_set)
            total_target_entities = len(target_entity_set)

            if total_target_entities > 0:
                entity_score = entity_overlap / total_target_entities
            else:
                entity_score = 0.0

            # Apply entity boost
            original_score = result["relevance_score"]
            entity_boosted_score = original_score + (entity_boost * entity_score)

            result["final_score"] = min(entity_boosted_score, 1.0)
            result["entity_boost"] = entity_boost * entity_score

        # Sort and limit results
        entity_focused_results = sorted(
            results, key=lambda x: x["final_score"], reverse=True
        )[:max_results]

        logger.debug(
            "Entity-focused fusion applied",
            extra={
                "input_results": len(results),
                "final_results": len(entity_focused_results),
                "entity_boost": entity_boost,
                "target_entities": target_entities,
            },
        )

        return entity_focused_results

    async def _apply_relevance_ranking(
        self, results: List[Dict[str, Any]], max_results: int
    ) -> List[Dict[str, Any]]:
        """Apply simple relevance-based ranking."""

        # Set final score to relevance score
        for result in results:
            result["final_score"] = result["relevance_score"]

        # Sort by relevance and limit
        ranked_results = sorted(results, key=lambda x: x["final_score"], reverse=True)[
            :max_results
        ]

        return ranked_results

    async def _apply_contextual_boosts(
        self, results: List[Dict[str, Any]], preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply additional contextual boosts based on preferences."""

        include_related = preferences.get("include_related", True)
        recency_bias = preferences.get("recency_bias", 0.3)

        for result in results:
            boost_factors = []

            # Apply recency bias if enabled
            if recency_bias > 0 and result.get("temporal_boost"):
                recency_boost = recency_bias * result["temporal_boost"]
                boost_factors.append(recency_boost)

            # Apply metadata-based boosts
            metadata = result.get("metadata", {})
            if metadata.get("type") == "recent" and include_related:
                boost_factors.append(0.1)

            # Calculate total boost
            total_boost = sum(boost_factors)

            # Apply boost to final score
            current_score = result.get("final_score", result["relevance_score"])
            result["final_score"] = min(current_score + total_boost, 1.0)

        return results

    async def _apply_quality_filtering(
        self, results: List[Dict[str, Any]], min_confidence: float
    ) -> List[Dict[str, Any]]:
        """Filter results based on quality thresholds."""

        # Filter by minimum confidence
        quality_filtered = [
            result
            for result in results
            if result.get("confidence", 0.0) >= min_confidence
        ]

        # Sort by final score
        final_results = sorted(
            quality_filtered, key=lambda x: x.get("final_score", 0), reverse=True
        )

        logger.debug(
            "Quality filtering applied",
            extra={
                "input_results": len(results),
                "filtered_results": len(final_results),
                "min_confidence": min_confidence,
            },
        )

        return final_results

    async def _merge_similar_results(
        self, similar_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge similar results into a single representative result."""

        if not similar_results:
            return {}

        if len(similar_results) == 1:
            return similar_results[0]

        # Select best result as base
        best_result = max(similar_results, key=lambda x: x["relevance_score"])

        # Merge information from other results
        merged_result = best_result.copy()

        # Combine entities
        all_entities = set()
        for result in similar_results:
            all_entities.update(result.get("entities", []))
        merged_result["entities"] = list(all_entities)

        # Average confidence scores
        confidences = [r.get("confidence", 0.5) for r in similar_results]
        merged_result["confidence"] = sum(confidences) / len(confidences)

        # Track merged content IDs
        merged_ids = [r.get("content_id", "") for r in similar_results]
        merged_result["merged_content_ids"] = merged_ids

        # Preserve highest relevance score
        max_relevance = max(r.get("relevance_score", 0) for r in similar_results)
        merged_result["relevance_score"] = max_relevance

        return merged_result

    def _generate_content_embedding(self, content: str) -> List[float]:
        """Generate placeholder embedding for content similarity calculation."""

        # Simple hash-based embedding for testing
        # In production, this would use actual embedding models
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Convert hash to fixed-size embedding
        embedding = []
        for i in range(0, min(len(content_hash), self.embedding_dim * 2), 2):
            hex_pair = content_hash[i : i + 2]
            value = int(hex_pair, 16) / 255.0  # Normalize to 0-1
            embedding.append(value)

        # Pad to embedding dimension
        while len(embedding) < self.embedding_dim:
            embedding.append(0.0)

        return embedding[: self.embedding_dim]

    def _calculate_content_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between content embeddings."""

        if len(embedding1) != len(embedding2):
            return 0.0

        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in embedding1))
        magnitude2 = math.sqrt(sum(b * b for b in embedding2))

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # Cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)

        return max(0.0, min(1.0, similarity))

    async def get_fusion_metrics(self) -> Dict[str, Any]:
        """Get fusion engine performance metrics."""

        # This would return actual metrics from monitoring
        return {
            "total_fusions_performed": 0,
            "average_processing_time_ms": 0.0,
            "average_deduplication_rate": 0.0,
            "average_diversity_score": 0.0,
            "quality_improvement_ratio": 0.0,
        }


# TODO: Production enhancements needed:
# - Integrate with actual semantic embedding models (sentence transformers, OpenAI)
# - Implement learned fusion strategies based on user feedback
# - Add support for multimedia content fusion (images, audio)
# - Implement adaptive MMR lambda tuning based on query characteristics
# - Add cross-store confidence calibration
# - Implement incremental fusion for streaming results
# - Add A/B testing framework for fusion strategy optimization
