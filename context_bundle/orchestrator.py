"""
Context Bundle Orchestrator - Hippocampal-Cortical Recall Coordination
======================================================================

This module implements the central orchestrator for context bundle assembly,
coordinating parallel queries across multiple heterogeneous storage systems
and assembling rich, contextually relevant memory bundles through intelligent
fusion strategies.

**Neuroscience Inspiration:**
The hippocampal-cortical recall system coordinates retrieval across distributed
cortical areas, with CA1 acting as a convergence zone that integrates pattern-
completed outputs from CA3 with cortical inputs. This orchestrator mirrors that
function by coordinating parallel memory retrieval and assembling coherent
contextual representations for working memory.

**Research Backing:**
- Squire & Kandel (2009): Memory: From mind to molecules - hippocampal-cortical interactions
- Buckner & Carroll (2007): Self-projection and the brain - cortical memory networks
- Diana et al. (2007): Imaging recollection and familiarity in the medial temporal lobe
- Preston & Eichenbaum (2013): Interplay of hippocampus and prefrontal cortex in memory

The implementation coordinates multi-store queries with performance budgets,
applies intelligent fusion strategies, and maintains comprehensive provenance
tracking for all retrieved context.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from observability.logging import get_json_logger
from observability.trace import start_span

from .mmr_diversifier import DiversificationConfig, MMRDiversifier

logger = get_json_logger(__name__)


@dataclass
class RecallIntent:
    """
    Intent for context recall assembly.

    Represents a request for assembling contextual memory bundles
    from multiple storage systems based on query and preferences.
    """

    query: str
    query_type: str  # "semantic_search", "temporal_sequence", "entity_lookup"
    context_hints: Dict[str, Any]  # Temporal scope, entities, intent categories
    preferences: Dict[str, Any]  # Max results, inclusion rules, weighting
    space_id: str
    actor: Dict[str, Any]


@dataclass
class PerformanceBudget:
    """
    Performance constraints for context assembly.
    """

    max_latency_ms: int
    max_stores: int
    max_results_per_store: int
    max_total_results: int = 50
    timeout_buffer_ms: int = 100


@dataclass
class PolicyContext:
    """
    Policy and access control context for recall.
    """

    permitted_spaces: List[str]
    redaction_level: str  # "minimal", "standard", "aggressive"
    audit_required: bool
    access_restrictions: Optional[List[str]] = None


@dataclass
class StoreQueryResult:
    """
    Result from a single store query.
    """

    store_name: str
    status: str  # "success", "timeout", "error", "empty"
    results: List[Dict[str, Any]]
    latency_ms: float
    total_candidates: int
    error_details: Optional[str] = None


@dataclass
class ContextBundle:
    """
    Assembled context bundle with fusion metadata.
    """

    bundle_id: str
    request_id: str
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    processing_time_ms: float
    confidence: float
    diversity_score: float
    store_coverage: Dict[str, Any]
    fusion_metadata: Dict[str, Any]
    provenance: List[Dict[str, Any]]


class ContextBundleOrchestrator:
    """
    Orchestrates multi-store context assembly with hippocampal-cortical coordination.

    Implements the central coordination for context bundle assembly, managing
    parallel queries across heterogeneous storage systems and intelligent
    result fusion to create coherent contextual memory bundles.

    **Key Functions:**
    - Query analysis and store selection strategy
    - Parallel store query coordination with timeout management
    - Multi-store result fusion with MMR diversification
    - Performance budget enforcement and graceful degradation
    - Comprehensive provenance tracking and quality assessment
    """

    def __init__(
        self,
        # Component dependencies
        store_fanout=None,
        result_fuser=None,
        provenance_tracer=None,
        budget_enforcer=None,
        mmr_diversifier=None,
        # Store adapters
        store_adapters=None,
        # Configuration
        config: Optional[Dict[str, Any]] = None,
    ):
        # Configuration with defaults (must be set first)
        self.config = config or {}

        # Initialize components
        from context_bundle.provenance_tracer import ProvenanceTracer
        from context_bundle.result_fuser import ResultFusionEngine
        from context_bundle.store_fanout import StoreFanoutManager

        self.store_fanout = store_fanout or StoreFanoutManager()
        self.result_fuser = result_fuser or ResultFusionEngine()
        self.provenance_tracer = provenance_tracer or ProvenanceTracer()
        self.budget_enforcer = budget_enforcer

        # MMR Diversification for optimal result selection
        self.mmr_diversifier = mmr_diversifier or MMRDiversifier(
            DiversificationConfig(
                lambda_relevance=self.config.get("mmr_lambda", 0.6),
                lambda_adaptive=self.config.get("mmr_adaptive", True),
                algorithm=self.config.get("mmr_algorithm", "mmr_enhanced"),
                parallel_processing=True,
                caching_enabled=True,
            )
        )

        # Store adapters for different backend types
        self.store_adapters = store_adapters or {}
        self.default_budget = PerformanceBudget(
            max_latency_ms=self.config.get("max_latency_ms", 800),
            max_stores=self.config.get("max_stores", 4),
            max_results_per_store=self.config.get("max_results_per_store", 10),
            max_total_results=self.config.get("max_total_results", 50),
        )
        self.enable_mmr_diversification = self.config.get(
            "enable_mmr_diversification", True
        )
        self.mmr_lambda = self.config.get("mmr_lambda", 0.3)
        self.temporal_weight = self.config.get("temporal_weight", 0.7)

        # Store priority configuration
        self.store_priorities = self.config.get(
            "store_priorities",
            {
                "semantic_store": 1.0,
                "episodic_memory": 0.9,
                "knowledge_graph": 0.8,
                "full_text_index": 0.7,
                "vector_store": 0.6,
            },
        )

        logger.info(
            "ContextBundleOrchestrator initialized",
            extra={
                "config": self.config,
                "default_budget": self.default_budget.__dict__,
                "enable_mmr": self.enable_mmr_diversification,
                "store_priorities": self.store_priorities,
                "store_adapters_count": len(self.store_adapters),
            },
        )

    async def assemble_context_bundle(
        self,
        recall_intent: RecallIntent,
        budget: Optional[PerformanceBudget] = None,
        policy_context: Optional[PolicyContext] = None,
        request_id: Optional[str] = None,
    ) -> ContextBundle:
        """
        Assemble context bundle through hippocampal-cortical coordination.

        Implements the complete recall assembly workflow:
        1. Query analysis and store selection (CA3 pattern completion)
        2. Parallel store fanout with budget management
        3. Result fusion with MMR diversification (CA1 integration)
        4. Provenance tracking and quality assessment

        Args:
            recall_intent: Query and preferences for context assembly
            budget: Performance constraints and resource limits
            policy_context: Access control and privacy requirements
            request_id: Unique identifier for request tracking

        Returns:
            ContextBundle with assembled results and metadata

        Raises:
            ContextAssemblyError: If assembly fails or quality thresholds not met
        """
        start_time = datetime.now(timezone.utc)
        bundle_id = f"bundle_{uuid.uuid4().hex[:12]}"
        request_id = request_id or f"req_{uuid.uuid4().hex[:8]}"
        budget = budget or self.default_budget

        with start_span("context_bundle.orchestrator.assemble_context_bundle") as span:
            if span:
                span.set_attribute("bundle_id", bundle_id)
                span.set_attribute("request_id", request_id)
                span.set_attribute("query_length", len(recall_intent.query))
                span.set_attribute("query_type", recall_intent.query_type)

            try:
                logger.info(
                    "Starting context bundle assembly",
                    extra={
                        "bundle_id": bundle_id,
                        "request_id": request_id,
                        "query": recall_intent.query,
                        "query_type": recall_intent.query_type,
                        "space_id": recall_intent.space_id,
                        "budget": budget.__dict__,
                    },
                )

                # Step 1: Query analysis and store selection (CA3 pattern completion)
                query_plan = await self._analyze_query_and_plan_stores(
                    recall_intent, budget, policy_context
                )

                if span:
                    span.set_attribute(
                        "selected_stores", len(query_plan["selected_stores"])
                    )

                # Step 2: Parallel store fanout (distributed cortical activation)
                store_results = await self._execute_parallel_store_queries(
                    query_plan, budget
                )

                # Step 3: Result fusion and diversification (CA1 integration)
                fused_results = await self._fuse_and_diversify_results(
                    store_results, recall_intent, query_plan
                )

                # Step 4: Provenance tracking and quality assessment
                provenance_data = await self._generate_provenance_data(
                    store_results, fused_results, query_plan
                )

                # Step 5: Assemble final context bundle
                bundle = await self._assemble_final_bundle(
                    bundle_id=bundle_id,
                    request_id=request_id,
                    recall_intent=recall_intent,
                    fused_results=fused_results,
                    store_results=store_results,
                    provenance_data=provenance_data,
                    query_plan=query_plan,
                    start_time=start_time,
                )

                # Performance and quality metrics
                if span:
                    span.set_attribute("total_results", bundle.total_results)
                    span.set_attribute("processing_time_ms", bundle.processing_time_ms)
                    span.set_attribute("confidence", bundle.confidence)
                    span.set_attribute("diversity_score", bundle.diversity_score)

                logger.info(
                    "Context bundle assembly completed",
                    extra={
                        "bundle_id": bundle_id,
                        "total_results": bundle.total_results,
                        "processing_time_ms": bundle.processing_time_ms,
                        "confidence": bundle.confidence,
                        "diversity_score": bundle.diversity_score,
                        "store_coverage": bundle.store_coverage,
                    },
                )

                return bundle

            except Exception as e:
                logger.error(
                    "Context bundle assembly failed",
                    extra={
                        "bundle_id": bundle_id,
                        "request_id": request_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))
                raise ContextAssemblyError(
                    f"Failed to assemble context bundle: {str(e)}",
                    bundle_id=bundle_id,
                    request_id=request_id,
                )

    async def _analyze_query_and_plan_stores(
        self,
        recall_intent: RecallIntent,
        budget: PerformanceBudget,
        policy_context: Optional[PolicyContext],
    ) -> Dict[str, Any]:
        """Analyze query and determine optimal store selection strategy."""

        # Extract query characteristics
        query_features = self._extract_query_features(recall_intent)

        # Determine store selection based on query type and features
        selected_stores = []

        # Semantic content analysis
        if query_features.get("has_conceptual_content", True):
            selected_stores.append(
                {
                    "store": "semantic_store",
                    "priority": self.store_priorities.get("semantic_store", 1.0),
                    "query_type": "vector_similarity",
                    "allocated_budget": budget.max_latency_ms // 4,
                }
            )

        # Temporal/episodic analysis
        if query_features.get("has_temporal_markers", False):
            selected_stores.append(
                {
                    "store": "episodic_memory",
                    "priority": self.store_priorities.get("episodic_memory", 0.9),
                    "query_type": "temporal_sequence",
                    "allocated_budget": budget.max_latency_ms // 4,
                }
            )

        # Entity relationship analysis
        if query_features.get("has_entity_references", False):
            selected_stores.append(
                {
                    "store": "knowledge_graph",
                    "priority": self.store_priorities.get("knowledge_graph", 0.8),
                    "query_type": "graph_traversal",
                    "allocated_budget": budget.max_latency_ms // 4,
                }
            )

        # Full-text search for keyword queries
        if query_features.get("has_keyword_patterns", False):
            selected_stores.append(
                {
                    "store": "full_text_index",
                    "priority": self.store_priorities.get("full_text_index", 0.7),
                    "query_type": "text_search",
                    "allocated_budget": budget.max_latency_ms // 4,
                }
            )

        # Sort by priority and limit to budget
        selected_stores.sort(key=lambda x: x["priority"], reverse=True)
        selected_stores = selected_stores[: budget.max_stores]

        # Create query plan
        query_plan = {
            "query": recall_intent.query,
            "query_features": query_features,
            "selected_stores": selected_stores,
            "fusion_strategy": self._determine_fusion_strategy(
                recall_intent, query_features
            ),
            "policy_constraints": policy_context.__dict__ if policy_context else {},
        }

        logger.debug(
            "Query analysis and store planning completed",
            extra={
                "query_features": query_features,
                "selected_stores": [s["store"] for s in selected_stores],
                "fusion_strategy": query_plan["fusion_strategy"],
            },
        )

        return query_plan

    async def _execute_parallel_store_queries(
        self, query_plan: Dict[str, Any], budget: PerformanceBudget
    ) -> Dict[str, StoreQueryResult]:
        """Execute parallel queries across selected stores."""

        # Use store fanout manager for parallel coordination
        store_results = await self.store_fanout.execute_parallel_queries(
            query_plan=query_plan, budget=budget, store_adapters=self.store_adapters
        )

        logger.debug(
            "Parallel store queries completed",
            extra={
                "stores_queried": len(store_results),
                "successful_queries": len(
                    [r for r in store_results.values() if r.status == "success"]
                ),
                "total_results": sum(len(r.results) for r in store_results.values()),
            },
        )

        return store_results

    async def _fuse_and_diversify_results(
        self,
        store_results: Dict[str, StoreQueryResult],
        recall_intent: RecallIntent,
        query_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Fuse results from multiple stores with MMR diversification."""

        # First phase: Use result fusion engine for intelligent combination
        fused_results = await self.result_fuser.fuse_multi_store_results(
            store_results=store_results,
            fusion_strategy=query_plan["fusion_strategy"],
            preferences=recall_intent.preferences,
        )

        # Second phase: Apply MMR diversification if enabled and beneficial
        if self.enable_mmr_diversification and len(fused_results) > 1:
            target_count = min(
                recall_intent.preferences.get("max_results", 15), len(fused_results)
            )

            # Apply MMR diversification with query-specific context
            mmr_context = {
                "query_type": recall_intent.query_type,
                "context_hints": recall_intent.context_hints,
                "space_id": recall_intent.space_id,
                "high_precision_required": query_plan.get("precision_mode", False),
                "exploration_mode": query_plan.get("exploration_mode", False),
            }

            try:
                diversification_result = await self.mmr_diversifier.diversify_results(
                    items=fused_results,
                    query=recall_intent.query,
                    target_count=target_count,
                    context=mmr_context,
                )

                # Use diversified results if quality is satisfactory
                if (
                    diversification_result.diversity_score > 0.4
                    and diversification_result.relevance_score > 0.6
                ):
                    fused_results = diversification_result.selected_items

                    logger.info(
                        "MMR diversification applied successfully",
                        extra={
                            "original_count": len(fused_results),
                            "diversified_count": len(
                                diversification_result.selected_items
                            ),
                            "diversity_score": diversification_result.diversity_score,
                            "relevance_score": diversification_result.relevance_score,
                            "algorithm_used": diversification_result.algorithm_used,
                            "processing_time_ms": diversification_result.processing_time_ms,
                        },
                    )
                else:
                    logger.warning(
                        "MMR diversification quality below threshold, using fusion results",
                        extra={
                            "diversity_score": diversification_result.diversity_score,
                            "relevance_score": diversification_result.relevance_score,
                            "threshold_diversity": 0.4,
                            "threshold_relevance": 0.6,
                        },
                    )

            except Exception as e:
                logger.error(
                    "MMR diversification failed, falling back to fusion results",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "input_count": len(fused_results),
                    },
                    exc_info=True,
                )

        logger.debug(
            "Result fusion and diversification completed",
            extra={
                "input_results": sum(len(r.results) for r in store_results.values()),
                "fused_results": len(fused_results),
                "fusion_strategy": query_plan["fusion_strategy"]["type"],
                "mmr_enabled": self.enable_mmr_diversification,
            },
        )

        return fused_results

    async def _generate_provenance_data(
        self,
        store_results: Dict[str, StoreQueryResult],
        fused_results: List[Dict[str, Any]],
        query_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate comprehensive provenance tracking data."""

        # Use provenance tracer for detailed source attribution
        provenance_data = await self.provenance_tracer.trace_result_provenance(
            store_results=store_results,
            fused_results=fused_results,
            query_plan=query_plan,
        )

        return provenance_data

    async def _assemble_final_bundle(
        self,
        bundle_id: str,
        request_id: str,
        recall_intent: RecallIntent,
        fused_results: List[Dict[str, Any]],
        store_results: Dict[str, StoreQueryResult],
        provenance_data: List[Dict[str, Any]],
        query_plan: Dict[str, Any],
        start_time: datetime,
    ) -> ContextBundle:
        """Assemble the final context bundle with metadata."""

        # Calculate processing metrics
        end_time = datetime.now(timezone.utc)
        processing_time_ms = (end_time - start_time).total_seconds() * 1000

        # Calculate quality metrics
        confidence = self._calculate_bundle_confidence(fused_results, store_results)
        diversity_score = self._calculate_diversity_score(fused_results)

        # Build store coverage metadata
        store_coverage = {}
        for store_name, result in store_results.items():
            store_coverage[store_name] = {
                "queried": True,
                "status": result.status,
                "results": len(result.results),
                "latency_ms": result.latency_ms,
                "total_candidates": result.total_candidates,
            }

        # Build fusion metadata
        fusion_metadata = {
            "strategy": query_plan["fusion_strategy"]["type"],
            "mmr_lambda": self.mmr_lambda,
            "temporal_weight_applied": query_plan["fusion_strategy"].get(
                "temporal_weight", False
            ),
            "cross_store_deduplication": self._count_deduplicated_results(
                store_results, fused_results
            ),
        }

        return ContextBundle(
            bundle_id=bundle_id,
            request_id=request_id,
            query=recall_intent.query,
            results=fused_results,
            total_results=len(fused_results),
            processing_time_ms=processing_time_ms,
            confidence=confidence,
            diversity_score=diversity_score,
            store_coverage=store_coverage,
            fusion_metadata=fusion_metadata,
            provenance=provenance_data,
        )

    def _extract_query_features(self, recall_intent: RecallIntent) -> Dict[str, Any]:
        """Extract features from query for store selection."""

        query = recall_intent.query.lower()
        context_hints = recall_intent.context_hints or {}

        features = {
            "has_conceptual_content": True,  # Assume all queries have conceptual content
            "has_temporal_markers": any(
                word in query
                for word in [
                    "when",
                    "time",
                    "date",
                    "yesterday",
                    "tomorrow",
                    "last",
                    "next",
                    "before",
                    "after",
                    "during",
                    "while",
                    "recent",
                    "old",
                    "new",
                ]
            ),
            "has_entity_references": any(
                word in query
                for word in [
                    "who",
                    "what",
                    "where",
                    "person",
                    "place",
                    "thing",
                    "people",
                ]
            )
            or "entities" in context_hints,
            "has_keyword_patterns": len(query.split())
            <= 5,  # Short queries likely keyword-based
            "query_length": len(query),
            "word_count": len(query.split()),
            "has_questions": query.strip().endswith("?"),
            "temporal_scope": context_hints.get("temporal_scope", "any"),
            "intent_categories": context_hints.get("intent_categories", []),
        }

        return features

    def _determine_fusion_strategy(
        self, recall_intent: RecallIntent, query_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine optimal fusion strategy based on query characteristics."""

        strategy = {
            "type": "mmr_diversification",  # Default strategy
            "lambda_diversity": self.mmr_lambda,
            "temporal_weight": query_features.get("has_temporal_markers", False),
            "max_results": recall_intent.preferences.get("max_results", 20),
        }

        # Adjust strategy based on query type
        if recall_intent.query_type == "temporal_sequence":
            strategy["type"] = "temporal_weighted"
            strategy["temporal_weight"] = self.temporal_weight

        elif query_features.get("has_entity_references", False):
            strategy["type"] = "entity_focused"
            strategy["entity_boost"] = 0.2

        return strategy

    def _calculate_bundle_confidence(
        self,
        fused_results: List[Dict[str, Any]],
        store_results: Dict[str, StoreQueryResult],
    ) -> float:
        """Calculate overall confidence for the assembled bundle."""

        if not fused_results:
            return 0.0

        # Average confidence of individual results
        result_confidences = [result.get("confidence", 0.5) for result in fused_results]
        avg_confidence = sum(result_confidences) / len(result_confidences)

        # Adjust based on store coverage
        successful_stores = len(
            [r for r in store_results.values() if r.status == "success"]
        )
        total_stores = len(store_results)
        coverage_factor = successful_stores / total_stores if total_stores > 0 else 0

        # Final confidence with coverage adjustment
        final_confidence = avg_confidence * (0.7 + 0.3 * coverage_factor)

        return min(final_confidence, 1.0)

    def _calculate_diversity_score(self, fused_results: List[Dict[str, Any]]) -> float:
        """Calculate diversity score for the result set."""

        if len(fused_results) <= 1:
            return 1.0

        # Simple diversity calculation based on content variation
        # In production, this would use semantic similarity analysis

        unique_sources = set(
            result.get("source_store", "unknown") for result in fused_results
        )
        source_diversity = len(unique_sources) / len(fused_results)

        # Content length variation as proxy for diversity
        content_lengths = [len(result.get("content", "")) for result in fused_results]
        if content_lengths:
            avg_length = sum(content_lengths) / len(content_lengths)
            length_variance = sum(
                (length - avg_length) ** 2 for length in content_lengths
            ) / len(content_lengths)
            length_diversity = min(length_variance / (avg_length**2 + 1), 1.0)
        else:
            length_diversity = 0.0

        # Combined diversity score
        diversity_score = 0.6 * source_diversity + 0.4 * length_diversity

        return min(diversity_score, 1.0)

    def _count_deduplicated_results(
        self,
        store_results: Dict[str, StoreQueryResult],
        fused_results: List[Dict[str, Any]],
    ) -> int:
        """Count how many results were deduplicated during fusion."""

        total_input_results = sum(len(r.results) for r in store_results.values())
        final_results = len(fused_results)

        return max(0, total_input_results - final_results)

    async def get_bundle_status(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a specific bundle."""

        # This would query bundle metadata from storage
        # For now, return placeholder status
        return {
            "bundle_id": bundle_id,
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_orchestrator_metrics(self) -> Dict[str, Any]:
        """Get orchestrator performance and quality metrics."""

        # This would return actual metrics from monitoring
        return {
            "total_bundles_assembled": 0,
            "average_processing_time_ms": 0.0,
            "average_confidence": 0.0,
            "average_diversity_score": 0.0,
            "store_success_rates": {},
        }


class ContextAssemblyError(Exception):
    """Exception raised when context assembly fails."""

    def __init__(self, message: str, bundle_id: str, request_id: str):
        super().__init__(message)
        self.bundle_id = bundle_id
        self.request_id = request_id


# TODO: Production enhancements needed:
# - Integrate with actual semantic similarity models for diversity calculation
# - Implement adaptive query planning based on historical performance
# - Add caching layer for frequently requested context patterns
# - Implement bundle quality learning from user feedback
# - Add support for incremental bundle assembly for large queries
# - Implement bundle versioning and update mechanisms
