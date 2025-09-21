"""
Provenance Tracer - Memory Lineage and Source Attribution System
================================================================

This module implements comprehensive provenance tracking for context bundle
assembly, providing transparent source attribution, confidence lineage, and
debugging capabilities. It mirrors the brain's ability to track the source
and reliability of retrieved memories for metacognitive assessment.

**Neuroscience Inspiration:**
The brain maintains sophisticated source monitoring capabilities that track
where memories came from, when they were formed, and how reliable they are.
The frontal cortex, particularly the anterior prefrontal cortex, is crucial
for source monitoring and metacognitive awareness of memory accuracy.

**Research Backing:**
- Johnson et al. (1993): Source monitoring - distinguishing memory sources
- Mitchell & Johnson (2009): Source monitoring 15 years later: What have we learned?
- Reder et al. (2009): A mechanistic account of the mirror effect for word frequency
- Yonelinas (2002): The nature of recollection and familiarity

The implementation provides detailed lineage tracking, confidence propagation,
and source attribution for comprehensive memory provenance analysis.
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from observability.logging import get_json_logger
from observability.trace import start_span

logger = get_json_logger(__name__)


@dataclass
class ProvenanceNode:
    """
    Individual node in the provenance graph.
    """

    node_id: str
    node_type: str  # "query", "store", "result", "fusion", "filter"
    timestamp: datetime
    operation: str
    input_ids: List[str]
    output_ids: List[str]
    metadata: Dict[str, Any]
    confidence: float
    processing_time_ms: float


@dataclass
class SourceAttribution:
    """
    Attribution information for a specific result source.
    """

    source_id: str
    source_type: str  # "vector_store", "graph_store", "text_store", "temporal_store"
    source_path: str
    confidence: float
    contribution_weight: float
    retrieval_timestamp: datetime
    query_parameters: Dict[str, Any]
    transformation_history: List[str]


@dataclass
class ConfidencePropagation:
    """
    Confidence tracking through processing pipeline.
    """

    initial_confidence: float
    fusion_confidence: float
    temporal_adjustment: float
    diversity_penalty: float
    quality_filter_confidence: float
    final_confidence: float
    confidence_factors: Dict[str, float]


@dataclass
class ProvenanceTrace:
    """
    Complete provenance trace for a context bundle.
    """

    trace_id: str
    bundle_id: str
    query_context: Dict[str, Any]
    source_attributions: List[SourceAttribution]
    processing_graph: List[ProvenanceNode]
    confidence_lineage: ConfidencePropagation
    execution_timeline: List[Dict[str, Any]]
    quality_metrics: Dict[str, float]
    created_at: datetime


class ProvenanceTracer:
    """
    Implements comprehensive provenance tracking for context bundle assembly.

    Provides detailed lineage tracking, source attribution, and confidence
    propagation analysis to enable transparency, debugging, and quality
    assessment of memory retrieval and fusion processes.

    **Key Functions:**
    - Source attribution and lineage tracking
    - Confidence propagation analysis
    - Processing graph construction
    - Quality metrics calculation
    - Debugging and audit support
    """

    def __init__(
        self,
        # Configuration
        config: Optional[Dict[str, Any]] = None,
    ):
        # Configuration with defaults
        self.config = config or {}
        self.enable_detailed_tracking = self.config.get(
            "enable_detailed_tracking", True
        )
        self.max_trace_depth = self.config.get("max_trace_depth", 10)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.1)
        self.retention_days = self.config.get("retention_days", 30)

        # In-memory trace storage (would be database in production)
        self.active_traces: Dict[str, ProvenanceTrace] = {}
        self.processing_nodes: Dict[str, List[ProvenanceNode]] = {}

        logger.info(
            "ProvenanceTracer initialized",
            extra={
                "config": self.config,
                "enable_detailed_tracking": self.enable_detailed_tracking,
                "max_trace_depth": self.max_trace_depth,
                "confidence_threshold": self.confidence_threshold,
            },
        )

    async def start_trace(
        self,
        bundle_id: str,
        query_context: Dict[str, Any],
        source_preferences: Dict[str, Any],
    ) -> str:
        """
        Start a new provenance trace for context bundle assembly.

        Initializes comprehensive tracking of the entire context assembly
        process, including query parameters, source preferences, and
        execution context for complete lineage documentation.

        Args:
            bundle_id: Unique identifier for the context bundle
            query_context: Original query and context information
            source_preferences: User preferences for source selection

        Returns:
            Unique trace identifier for tracking
        """
        trace_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        with start_span("context_bundle.provenance_tracer.start_trace") as span:
            try:
                # Create initial provenance trace
                trace = ProvenanceTrace(
                    trace_id=trace_id,
                    bundle_id=bundle_id,
                    query_context=query_context,
                    source_attributions=[],
                    processing_graph=[],
                    confidence_lineage=ConfidencePropagation(
                        initial_confidence=1.0,
                        fusion_confidence=0.0,
                        temporal_adjustment=0.0,
                        diversity_penalty=0.0,
                        quality_filter_confidence=0.0,
                        final_confidence=0.0,
                        confidence_factors={},
                    ),
                    execution_timeline=[],
                    quality_metrics={},
                    created_at=start_time,
                )

                # Create initial query node
                query_node = ProvenanceNode(
                    node_id=str(uuid.uuid4()),
                    node_type="query",
                    timestamp=start_time,
                    operation="context_bundle_query",
                    input_ids=[],
                    output_ids=[],
                    metadata={
                        "query_context": query_context,
                        "source_preferences": source_preferences,
                    },
                    confidence=1.0,
                    processing_time_ms=0.0,
                )

                trace.processing_graph.append(query_node)
                trace.execution_timeline.append(
                    {
                        "timestamp": start_time.isoformat(),
                        "event": "trace_started",
                        "node_id": query_node.node_id,
                        "details": "Context bundle provenance tracking initiated",
                    }
                )

                # Store active trace
                self.active_traces[trace_id] = trace
                self.processing_nodes[trace_id] = [query_node]

                if span:
                    span.set_attribute("trace_id", trace_id)
                    span.set_attribute("bundle_id", bundle_id)
                    span.set_attribute(
                        "query_type", query_context.get("type", "unknown")
                    )

                logger.info(
                    "Provenance trace started",
                    extra={
                        "trace_id": trace_id,
                        "bundle_id": bundle_id,
                        "query_context": query_context,
                        "initial_node_id": query_node.node_id,
                    },
                )

                return trace_id

            except Exception as e:
                logger.error(
                    "Failed to start provenance trace",
                    extra={
                        "bundle_id": bundle_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))
                raise

    async def track_store_query(
        self,
        trace_id: str,
        store_name: str,
        query_parameters: Dict[str, Any],
        query_start_time: datetime,
        parent_node_id: str,
    ) -> str:
        """
        Track individual store query execution.

        Records detailed information about queries to specific storage
        systems, including timing, parameters, and relationship to the
        overall processing graph.

        Args:
            trace_id: Active trace identifier
            store_name: Name of the storage system being queried
            query_parameters: Parameters used for the query
            query_start_time: When the query was initiated
            parent_node_id: Parent node in the processing graph

        Returns:
            Node identifier for the store query
        """
        if trace_id not in self.active_traces:
            logger.warning(f"Trace {trace_id} not found for store query tracking")
            return ""

        node_id = str(uuid.uuid4())

        try:
            trace = self.active_traces[trace_id]

            # Create store query node
            store_node = ProvenanceNode(
                node_id=node_id,
                node_type="store",
                timestamp=query_start_time,
                operation=f"{store_name}_query",
                input_ids=[parent_node_id],
                output_ids=[],  # Will be populated when results arrive
                metadata={
                    "store_name": store_name,
                    "query_parameters": query_parameters,
                    "query_type": query_parameters.get("query_type", "unknown"),
                },
                confidence=1.0,  # Initial confidence
                processing_time_ms=0.0,  # Will be updated on completion
            )

            # Add to processing graph
            trace.processing_graph.append(store_node)
            self.processing_nodes[trace_id].append(store_node)

            # Add to execution timeline
            trace.execution_timeline.append(
                {
                    "timestamp": query_start_time.isoformat(),
                    "event": "store_query_started",
                    "node_id": node_id,
                    "store_name": store_name,
                    "details": f"Query initiated to {store_name}",
                }
            )

            logger.debug(
                "Store query tracked",
                extra={
                    "trace_id": trace_id,
                    "node_id": node_id,
                    "store_name": store_name,
                    "parent_node_id": parent_node_id,
                },
            )

            return node_id

        except Exception as e:
            logger.error(
                "Failed to track store query",
                extra={"trace_id": trace_id, "store_name": store_name, "error": str(e)},
            )
            return ""

    async def track_store_results(
        self,
        trace_id: str,
        store_node_id: str,
        results: List[Dict[str, Any]],
        processing_time_ms: float,
        success: bool,
        error_details: Optional[str] = None,
    ) -> None:
        """
        Track store query results and create source attributions.

        Records the results returned by individual storage systems and
        creates detailed source attribution records for provenance tracking.

        Args:
            trace_id: Active trace identifier
            store_node_id: Node ID for the store query
            results: Results returned by the store
            processing_time_ms: Time taken for query execution
            success: Whether the query was successful
            error_details: Error information if query failed
        """
        if trace_id not in self.active_traces:
            logger.warning(f"Trace {trace_id} not found for result tracking")
            return

        try:
            trace = self.active_traces[trace_id]
            completion_time = datetime.now(timezone.utc)

            # Find and update the store node
            store_node = None
            for node in self.processing_nodes[trace_id]:
                if node.node_id == store_node_id:
                    store_node = node
                    break

            if not store_node:
                logger.warning(f"Store node {store_node_id} not found")
                return

            # Update store node with results
            store_node.processing_time_ms = processing_time_ms
            result_ids = []

            if success and results:
                # Create source attributions for each result
                for i, result in enumerate(results):
                    result_id = str(uuid.uuid4())
                    result_ids.append(result_id)

                    attribution = SourceAttribution(
                        source_id=result_id,
                        source_type=store_node.metadata["store_name"],
                        source_path=result.get("source_path", f"result_{i}"),
                        confidence=result.get("confidence", 0.5),
                        contribution_weight=result.get("relevance_score", 0.5),
                        retrieval_timestamp=completion_time,
                        query_parameters=store_node.metadata["query_parameters"],
                        transformation_history=[],
                    )

                    trace.source_attributions.append(attribution)

                store_node.output_ids = result_ids
                store_node.confidence = sum(
                    r.get("confidence", 0.5) for r in results
                ) / len(results)
            else:
                store_node.confidence = 0.0
                store_node.metadata["error"] = error_details

            # Add to execution timeline
            trace.execution_timeline.append(
                {
                    "timestamp": completion_time.isoformat(),
                    "event": "store_query_completed",
                    "node_id": store_node_id,
                    "success": success,
                    "result_count": len(results) if results else 0,
                    "processing_time_ms": processing_time_ms,
                    "details": f"Store query completed with {len(results) if results else 0} results",
                }
            )

            logger.debug(
                "Store results tracked",
                extra={
                    "trace_id": trace_id,
                    "store_node_id": store_node_id,
                    "success": success,
                    "result_count": len(results) if results else 0,
                    "processing_time_ms": processing_time_ms,
                },
            )

        except Exception as e:
            logger.error(
                "Failed to track store results",
                extra={
                    "trace_id": trace_id,
                    "store_node_id": store_node_id,
                    "error": str(e),
                },
            )

    async def track_fusion_process(
        self,
        trace_id: str,
        fusion_strategy: Dict[str, Any],
        input_results: List[Dict[str, Any]],
        fused_results: List[Dict[str, Any]],
        fusion_metrics: Dict[str, Any],
        parent_node_ids: List[str],
    ) -> str:
        """
        Track result fusion process with detailed confidence propagation.

        Records the fusion of results from multiple stores, including
        strategy used, confidence changes, and quality transformations
        applied during the fusion process.

        Args:
            trace_id: Active trace identifier
            fusion_strategy: Strategy used for fusion
            input_results: Original results before fusion
            fused_results: Results after fusion processing
            fusion_metrics: Metrics from fusion process
            parent_node_ids: Input node IDs in processing graph

        Returns:
            Node identifier for the fusion process
        """
        if trace_id not in self.active_traces:
            logger.warning(f"Trace {trace_id} not found for fusion tracking")
            return ""

        node_id = str(uuid.uuid4())
        fusion_start_time = datetime.now(timezone.utc)

        try:
            trace = self.active_traces[trace_id]

            # Create fusion node
            fusion_node = ProvenanceNode(
                node_id=node_id,
                node_type="fusion",
                timestamp=fusion_start_time,
                operation="result_fusion",
                input_ids=parent_node_ids,
                output_ids=[],
                metadata={
                    "fusion_strategy": fusion_strategy,
                    "input_count": len(input_results),
                    "output_count": len(fused_results),
                    "fusion_metrics": fusion_metrics,
                },
                confidence=0.0,  # Will be calculated
                processing_time_ms=fusion_metrics.get("processing_time_ms", 0.0),
            )

            # Calculate confidence propagation
            if input_results and fused_results:
                input_confidence = sum(
                    r.get("confidence", 0.5) for r in input_results
                ) / len(input_results)
                output_confidence = sum(
                    r.get("confidence", 0.5) for r in fused_results
                ) / len(fused_results)

                trace.confidence_lineage.initial_confidence = input_confidence
                trace.confidence_lineage.fusion_confidence = output_confidence
                trace.confidence_lineage.confidence_factors.update(
                    {
                        "deduplication_impact": fusion_metrics.get(
                            "deduplication_removed", 0
                        ),
                        "diversity_applied": fusion_strategy.get(
                            "lambda_diversity", 0.0
                        ),
                        "quality_filtering": fusion_metrics.get("quality_scores", {}),
                    }
                )

                fusion_node.confidence = output_confidence

            # Track transformation history for source attributions
            for i, fused_result in enumerate(fused_results):
                # Find corresponding source attributions and update
                for attribution in trace.source_attributions:
                    if attribution.source_id in str(
                        fused_result.get("original_metadata", {})
                    ):
                        attribution.transformation_history.append(f"fusion_{node_id}")
                        attribution.confidence = fused_result.get(
                            "confidence", attribution.confidence
                        )

            # Update output IDs with fused result identifiers
            fusion_node.output_ids = [
                r.get("content_id", f"fused_{i}") for i, r in enumerate(fused_results)
            ]

            # Add to processing graph
            trace.processing_graph.append(fusion_node)
            self.processing_nodes[trace_id].append(fusion_node)

            # Add to execution timeline
            trace.execution_timeline.append(
                {
                    "timestamp": fusion_start_time.isoformat(),
                    "event": "fusion_completed",
                    "node_id": node_id,
                    "strategy": fusion_strategy.get("type", "unknown"),
                    "input_count": len(input_results),
                    "output_count": len(fused_results),
                    "details": f"Result fusion applied with {fusion_strategy.get('type', 'unknown')} strategy",
                }
            )

            logger.debug(
                "Fusion process tracked",
                extra={
                    "trace_id": trace_id,
                    "node_id": node_id,
                    "fusion_strategy": fusion_strategy.get("type", "unknown"),
                    "input_count": len(input_results),
                    "output_count": len(fused_results),
                },
            )

            return node_id

        except Exception as e:
            logger.error(
                "Failed to track fusion process",
                extra={"trace_id": trace_id, "error": str(e)},
            )
            return ""

    async def complete_trace(
        self,
        trace_id: str,
        final_results: List[Dict[str, Any]],
        overall_metrics: Dict[str, Any],
    ) -> Optional[ProvenanceTrace]:
        """
        Complete provenance trace and calculate final metrics.

        Finalizes the provenance trace with overall quality metrics,
        confidence assessment, and complete execution summary for
        audit and debugging purposes.

        Args:
            trace_id: Active trace identifier
            final_results: Final context bundle results
            overall_metrics: Overall processing metrics

        Returns:
            Complete provenance trace record
        """
        if trace_id not in self.active_traces:
            logger.warning(f"Trace {trace_id} not found for completion")
            return None

        completion_time = datetime.now(timezone.utc)

        try:
            trace = self.active_traces[trace_id]

            # Calculate final confidence
            if final_results:
                final_confidence = sum(
                    r.get("confidence", 0.5) for r in final_results
                ) / len(final_results)
                trace.confidence_lineage.final_confidence = final_confidence

            # Calculate quality metrics
            trace.quality_metrics = {
                "total_processing_time_ms": overall_metrics.get(
                    "processing_time_ms", 0.0
                ),
                "source_diversity": len(
                    set(attr.source_type for attr in trace.source_attributions)
                ),
                "result_count": len(final_results),
                "confidence_preservation": (
                    trace.confidence_lineage.final_confidence
                    / trace.confidence_lineage.initial_confidence
                    if trace.confidence_lineage.initial_confidence > 0
                    else 0.0
                ),
                "processing_efficiency": (
                    len(final_results) / len(trace.source_attributions)
                    if trace.source_attributions
                    else 0.0
                ),
            }

            # Add completion event to timeline
            trace.execution_timeline.append(
                {
                    "timestamp": completion_time.isoformat(),
                    "event": "trace_completed",
                    "node_id": "",
                    "final_result_count": len(final_results),
                    "total_sources": len(trace.source_attributions),
                    "details": "Provenance trace completed successfully",
                }
            )

            logger.info(
                "Provenance trace completed",
                extra={
                    "trace_id": trace_id,
                    "bundle_id": trace.bundle_id,
                    "final_result_count": len(final_results),
                    "source_count": len(trace.source_attributions),
                    "processing_nodes": len(trace.processing_graph),
                    "quality_metrics": trace.quality_metrics,
                },
            )

            return trace

        except Exception as e:
            logger.error(
                "Failed to complete provenance trace",
                extra={"trace_id": trace_id, "error": str(e)},
            )
            return None
        finally:
            # Clean up active trace
            if trace_id in self.active_traces:
                del self.active_traces[trace_id]
            if trace_id in self.processing_nodes:
                del self.processing_nodes[trace_id]

    async def get_trace_summary(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get concise summary of provenance trace."""

        if trace_id not in self.active_traces:
            return None

        trace = self.active_traces[trace_id]

        return {
            "trace_id": trace_id,
            "bundle_id": trace.bundle_id,
            "created_at": trace.created_at.isoformat(),
            "source_count": len(trace.source_attributions),
            "processing_nodes": len(trace.processing_graph),
            "current_confidence": trace.confidence_lineage.final_confidence,
            "quality_score": trace.quality_metrics.get("confidence_preservation", 0.0),
        }

    async def export_trace(
        self, trace_id: str, format_type: str = "json"
    ) -> Optional[str]:
        """Export complete provenance trace for external analysis."""

        if trace_id not in self.active_traces:
            return None

        trace = self.active_traces[trace_id]

        if format_type == "json":
            # Convert trace to JSON-serializable format
            trace_dict = asdict(trace)
            # Convert datetime objects to ISO strings
            trace_dict["created_at"] = trace.created_at.isoformat()
            for node in trace_dict["processing_graph"]:
                node["timestamp"] = (
                    node["timestamp"].isoformat()
                    if isinstance(node["timestamp"], datetime)
                    else node["timestamp"]
                )
            for attr in trace_dict["source_attributions"]:
                attr["retrieval_timestamp"] = (
                    attr["retrieval_timestamp"].isoformat()
                    if isinstance(attr["retrieval_timestamp"], datetime)
                    else attr["retrieval_timestamp"]
                )

            return json.dumps(trace_dict, indent=2)

        return None


# TODO: Production enhancements needed:
# - Implement persistent storage for provenance traces (database)
# - Add provenance trace compression for long-term storage
# - Implement provenance query and analysis capabilities
# - Add privacy-preserving provenance for sensitive data
# - Implement provenance-based confidence calibration
# - Add automated quality assessment based on provenance patterns
# - Implement provenance-guided result explanation generation
