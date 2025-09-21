# context_bundle/ — Hybrid Recall Assembly & Multi-Store Fusion

**Version:** context-bundle @ 2025-09-16T00:00:00Z
**Scope:** Single, authoritative spec for the `context_bundle/` component in MemoryOS. Explains **why** it exists, **how** it orchestrates hybrid recall assembly, the **envelopes** it consumes/produces, where it **fits** in the cognitive architecture, the **algorithms** behind multi-store coordination and result fusion, and the **operational patterns** (fanout queries, MMR diversification, provenance tracking). Written to be understandable and maintainable for decades.

---

## 0) Problem & Philosophy

**Problem.** MemoryOS needs to assemble rich, contextually relevant memory bundles from multiple heterogeneous storage systems (vector stores, knowledge graphs, full-text indices, episodic sequences). This requires coordinated parallel queries, intelligent result fusion, relevance diversification, provenance tracking, and performance budget enforcement—all while maintaining cognitive coherence and user expectations.

**Neuroscience inspiration.** The design abstracts **hippocampal-cortical recall loops** where the hippocampus coordinates retrieval across distributed cortical areas, assembles episodic context, and binds disparate memory traces into coherent conscious experiences. The hippocampus CA1 acts as a convergence zone that integrates pattern-completed outputs from CA3 with cortical inputs, creating rich contextual representations for working memory.

**Philosophy.**
- **Multi-store orchestration:** Coordinate parallel queries across heterogeneous memory systems
- **Contextual coherence:** Assemble meaningfully related content rather than isolated fragments
- **Relevance optimization:** Balance similarity with diversity for rich context assembly
- **Provenance transparency:** Track source attribution and confidence for all retrieved content
- **Performance discipline:** Enforce budgets and deadlines for responsive user experience

---

## 1) Interfaces (Envelopes)

### 1.1 Input — Context Assembly Request

> Emitted by **Attention Gate** after ADMIT decision for RecallIntent requests.

```json
{
  "request_id": "req-2025-09-16-0002",
  "actor": {"person_id": "alice", "role": "member", "device_id": "laptop-456"},
  "space_id": "shared:household",
  "recall_intent": {
    "query": "family vacation plans for next summer",
    "query_type": "semantic_search",
    "context_hints": {
      "temporal_scope": "future",
      "entities": ["family", "vacation", "summer"],
      "intent_categories": ["planning", "travel"]
    },
    "preferences": {
      "max_results": 20,
      "include_related": true,
      "temporal_weight": 0.7,
      "recency_bias": 0.3
    }
  },
  "budget": {
    "max_latency_ms": 800,
    "max_stores": 4,
    "max_results_per_store": 10
  },
  "policy_context": {
    "permitted_spaces": ["shared:household", "personal:alice"],
    "redaction_level": "minimal",
    "audit_required": true
  },
  "trace_id": "trace-def456",
  "version": "context-bundle:2025-09-16"
}
```

### 1.2 Output — Assembled Context Bundle

```json
{
  "context_bundle": {
    "bundle_id": "bundle-2025-09-16-0002",
    "request_id": "req-2025-09-16-0002",
    "query": "family vacation plans for next summer",
    "total_results": 18,
    "processing_time_ms": 650,
    "confidence": 0.82,
    "diversity_score": 0.75,
    "results": [
      {
        "content_id": "memory-uuid-789",
        "content": "Discussed potential Europe trip with family",
        "source_store": "episodic_memory",
        "relevance_score": 0.91,
        "temporal_context": "2025-08-15T19:30:00Z",
        "entities": ["Europe", "family", "trip"],
        "content_type": "conversation",
        "provenance": {
          "store_query_time_ms": 45,
          "original_similarity": 0.89,
          "mmr_adjusted_score": 0.91,
          "confidence": 0.88
        }
      }
    ],
    "store_coverage": {
      "episodic_memory": {"queried": true, "results": 6, "latency_ms": 120},
      "semantic_store": {"queried": true, "results": 8, "latency_ms": 180},
      "knowledge_graph": {"queried": true, "results": 3, "latency_ms": 95},
      "full_text_index": {"queried": true, "results": 1, "latency_ms": 60}
    },
    "fusion_metadata": {
      "strategy": "mmr_diversification",
      "lambda_diversity": 0.3,
      "temporal_boost_applied": true,
      "cross_store_deduplication": 2
    }
  }
}
```

### 1.3 Output — Cognitive Recall Events

```json
{
  "cognitive_events": [
    {"topic": "cognitive.recall.context.requested", "payload": {...}},
    {"topic": "cognitive.recall.stores.queried", "payload": {...}},
    {"topic": "cognitive.recall.results.fused", "payload": {...}},
    {"topic": "cognitive.recall.bundle.assembled", "payload": {...}}
  ]
}
```

### 1.4 Output — Provenance & Audit Trail

```json
{
  "recall_provenance": {
    "bundle_id": "bundle-2025-09-16-0002",
    "query_hash": "sha256:query_fingerprint",
    "store_queries": [
      {
        "store": "episodic_memory",
        "query_vector": [0.1, 0.2, ...],
        "query_params": {"k": 10, "threshold": 0.7},
        "results_count": 6,
        "max_similarity": 0.89,
        "query_latency_ms": 120
      }
    ],
    "fusion_decisions": {
      "mmr_iterations": 18,
      "diversity_lambda": 0.3,
      "deduplication_removed": 2,
      "temporal_boosts_applied": 5
    },
    "performance_budget": {
      "allocated_ms": 800,
      "used_ms": 650,
      "efficiency_ratio": 0.81
    },
    "timestamp": "2025-09-16T15:20:00Z"
  }
}
```

---

## 2) System Fit (MemoryOS Cognitive Architecture)

- **Attention Gate → Context Bundle:** ADMIT decisions for RecallIntent trigger assembly workflow
- **Context Bundle → Multiple Stores:** Coordinates parallel queries across vector, graph, text, and episodic stores
- **Context Bundle → Working Memory:** Provides assembled context for active cognitive processing
- **Context Bundle → Policy:** Integrates with access control and redaction for secure retrieval
- **Context Bundle → Events:** Publishes cognitive events for downstream processing and learning
- **Context Bundle → Observability:** Comprehensive performance and relevance tracking

---

## 3) Hippocampal-Cortical Recall Processing

### 3.1 Query Analysis & Store Selection (Hippocampal CA3 Pattern Completion)

Analyzes the incoming query to determine optimal store selection and query strategies:

```python
def analyze_query_and_select_stores(recall_intent, budget):
    # Query decomposition
    query_features = extract_query_features(recall_intent.query)
    semantic_complexity = assess_semantic_complexity(query_features)
    temporal_aspects = extract_temporal_context(recall_intent.context_hints)

    # Store selection based on query characteristics
    selected_stores = []

    if semantic_complexity.has_conceptual_content:
        selected_stores.append({
            "store": "semantic_store",
            "priority": 1.0,
            "query_type": "vector_similarity"
        })

    if temporal_aspects.has_episodic_markers:
        selected_stores.append({
            "store": "episodic_memory",
            "priority": 0.9,
            "query_type": "temporal_sequence"
        })

    if query_features.has_entity_references:
        selected_stores.append({
            "store": "knowledge_graph",
            "priority": 0.8,
            "query_type": "graph_traversal"
        })

    # Budget allocation across selected stores
    return allocate_budget_across_stores(selected_stores, budget)
```

### 3.2 Parallel Store Fanout (Distributed Cortical Activation)

Coordinates simultaneous queries across multiple memory stores with timeout management:

```python
async def execute_parallel_store_queries(query_plan, budget):
    query_tasks = []

    for store_config in query_plan.stores:
        task = asyncio.create_task(
            query_single_store(
                store=store_config.store,
                query=adapt_query_for_store(query_plan.query, store_config),
                budget=store_config.allocated_budget,
                timeout_ms=budget.max_latency_ms // 2
            )
        )
        query_tasks.append((store_config.store, task))

    # Wait for completion with timeout
    results = {}
    async with asyncio.timeout(budget.max_latency_ms / 1000):
        for store_name, task in query_tasks:
            try:
                store_results = await task
                results[store_name] = store_results
            except asyncio.TimeoutError:
                results[store_name] = StoreResult(
                    status="timeout",
                    results=[],
                    latency_ms=budget.max_latency_ms // 2
                )
            except Exception as e:
                results[store_name] = StoreResult(
                    status="error",
                    error=str(e),
                    results=[]
                )

    return results
```

### 3.3 Cross-Store Result Fusion (Hippocampal CA1 Integration)

Implements intelligent fusion of results from heterogeneous stores:

```python
def fuse_multi_store_results(store_results, fusion_strategy):
    # Normalize scores across different stores
    normalized_results = []
    for store_name, store_result in store_results.items():
        for result in store_result.results:
            normalized_result = normalize_store_result(
                result=result,
                store_type=store_name,
                store_characteristics=get_store_characteristics(store_name)
            )
            normalized_results.append(normalized_result)

    # Cross-store deduplication
    deduplicated_results = deduplicate_cross_store_results(
        normalized_results,
        similarity_threshold=0.85
    )

    # Apply fusion strategy (MMR, temporal weighting, etc.)
    if fusion_strategy.type == "mmr_diversification":
        fused_results = apply_mmr_diversification(
            deduplicated_results,
            lambda_diversity=fusion_strategy.lambda_diversity,
            max_results=fusion_strategy.max_results
        )
    elif fusion_strategy.type == "temporal_weighted":
        fused_results = apply_temporal_weighting(
            deduplicated_results,
            temporal_weight=fusion_strategy.temporal_weight,
            recency_bias=fusion_strategy.recency_bias
        )

    return fused_results
```

### 3.4 MMR Diversification (Maximal Marginal Relevance)

Implements cognitive diversification to provide rich, non-redundant context:

```python
def apply_mmr_diversification(candidates, lambda_diversity, max_results):
    """
    Maximal Marginal Relevance for balancing relevance with diversity.

    MMR(D) = argmax[d ∈ D] [λ * Rel(d,Q) - (1-λ) * max[d' ∈ S] Sim(d,d')]

    Where:
    - λ balances relevance vs diversity
    - Rel(d,Q) is relevance to query
    - Sim(d,d') is similarity between documents
    - S is already selected set
    """
    selected = []
    remaining = candidates[:]

    # Select highest relevance first
    if remaining:
        best_initial = max(remaining, key=lambda x: x.relevance_score)
        selected.append(best_initial)
        remaining.remove(best_initial)

    # Iteratively select based on MMR score
    while len(selected) < max_results and remaining:
        mmr_scores = []

        for candidate in remaining:
            relevance = candidate.relevance_score

            # Calculate maximum similarity to already selected
            max_similarity = 0
            for selected_doc in selected:
                similarity = calculate_semantic_similarity(
                    candidate.embedding,
                    selected_doc.embedding
                )
                max_similarity = max(max_similarity, similarity)

            # MMR formula
            mmr_score = (lambda_diversity * relevance -
                        (1 - lambda_diversity) * max_similarity)

            mmr_scores.append((candidate, mmr_score))

        # Select candidate with highest MMR score
        best_candidate, best_score = max(mmr_scores, key=lambda x: x[1])
        selected.append(best_candidate)
        remaining.remove(best_candidate)

    return selected
```

### 3.5 Provenance Tracking & Confidence Estimation

Maintains detailed source attribution and confidence modeling:

```python
def track_result_provenance(result, store_metadata, fusion_metadata):
    provenance = ResultProvenance(
        source_store=store_metadata.store_name,
        original_query=store_metadata.query,
        original_similarity=result.similarity_score,
        store_confidence=result.confidence,
        store_query_latency=store_metadata.latency_ms,

        # Fusion transformations
        mmr_adjusted_score=fusion_metadata.get("mmr_score"),
        diversity_penalty=fusion_metadata.get("diversity_penalty"),
        temporal_boost=fusion_metadata.get("temporal_boost"),

        # Overall confidence estimation
        final_confidence=estimate_final_confidence(result, fusion_metadata),

        # Audit trail
        processing_timestamp=datetime.utcnow(),
        bundle_id=fusion_metadata.bundle_id
    )

    return provenance

def estimate_final_confidence(result, fusion_metadata):
    """
    Estimate final confidence based on source confidence, fusion adjustments,
    and cross-store agreement.
    """
    base_confidence = result.confidence

    # Adjust for fusion penalties/boosts
    diversity_adjustment = 1.0 - fusion_metadata.get("diversity_penalty", 0)
    temporal_adjustment = 1.0 + fusion_metadata.get("temporal_boost", 0)

    # Cross-store agreement boost
    agreement_boost = fusion_metadata.get("cross_store_agreement", 0)

    final_confidence = (base_confidence *
                       diversity_adjustment *
                       temporal_adjustment *
                       (1 + agreement_boost))

    return min(final_confidence, 1.0)  # Cap at 1.0
```

---

## 4) Algorithms & Components

### 4.1 Context Bundle Orchestrator

Central coordination service for multi-store recall assembly:

- **Query planning:** Analyzes recall intent and selects optimal store strategies
- **Parallel coordination:** Manages concurrent store queries with timeout handling
- **Result integration:** Orchestrates fusion, deduplication, and diversification
- **Budget enforcement:** Ensures performance targets and resource limits

### 4.2 Store Fanout Manager

Handles parallel query distribution across heterogeneous stores:

- **Store adapters:** Translates generic queries into store-specific formats
- **Timeout management:** Handles partial results and graceful degradation
- **Error isolation:** Prevents single store failures from affecting others
- **Load balancing:** Distributes query load across available store instances

### 4.3 Result Fusion Engine

Implements sophisticated result combination strategies:

- **Score normalization:** Harmonizes similarity scores across different stores
- **Cross-store deduplication:** Identifies and merges duplicate content
- **MMR diversification:** Balances relevance with content diversity
- **Temporal weighting:** Applies time-based relevance adjustments

### 4.4 MMR Diversifier

Specialized component for Maximal Marginal Relevance computation:

- **Similarity calculation:** Computes semantic similarity between result pairs
- **Relevance optimization:** Balances query relevance with result diversity
- **Iterative selection:** Greedy algorithm for optimal result set assembly
- **Parameter tuning:** Adaptive lambda adjustment based on query characteristics

### 4.5 Provenance Tracer

Maintains comprehensive source attribution and confidence tracking:

- **Source tracking:** Records origin store and query parameters for each result
- **Confidence modeling:** Estimates reliability based on fusion transformations
- **Audit trails:** Maintains detailed processing history for compliance
- **Performance metrics:** Tracks latency and efficiency across processing stages

### 4.6 Budget Enforcer

Ensures responsive performance within specified resource constraints:

- **Latency budgets:** Enforces maximum response time limits
- **Store quotas:** Allocates query resources across selected stores
- **Graceful degradation:** Handles timeouts and partial results gracefully
- **Performance monitoring:** Tracks budget utilization and optimization opportunities

---

## 5) Performance Optimization

### 5.1 Query Optimization

- **Store selection heuristics:** Choose optimal stores based on query characteristics
- **Query adaptation:** Transform queries for maximum store efficiency
- **Parallel execution:** Maximize concurrency while respecting resource limits
- **Caching strategies:** Cache frequent query patterns and intermediate results

### 5.2 Result Processing Efficiency

- **Streaming fusion:** Process results as they arrive rather than batch processing
- **Early termination:** Stop processing when sufficient results are obtained
- **Similarity indexing:** Optimize cross-store deduplication with efficient algorithms
- **Memory management:** Minimize memory footprint for large result sets

### 5.3 Budget Management

- **Adaptive timeouts:** Adjust timeouts based on query complexity and historical performance
- **Resource allocation:** Dynamically distribute resources based on store performance
- **Quality vs. speed trade-offs:** Allow configuration of performance vs. quality preferences
- **Circuit breakers:** Protect against cascading failures in store systems

---

## 6) Error Handling & Resilience

### 6.1 Store Failure Handling

- **Graceful degradation:** Continue with available stores when some fail
- **Partial result assembly:** Create meaningful bundles from incomplete data
- **Error isolation:** Prevent store failures from affecting parallel queries
- **Retry strategies:** Implement exponential backoff for transient failures

### 6.2 Quality Assurance

- **Minimum result thresholds:** Ensure meaningful context even with failures
- **Confidence thresholds:** Filter low-confidence results to maintain quality
- **Coherence validation:** Verify assembled context makes semantic sense
- **Fallback strategies:** Provide alternative approaches when primary methods fail

---

## 7) Privacy & Security

### 7.1 Access Control Integration

- **Space-scoped queries:** Respect memory space boundaries and permissions
- **Result filtering:** Apply redaction and access controls to retrieved content
- **Audit requirements:** Log all access patterns for compliance monitoring
- **Secure aggregation:** Prevent information leakage through result patterns

### 7.2 Content Protection

- **Query redaction:** Remove sensitive information from query traces
- **Result anonymization:** Apply data minimization to retrieved content
- **Provenance privacy:** Protect source attribution when required
- **Cross-store isolation:** Prevent unauthorized information combination

---

## 8) Implementation Files

```
context_bundle/
├── __init__.py                    # Module exports and version
├── orchestrator.py               # Main recall assembly coordination
├── store_fanout.py               # Parallel store query management
├── result_fuser.py               # Multi-store result combination
├── mmr_diversifier.py            # Maximal Marginal Relevance implementation
├── provenance_tracer.py          # Source attribution and confidence tracking
├── budget_enforcer.py            # Performance budget management
├── adapters/                     # Store-specific query adapters
│   ├── vector_store_adapter.py  # Vector similarity store adapter
│   ├── graph_store_adapter.py   # Knowledge graph adapter
│   ├── text_index_adapter.py    # Full-text search adapter
│   └── episodic_store_adapter.py # Episodic sequence adapter
├── config/                       # Configuration files
│   ├── fusion.yaml              # Fusion strategy configuration
│   ├── stores.yaml              # Store connection and timeout settings
│   └── mmr.yaml                 # MMR diversification parameters
└── tests/                        # Comprehensive test suite
    ├── test_orchestrator.py     # Integration workflow tests
    ├── test_store_fanout.py     # Parallel query coordination tests
    ├── test_result_fusion.py    # Fusion algorithm validation
    ├── test_mmr_diversifier.py  # MMR algorithm correctness
    ├── test_provenance.py       # Source tracking verification
    └── test_budget_enforcement.py # Performance constraint tests
```

---

## 9) Observability & Metrics

### 9.1 Key Metrics

- `context_assembly_requests_total{status}` - Total assembly requests
- `context_assembly_duration_seconds` - End-to-end processing time
- `store_query_duration_seconds{store}` - Per-store query latency
- `result_fusion_diversity_score` - MMR diversification effectiveness
- `budget_utilization_ratio` - Performance budget efficiency

### 9.2 Distributed Tracing

- **Span names:** `context_bundle.{component}.{operation}`
- **Span attributes:** query_hash, store_coverage, fusion_strategy, diversity_score
- **Performance tracking:** Per-store latencies and fusion processing time
- **Quality tracking:** Confidence scores and relevance distributions

---

## 10) Testing Strategy

### 10.1 Algorithm Validation

- **MMR correctness:** Verify diversification algorithm produces expected results
- **Fusion quality:** Test result combination across different store types
- **Performance compliance:** Validate budget enforcement under various loads
- **Error resilience:** Test graceful degradation with store failures

### 10.2 Integration Testing

- **Multi-store coordination:** End-to-end testing with real store backends
- **Performance benchmarks:** Latency and throughput validation under load
- **Quality assessment:** Relevance and diversity metrics validation
- **Security compliance:** Access control and privacy protection verification

---

## 🎉 Implementation Status: 100% Complete

**Context Bundle Builder has achieved full implementation** with all architectural gaps resolved:

### ✅ **Completed Components (100%)**

1. **MMR Diversifier** (`mmr_diversifier.py`)
   - ✅ Classic, enhanced, and adaptive MMR algorithms
   - ✅ Multi-dimensional similarity computation (semantic, temporal, contextual, structural)
   - ✅ Adaptive parameter tuning based on query characteristics
   - ✅ Comprehensive quality metrics and performance tracking
   - ✅ Brain-inspired diversification mirroring hippocampal-cortical selection

2. **Enhanced Orchestrator** (`orchestrator.py`)
   - ✅ Integrated MMR diversification with quality thresholds (diversity > 0.4, relevance > 0.6)
   - ✅ Two-phase processing: fusion followed by diversification
   - ✅ Query-specific context adaptation with exploration/precision modes
   - ✅ Robust error handling with fallback to fusion results
   - ✅ Comprehensive observability and performance tracking

3. **Production-Ready Infrastructure**
   - ✅ Store Fanout Manager with parallel coordination
   - ✅ Result Fuser with intelligent combination strategies
   - ✅ Provenance Tracer with complete source tracking
   - ✅ Performance budget enforcement and graceful degradation

### 🚀 **Key Achievements**

- **Brain-Inspired Architecture**: Neuroscience-accurate hippocampal-cortical coordination
- **Sophisticated Algorithms**: MMR with adaptive optimization and quality thresholds
- **Production Quality**: Enterprise-grade error handling and performance optimization
- **Complete Integration**: Seamless connection to working memory and cognitive architecture
- **100% Feature Complete**: All identified architectural gaps resolved

### 📊 **Performance Characteristics**

- **Latency Budget**: 800ms max with 100ms buffer for responsive UX
- **Quality Assurance**: Diversity > 0.4, relevance > 0.6 thresholds for MMR acceptance
- **Parallel Processing**: Concurrent similarity computations with caching optimization
- **Graceful Degradation**: Fallback strategies for failed components or low-quality results

**This represents the completion of the final component needed to achieve 100% implementation across all architectural gaps identified in the comprehensive analysis.**

---

**Stewardship:** The Context Bundle system should remain the primary coordination point for multi-store recall while maintaining clear performance and quality guarantees. Keep the hippocampal-cortical metaphor grounded in practical distributed query optimization.
