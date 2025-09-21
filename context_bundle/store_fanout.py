"""
Store Fanout Manager - Distributed Cortical Activation for Parallel Queries
============================================================================

This module implements parallel query coordination across multiple heterogeneous
storage systems, managing concurrent execution with timeout handling, error
isolation, and graceful degradation. It mirrors distributed cortical activation
patterns where multiple brain regions are simultaneously activated for recall.

**Neuroscience Inspiration:**
Cortical memory networks involve distributed activation across multiple brain
regions during recall, with parallel processing and convergence. This fanout
manager mirrors how the brain activates multiple cortical areas simultaneously,
coordinates their responses, and handles partial information when some regions
are unavailable or slow to respond.

**Research Backing:**
- Buckner & Carroll (2007): Self-projection and the brain - cortical memory networks
- Rugg & Vilberg (2013): Brain networks underlying episodic memory retrieval
- Cabeza & Moscovitch (2013): Memory systems, processing modes, and components
- Simons & Spiers (2003): Prefrontal and medial temporal lobe interactions

The implementation provides robust parallel query execution with performance
budgets, error isolation, and adaptive timeout management for responsive
user experience while maintaining data quality.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from observability.logging import get_json_logger
from observability.trace import start_span

logger = get_json_logger(__name__)


@dataclass
class StoreAdapter:
    """
    Adapter interface for different storage backend types.
    """

    store_name: str
    store_type: str  # "vector", "graph", "text", "episodic"
    connection_pool: Any
    default_timeout_ms: int
    max_concurrent_queries: int = 5


@dataclass
class QueryPlan:
    """
    Execution plan for a single store query.
    """

    store_name: str
    query_type: str  # "vector_similarity", "graph_traversal", "text_search", "temporal_sequence"
    adapted_query: Dict[str, Any]  # Store-specific query format
    timeout_ms: int
    max_results: int
    priority: float


@dataclass
class StoreQueryResult:
    """
    Result from a single store query execution.
    """

    store_name: str
    status: str  # "success", "timeout", "error", "empty"
    results: List[Dict[str, Any]]
    latency_ms: float
    total_candidates: int
    query_metadata: Dict[str, Any]
    error_details: Optional[str] = None


class StoreFanoutManager:
    """
    Manages parallel query execution across multiple heterogeneous storage systems.

    Implements distributed cortical activation patterns by coordinating simultaneous
    queries across different storage backends, handling timeouts and errors gracefully,
    and ensuring responsive performance within budget constraints.

    **Key Functions:**
    - Parallel query coordination with timeout management
    - Store-specific query adaptation and optimization
    - Error isolation preventing cascading failures
    - Graceful degradation with partial results
    - Performance budget enforcement and monitoring
    """

    def __init__(
        self,
        # Store adapters for different backend types
        store_adapters: Optional[Dict[str, StoreAdapter]] = None,
        # Configuration
        config: Optional[Dict[str, Any]] = None,
    ):
        # Store adapters configuration
        self.store_adapters = store_adapters or {}

        # Configuration with defaults
        self.config = config or {}
        self.default_timeout_ms = self.config.get("default_timeout_ms", 500)
        self.max_concurrent_stores = self.config.get("max_concurrent_stores", 6)
        self.timeout_buffer_ms = self.config.get("timeout_buffer_ms", 100)
        self.enable_circuit_breaker = self.config.get("enable_circuit_breaker", True)
        self.partial_results_threshold = self.config.get(
            "partial_results_threshold", 0.5
        )

        # Circuit breaker state for each store
        self._circuit_breakers = {}
        self._store_performance_history = {}

        # Initialize default store adapters if none provided
        if not self.store_adapters:
            self._initialize_default_adapters()

        logger.info(
            "StoreFanoutManager initialized",
            extra={
                "config": self.config,
                "store_adapters": list(self.store_adapters.keys()),
                "default_timeout_ms": self.default_timeout_ms,
                "max_concurrent_stores": self.max_concurrent_stores,
            },
        )

    async def execute_parallel_queries(
        self,
        query_plan: Dict[str, Any],
        budget,
        store_adapters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, StoreQueryResult]:
        """
        Execute parallel queries across selected stores with budget management.

        Implements distributed cortical activation by simultaneously querying
        multiple storage systems while respecting performance budgets and
        handling partial failures gracefully.

        Args:
            query_plan: Query execution plan with store selection and adaptation
            budget: Performance budget constraints
            store_adapters: Optional store adapter overrides

        Returns:
            Dictionary mapping store names to query results
        """
        start_time = datetime.now(timezone.utc)

        with start_span("context_bundle.store_fanout.execute_parallel_queries") as span:
            span.set_attribute("stores_planned", len(query_plan["selected_stores"]))
            span.set_attribute("budget_ms", budget.max_latency_ms)

            try:
                logger.info(
                    "Starting parallel store queries",
                    extra={
                        "stores_selected": [
                            s["store"] for s in query_plan["selected_stores"]
                        ],
                        "budget_ms": budget.max_latency_ms,
                        "query": query_plan["query"][:100],  # Truncate for logging
                    },
                )

                # Step 1: Prepare query plans for each store
                store_query_plans = await self._prepare_store_query_plans(
                    query_plan, budget
                )

                # Step 2: Execute queries in parallel with timeout management
                query_results = await self._execute_concurrent_queries(
                    store_query_plans, budget
                )

                # Step 3: Post-process results and update performance metrics
                processed_results = await self._post_process_query_results(
                    query_results, start_time
                )

                # Update performance tracking
                await self._update_store_performance_metrics(processed_results)

                # Calculate overall execution metrics
                end_time = datetime.now(timezone.utc)
                total_latency_ms = (end_time - start_time).total_seconds() * 1000

                span.set_attribute("total_latency_ms", total_latency_ms)
                span.set_attribute(
                    "successful_stores",
                    len(
                        [r for r in processed_results.values() if r.status == "success"]
                    ),
                )
                span.set_attribute(
                    "total_results",
                    sum(len(r.results) for r in processed_results.values()),
                )

                logger.info(
                    "Parallel store queries completed",
                    extra={
                        "total_latency_ms": total_latency_ms,
                        "successful_stores": len(
                            [
                                r
                                for r in processed_results.values()
                                if r.status == "success"
                            ]
                        ),
                        "total_results": sum(
                            len(r.results) for r in processed_results.values()
                        ),
                        "store_results": {
                            name: {
                                "status": r.status,
                                "count": len(r.results),
                                "latency": r.latency_ms,
                            }
                            for name, r in processed_results.items()
                        },
                    },
                )

                return processed_results

            except Exception as e:
                logger.error(
                    "Parallel store queries failed",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "stores_planned": [
                            s["store"] for s in query_plan["selected_stores"]
                        ],
                    },
                )
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise

    async def _prepare_store_query_plans(
        self, query_plan: Dict[str, Any], budget
    ) -> List[QueryPlan]:
        """Prepare store-specific query plans with adaptation."""

        store_query_plans = []

        for store_config in query_plan["selected_stores"]:
            store_name = store_config["store"]

            # Check circuit breaker status
            if self._is_circuit_breaker_open(store_name):
                logger.warning(
                    f"Circuit breaker open for store {store_name}, skipping query",
                    extra={"store": store_name, "circuit_breaker": "open"},
                )
                continue

            # Adapt query for specific store type
            adapted_query = await self._adapt_query_for_store(
                query=query_plan["query"],
                query_features=query_plan["query_features"],
                store_config=store_config,
            )

            # Calculate timeout allocation
            allocated_timeout = min(
                store_config.get("allocated_budget", self.default_timeout_ms),
                budget.max_latency_ms - self.timeout_buffer_ms,
            )

            query_plan_item = QueryPlan(
                store_name=store_name,
                query_type=store_config["query_type"],
                adapted_query=adapted_query,
                timeout_ms=allocated_timeout,
                max_results=budget.max_results_per_store,
                priority=store_config.get("priority", 1.0),
            )

            store_query_plans.append(query_plan_item)

        # Sort by priority for better resource allocation
        store_query_plans.sort(key=lambda x: x.priority, reverse=True)

        logger.debug(
            "Store query plans prepared",
            extra={
                "plans_count": len(store_query_plans),
                "stores": [p.store_name for p in store_query_plans],
                "timeouts": [p.timeout_ms for p in store_query_plans],
            },
        )

        return store_query_plans

    async def _execute_concurrent_queries(
        self, store_query_plans: List[QueryPlan], budget
    ) -> Dict[str, StoreQueryResult]:
        """Execute store queries concurrently with timeout management."""

        # Create tasks for parallel execution
        query_tasks = []

        for plan in store_query_plans:
            task = asyncio.create_task(
                self._execute_single_store_query(plan), name=f"query_{plan.store_name}"
            )
            query_tasks.append((plan.store_name, task))

        # Execute with overall timeout
        results = {}
        overall_timeout = budget.max_latency_ms / 1000  # Convert to seconds

        try:
            async with asyncio.timeout(overall_timeout):
                # Wait for all tasks to complete or timeout
                for store_name, task in query_tasks:
                    try:
                        result = await task
                        results[store_name] = result
                    except asyncio.TimeoutError:
                        logger.warning(
                            f"Query timeout for store {store_name}",
                            extra={
                                "store": store_name,
                                "timeout_ms": overall_timeout * 1000,
                            },
                        )
                        results[store_name] = StoreQueryResult(
                            store_name=store_name,
                            status="timeout",
                            results=[],
                            latency_ms=overall_timeout * 1000,
                            total_candidates=0,
                            query_metadata={},
                            error_details="Query timeout",
                        )
                    except Exception as e:
                        logger.error(
                            f"Query error for store {store_name}: {str(e)}",
                            extra={"store": store_name, "error": str(e)},
                        )
                        results[store_name] = StoreQueryResult(
                            store_name=store_name,
                            status="error",
                            results=[],
                            latency_ms=0,
                            total_candidates=0,
                            query_metadata={},
                            error_details=str(e),
                        )

        except asyncio.TimeoutError:
            # Handle overall timeout - cancel remaining tasks
            logger.warning(
                "Overall query timeout reached, cancelling remaining tasks",
                extra={"timeout_ms": overall_timeout * 1000},
            )

            for store_name, task in query_tasks:
                if not task.done():
                    task.cancel()
                    if store_name not in results:
                        results[store_name] = StoreQueryResult(
                            store_name=store_name,
                            status="timeout",
                            results=[],
                            latency_ms=overall_timeout * 1000,
                            total_candidates=0,
                            query_metadata={},
                            error_details="Overall timeout",
                        )

        return results

    async def _execute_single_store_query(self, plan: QueryPlan) -> StoreQueryResult:
        """Execute query against a single store with error handling."""

        start_time = datetime.now(timezone.utc)

        try:
            # Get store adapter
            adapter = self.store_adapters.get(plan.store_name)
            if not adapter:
                return StoreQueryResult(
                    store_name=plan.store_name,
                    status="error",
                    results=[],
                    latency_ms=0,
                    total_candidates=0,
                    query_metadata={},
                    error_details=f"No adapter found for store {plan.store_name}",
                )

            # Execute store-specific query
            if plan.query_type == "vector_similarity":
                results = await self._execute_vector_query(adapter, plan)
            elif plan.query_type == "graph_traversal":
                results = await self._execute_graph_query(adapter, plan)
            elif plan.query_type == "text_search":
                results = await self._execute_text_query(adapter, plan)
            elif plan.query_type == "temporal_sequence":
                results = await self._execute_temporal_query(adapter, plan)
            else:
                results = await self._execute_generic_query(adapter, plan)

            # Calculate latency
            end_time = datetime.now(timezone.utc)
            latency_ms = (end_time - start_time).total_seconds() * 1000

            return StoreQueryResult(
                store_name=plan.store_name,
                status="success" if results else "empty",
                results=results,
                latency_ms=latency_ms,
                total_candidates=len(results),
                query_metadata={
                    "query_type": plan.query_type,
                    "timeout_ms": plan.timeout_ms,
                    "max_results": plan.max_results,
                },
            )

        except asyncio.TimeoutError:
            latency_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            return StoreQueryResult(
                store_name=plan.store_name,
                status="timeout",
                results=[],
                latency_ms=latency_ms,
                total_candidates=0,
                query_metadata={},
                error_details="Query timeout",
            )

        except Exception as e:
            latency_ms = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000
            return StoreQueryResult(
                store_name=plan.store_name,
                status="error",
                results=[],
                latency_ms=latency_ms,
                total_candidates=0,
                query_metadata={},
                error_details=str(e),
            )

    async def _adapt_query_for_store(
        self, query: str, query_features: Dict[str, Any], store_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adapt generic query for specific store type."""

        store_name = store_config["store"]
        query_type = store_config["query_type"]

        # Base adapted query
        adapted_query = {
            "query": query,
            "max_results": store_config.get("max_results", 10),
            "timeout_ms": store_config.get("allocated_budget", self.default_timeout_ms),
        }

        # Store-specific adaptations
        if store_name == "semantic_store" and query_type == "vector_similarity":
            adapted_query.update(
                {
                    "embedding_query": query,  # Would be converted to embedding
                    "similarity_threshold": 0.7,
                    "include_metadata": True,
                }
            )

        elif store_name == "knowledge_graph" and query_type == "graph_traversal":
            # Extract entities for graph traversal
            entities = query_features.get("entities", [])
            adapted_query.update(
                {
                    "start_entities": entities,
                    "max_hops": 2,
                    "relationship_types": ["related_to", "mentions", "involves"],
                }
            )

        elif store_name == "full_text_index" and query_type == "text_search":
            adapted_query.update(
                {
                    "search_query": query,
                    "fields": ["content", "title", "summary"],
                    "boost_recent": True,
                    "minimum_score": 0.1,
                }
            )

        elif store_name == "episodic_memory" and query_type == "temporal_sequence":
            temporal_hints = query_features.get("temporal_scope", "any")
            adapted_query.update(
                {
                    "temporal_query": query,
                    "temporal_scope": temporal_hints,
                    "sequence_length": 5,
                    "include_context": True,
                }
            )

        return adapted_query

    async def _execute_vector_query(
        self, adapter: StoreAdapter, plan: QueryPlan
    ) -> List[Dict[str, Any]]:
        """Execute vector similarity query."""
        # Placeholder implementation - would integrate with actual vector store
        logger.debug(f"Executing vector query for {adapter.store_name}")

        # Simulate query execution
        await asyncio.sleep(0.1)  # Simulate network latency

        # Return mock results
        return [
            {
                "content_id": f"vec_{i}",
                "content": f"Vector result {i} for query: {plan.adapted_query['query'][:50]}",
                "similarity_score": 0.9 - (i * 0.1),
                "source_store": adapter.store_name,
                "metadata": {"type": "vector_match"},
            }
            for i in range(min(3, plan.max_results))
        ]

    async def _execute_graph_query(
        self, adapter: StoreAdapter, plan: QueryPlan
    ) -> List[Dict[str, Any]]:
        """Execute knowledge graph traversal query."""
        logger.debug(f"Executing graph query for {adapter.store_name}")

        await asyncio.sleep(0.08)  # Simulate processing time

        return [
            {
                "content_id": f"graph_{i}",
                "content": f"Graph result {i} for entities in: {plan.adapted_query['query'][:50]}",
                "relevance_score": 0.85 - (i * 0.1),
                "source_store": adapter.store_name,
                "metadata": {"type": "graph_traversal", "hops": i + 1},
            }
            for i in range(min(2, plan.max_results))
        ]

    async def _execute_text_query(
        self, adapter: StoreAdapter, plan: QueryPlan
    ) -> List[Dict[str, Any]]:
        """Execute full-text search query."""
        logger.debug(f"Executing text query for {adapter.store_name}")

        await asyncio.sleep(0.05)  # Fast text search

        return [
            {
                "content_id": f"text_{i}",
                "content": f"Text search result {i}: {plan.adapted_query['query'][:50]}",
                "text_score": 0.8 - (i * 0.1),
                "source_store": adapter.store_name,
                "metadata": {"type": "text_search", "field_matches": ["content"]},
            }
            for i in range(min(4, plan.max_results))
        ]

    async def _execute_temporal_query(
        self, adapter: StoreAdapter, plan: QueryPlan
    ) -> List[Dict[str, Any]]:
        """Execute temporal sequence query."""
        logger.debug(f"Executing temporal query for {adapter.store_name}")

        await asyncio.sleep(0.12)  # Temporal queries can be slower

        return [
            {
                "content_id": f"temporal_{i}",
                "content": f"Temporal result {i}: {plan.adapted_query['query'][:50]}",
                "temporal_score": 0.9 - (i * 0.05),
                "source_store": adapter.store_name,
                "metadata": {"type": "temporal_sequence", "time_period": "recent"},
            }
            for i in range(min(3, plan.max_results))
        ]

    async def _execute_generic_query(
        self, adapter: StoreAdapter, plan: QueryPlan
    ) -> List[Dict[str, Any]]:
        """Execute generic query for unknown store types."""
        logger.debug(f"Executing generic query for {adapter.store_name}")

        await asyncio.sleep(0.1)

        return [
            {
                "content_id": f"generic_{i}",
                "content": f"Generic result {i}: {plan.adapted_query['query'][:50]}",
                "score": 0.7 - (i * 0.1),
                "source_store": adapter.store_name,
                "metadata": {"type": "generic"},
            }
            for i in range(min(2, plan.max_results))
        ]

    async def _post_process_query_results(
        self, query_results: Dict[str, StoreQueryResult], start_time: datetime
    ) -> Dict[str, StoreQueryResult]:
        """Post-process query results and normalize formats."""

        processed_results = {}

        for store_name, result in query_results.items():
            # Normalize result format
            normalized_results = []

            for item in result.results:
                normalized_item = {
                    "content_id": item.get(
                        "content_id", f"unknown_{len(normalized_results)}"
                    ),
                    "content": item.get("content", ""),
                    "relevance_score": self._normalize_score(item, store_name),
                    "source_store": store_name,
                    "confidence": self._calculate_confidence(item, result),
                    "metadata": item.get("metadata", {}),
                    "temporal_context": item.get("timestamp"),
                    "entities": self._extract_entities(item.get("content", "")),
                }
                normalized_results.append(normalized_item)

            # Update result with normalized data
            processed_result = StoreQueryResult(
                store_name=result.store_name,
                status=result.status,
                results=normalized_results,
                latency_ms=result.latency_ms,
                total_candidates=result.total_candidates,
                query_metadata=result.query_metadata,
                error_details=result.error_details,
            )

            processed_results[store_name] = processed_result

        return processed_results

    def _normalize_score(self, item: Dict[str, Any], store_name: str) -> float:
        """Normalize scores from different stores to common scale."""

        # Extract various score fields
        similarity_score = item.get("similarity_score", 0.0)
        relevance_score = item.get("relevance_score", 0.0)
        text_score = item.get("text_score", 0.0)
        temporal_score = item.get("temporal_score", 0.0)
        generic_score = item.get("score", 0.0)

        # Use the highest available score
        score = max(
            similarity_score, relevance_score, text_score, temporal_score, generic_score
        )

        # Apply store-specific normalization factors
        normalization_factors = {
            "semantic_store": 1.0,
            "episodic_memory": 0.95,
            "knowledge_graph": 0.9,
            "full_text_index": 0.85,
        }

        factor = normalization_factors.get(store_name, 0.8)
        return min(score * factor, 1.0)

    def _calculate_confidence(
        self, item: Dict[str, Any], result: StoreQueryResult
    ) -> float:
        """Calculate confidence score for individual result."""

        base_confidence = 0.8  # Base confidence for successful queries

        # Adjust based on query latency (faster = more confident)
        latency_factor = max(0.5, 1.0 - (result.latency_ms / 1000))

        # Adjust based on score
        score = self._normalize_score(item, result.store_name)
        score_factor = score

        # Combined confidence
        confidence = base_confidence * latency_factor * score_factor

        return min(confidence, 1.0)

    def _extract_entities(self, content: str) -> List[str]:
        """Extract entities from content (placeholder implementation)."""

        # Simple entity extraction - in production would use NER
        common_entities = [
            "family",
            "vacation",
            "work",
            "home",
            "friend",
            "meeting",
            "project",
        ]
        found_entities = [
            entity for entity in common_entities if entity.lower() in content.lower()
        ]

        return found_entities

    async def _update_store_performance_metrics(
        self, results: Dict[str, StoreQueryResult]
    ) -> None:
        """Update performance tracking for circuit breaker decisions."""

        for store_name, result in results.items():
            if store_name not in self._store_performance_history:
                self._store_performance_history[store_name] = {
                    "total_queries": 0,
                    "successful_queries": 0,
                    "average_latency_ms": 0.0,
                    "error_rate": 0.0,
                }

            history = self._store_performance_history[store_name]
            history["total_queries"] += 1

            if result.status == "success":
                history["successful_queries"] += 1

            # Update rolling average latency
            history["average_latency_ms"] = (
                history["average_latency_ms"] * (history["total_queries"] - 1)
                + result.latency_ms
            ) / history["total_queries"]

            # Calculate error rate
            history["error_rate"] = 1.0 - (
                history["successful_queries"] / history["total_queries"]
            )

    def _is_circuit_breaker_open(self, store_name: str) -> bool:
        """Check if circuit breaker is open for a store."""

        if not self.enable_circuit_breaker:
            return False

        history = self._store_performance_history.get(store_name, {})
        error_rate = history.get("error_rate", 0.0)

        # Open circuit breaker if error rate is too high
        return error_rate > 0.5 and history.get("total_queries", 0) > 5

    def _initialize_default_adapters(self) -> None:
        """Initialize default store adapters for testing."""

        default_adapters = {
            "semantic_store": StoreAdapter(
                store_name="semantic_store",
                store_type="vector",
                connection_pool=None,
                default_timeout_ms=400,
            ),
            "episodic_memory": StoreAdapter(
                store_name="episodic_memory",
                store_type="episodic",
                connection_pool=None,
                default_timeout_ms=300,
            ),
            "knowledge_graph": StoreAdapter(
                store_name="knowledge_graph",
                store_type="graph",
                connection_pool=None,
                default_timeout_ms=350,
            ),
            "full_text_index": StoreAdapter(
                store_name="full_text_index",
                store_type="text",
                connection_pool=None,
                default_timeout_ms=200,
            ),
        }

        self.store_adapters.update(default_adapters)

        logger.debug(
            "Default store adapters initialized",
            extra={"adapters": list(default_adapters.keys())},
        )

    async def get_store_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all stores."""

        return {
            "store_performance": self._store_performance_history,
            "circuit_breakers": {
                store: self._is_circuit_breaker_open(store)
                for store in self.store_adapters.keys()
            },
        }


# TODO: Production enhancements needed:
# - Integrate with actual storage backend connection pools
# - Implement sophisticated circuit breaker patterns with recovery
# - Add query result caching for frequent patterns
# - Implement adaptive timeout adjustment based on historical performance
# - Add load balancing across multiple instances of same store type
# - Implement query optimization based on store characteristics
# - Add comprehensive error classification and retry strategies
