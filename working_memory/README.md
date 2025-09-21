# working_memory/ — Active Context Management & Session Buffers

**Version:** working-memory @ 2025-09-16T00:00:00Z
**Scope:** Single, authoritative spec for the `working_memory/` component in MemoryOS. Explains **why** it exists, **how** it manages active context sessions, the **envelopes** it consumes/produces, where it **fits** in the cognitive architecture, the **algorithms** behind salience-based admission and priority-aware eviction, and the **operational patterns** (session tracking, cross-session correlation). Written to be understandable and maintainable for decades.

---

## 0) Problem & Philosophy

**Problem.** MemoryOS needs to maintain active, immediately accessible context for ongoing cognitive operations. Users engage in multi-turn conversations, maintain attention across tasks, and expect the system to "remember" what's currently relevant without repeatedly retrieving from long-term storage. This requires session-scoped buffers, intelligent admission control, priority-aware eviction, and efficient cross-session correlation.

**Neuroscience inspiration.** The design abstracts **working memory** as implemented by prefrontal cortex (PFC) circuits with dopaminergic modulation. Working memory maintains active representations for immediate cognitive operations, uses attention mechanisms for selective updating vs. maintenance, and implements capacity limits with intelligent priority-based competition. The system mirrors PFC-basal ganglia gating circuits that control what information enters, updates, or exits working memory buffers.

**Philosophy.**
- **Active context maintenance:** Keep immediately relevant information in fast-access buffers
- **Capacity-aware management:** Enforce realistic limits with intelligent eviction strategies
- **Salience-driven admission:** Prioritize important information for working memory entry
- **Session coherence:** Maintain context continuity within cognitive episodes
- **Cross-session correlation:** Track relationships between different interaction sessions

---

## 1) Interfaces (Envelopes)

### 1.1 Input — Working Memory Update Request

> Emitted by **Memory Steward**, **Context Bundle Builder**, and **Attention Gate** during cognitive operations.

```json
{
  "request_id": "wm-req-2025-09-16-0001",
  "actor": {"person_id": "alice", "device_id": "laptop-456"},
  "session_id": "session-uuid-789",
  "operation": "add",  // add | update | evict | refresh
  "content": {
    "item_id": "memory-uuid-123",
    "content_type": "memory_fragment",
    "content": "Family vacation planning discussion with mom",
    "entities": ["family", "vacation", "mom", "planning"],
    "temporal_context": "2025-09-16T14:30:00Z",
    "source": "context_bundle",
    "confidence": 0.85
  },
  "salience": {
    "relevance_score": 0.78,
    "urgency": 0.6,
    "recency": 0.9,
    "user_attention": 0.8,
    "contextual_importance": 0.7
  },
  "session_context": {
    "current_task": "planning",
    "conversation_turn": 5,
    "attention_focus": ["vacation", "family", "summer"],
    "active_duration_minutes": 12
  },
  "trace_id": "trace-ghi789",
  "version": "working-memory:2025-09-16"
}
```

### 1.2 Input — Session State Query

```json
{
  "query_id": "wm-query-2025-09-16-0001",
  "actor": {"person_id": "alice", "device_id": "laptop-456"},
  "session_id": "session-uuid-789",
  "query_type": "get_active_context",  // get_active_context | get_session_history | search_working_memory
  "filters": {
    "content_types": ["memory_fragment", "entity_reference"],
    "min_salience": 0.5,
    "time_window_minutes": 30,
    "max_results": 10
  },
  "trace_id": "trace-jkl012"
}
```

### 1.3 Output — Working Memory State Update

```json
{
  "working_memory_update": {
    "session_id": "session-uuid-789",
    "operation_result": "added",
    "item_id": "memory-uuid-123",
    "current_capacity": {
      "items_count": 8,
      "max_capacity": 12,
      "utilization_ratio": 0.67
    },
    "eviction_occurred": false,
    "evicted_items": [],
    "admission_decision": {
      "admitted": true,
      "salience_threshold": 0.55,
      "item_salience": 0.78,
      "reasons": ["high_relevance", "recent_access", "user_attention"]
    },
    "updated_session_context": {
      "dominant_themes": ["vacation", "family", "planning"],
      "attention_focus_strength": 0.82,
      "session_coherence": 0.79
    }
  }
}
```

### 1.4 Output — Active Context Bundle

```json
{
  "active_context": {
    "session_id": "session-uuid-789",
    "actor": {"person_id": "alice"},
    "items": [
      {
        "item_id": "memory-uuid-123",
        "content": "Family vacation planning discussion with mom",
        "salience": 0.78,
        "admission_time": "2025-09-16T14:30:00Z",
        "last_access": "2025-09-16T14:35:00Z",
        "access_count": 3,
        "entities": ["family", "vacation", "mom", "planning"],
        "source": "context_bundle",
        "confidence": 0.85,
        "priority_rank": 2
      }
    ],
    "session_metadata": {
      "session_start": "2025-09-16T14:18:00Z",
      "last_activity": "2025-09-16T14:35:00Z",
      "total_items_processed": 15,
      "current_items": 8,
      "dominant_themes": ["vacation", "family", "planning"],
      "coherence_score": 0.79
    },
    "cross_session_links": [
      {
        "related_session": "session-uuid-456",
        "relationship": "continuation",
        "similarity": 0.83,
        "shared_entities": ["vacation", "family"]
      }
    ]
  }
}
```

### 1.5 Output — Cognitive Working Memory Events

```json
{
  "cognitive_events": [
    {"topic": "cognitive.working_memory.updated", "payload": {...}},
    {"topic": "cognitive.working_memory.evicted", "payload": {...}},
    {"topic": "cognitive.working_memory.session.started", "payload": {...}},
    {"topic": "cognitive.working_memory.session.ended", "payload": {...}}
  ]
}
```

---

## 2) System Fit (MemoryOS Cognitive Architecture)

- **Attention Gate → Working Memory:** High-salience admitted content enters working memory buffers
- **Context Bundle → Working Memory:** Recalled context is made available for immediate access
- **Memory Steward → Working Memory:** Newly formed memories are cached for continued relevance
- **Working Memory → All Cognitive Components:** Provides fast access to active context
- **Working Memory → Events:** Publishes state changes for downstream cognitive processing
- **Working Memory → Observability:** Tracks attention patterns and cognitive load

---

## 3) Prefrontal Working Memory Processing

### 3.1 Salience-Based Admission Control (PFC Gating)

Implements attention-modulated gating for working memory entry:

```python
def evaluate_admission(item, current_context, session_state):
    """
    PFC-inspired gating decision for working memory admission.
    Based on salience, capacity, and contextual relevance.
    """
    # Base salience computation
    relevance = compute_contextual_relevance(item, current_context)
    urgency = extract_urgency_signals(item)
    recency = calculate_temporal_recency(item)
    attention = measure_user_attention_alignment(item, session_state)

    # Weighted salience score
    salience = (0.4 * relevance +
                0.2 * urgency +
                0.2 * recency +
                0.2 * attention)

    # Contextual modulation (PFC top-down control)
    task_relevance = assess_task_relevance(item, session_state.current_task)
    coherence_boost = calculate_coherence_boost(item, current_context)

    # Final admission score
    admission_score = salience * (1 + 0.3 * task_relevance + 0.2 * coherence_boost)

    # Capacity-dependent threshold adjustment
    capacity_pressure = session_state.utilization_ratio
    dynamic_threshold = base_threshold * (1 + capacity_pressure * 0.5)

    return AdmissionDecision(
        admit=admission_score > dynamic_threshold,
        score=admission_score,
        threshold=dynamic_threshold,
        reasons=generate_admission_reasons(relevance, urgency, recency, attention)
    )
```

### 3.2 Priority-Aware LRU Eviction (Dopaminergic Modulation)

Implements intelligent eviction with priority and access pattern consideration:

```python
def select_eviction_candidates(working_memory, capacity_limit):
    """
    Priority-aware LRU eviction with dopaminergic-inspired modulation.
    Combines recency with importance and access patterns.
    """
    if len(working_memory.items) <= capacity_limit:
        return []

    # Calculate eviction scores for all items
    eviction_candidates = []
    current_time = datetime.utcnow()

    for item in working_memory.items:
        # Recency factors (inverse relationship - older = higher eviction score)
        time_since_access = (current_time - item.last_access).total_seconds()
        time_since_admission = (current_time - item.admission_time).total_seconds()

        # Access pattern factors
        access_frequency = item.access_count / time_since_admission * 3600  # per hour
        access_recency_weight = 1.0 / (1.0 + time_since_access / 300)  # 5-min decay

        # Importance factors (inverse relationship - more important = lower eviction score)
        salience_protection = 1.0 - item.salience  # High salience protects from eviction
        confidence_protection = 1.0 - item.confidence

        # Contextual factors
        theme_alignment = calculate_theme_alignment(item, working_memory.dominant_themes)
        coherence_contribution = assess_coherence_contribution(item, working_memory.items)

        # Combined eviction score (higher = more likely to evict)
        eviction_score = (
            0.3 * (time_since_access / 3600) +  # Hours since last access
            0.2 * (time_since_admission / 3600) +  # Hours since admission
            0.2 * salience_protection +  # Inverse salience protection
            0.1 * confidence_protection +  # Inverse confidence protection
            0.1 * (1.0 - access_frequency / 10) +  # Inverse access frequency
            0.05 * (1.0 - theme_alignment) +  # Inverse theme alignment
            0.05 * (1.0 - coherence_contribution)  # Inverse coherence contribution
        )

        eviction_candidates.append((item, eviction_score))

    # Sort by eviction score (highest first) and select excess items
    eviction_candidates.sort(key=lambda x: x[1], reverse=True)
    items_to_evict = len(working_memory.items) - capacity_limit

    return [item for item, score in eviction_candidates[:items_to_evict]]
```

### 3.3 Session Coherence Tracking

Maintains coherence and thematic consistency within working memory sessions:

```python
def update_session_coherence(session, new_item=None, evicted_items=None):
    """
    Track session coherence based on thematic consistency and entity overlap.
    """
    if not session.items:
        return SessionCoherence(score=1.0, themes=[], entity_graph={})

    # Extract entities and themes from all active items
    all_entities = []
    all_themes = []

    for item in session.items:
        all_entities.extend(item.entities)
        all_themes.extend(extract_themes(item.content))

    # Calculate entity co-occurrence patterns
    entity_graph = build_entity_cooccurrence_graph(all_entities)

    # Identify dominant themes
    theme_frequencies = Counter(all_themes)
    dominant_themes = [theme for theme, count in theme_frequencies.most_common(5)]

    # Calculate coherence score
    thematic_coherence = calculate_thematic_coherence(all_themes)
    entity_coherence = calculate_entity_coherence(entity_graph)
    temporal_coherence = calculate_temporal_coherence(session.items)

    overall_coherence = (0.4 * thematic_coherence +
                        0.3 * entity_coherence +
                        0.3 * temporal_coherence)

    return SessionCoherence(
        score=overall_coherence,
        dominant_themes=dominant_themes,
        entity_graph=entity_graph,
        thematic_coherence=thematic_coherence,
        entity_coherence=entity_coherence,
        temporal_coherence=temporal_coherence
    )
```

### 3.4 Cross-Session Correlation

Tracks relationships between different working memory sessions:

```python
def correlate_sessions(current_session, historical_sessions, max_lookback_hours=24):
    """
    Identify relationships between current and recent sessions.
    """
    correlations = []
    current_time = datetime.utcnow()

    for historical_session in historical_sessions:
        # Skip sessions outside lookback window
        time_delta = current_time - historical_session.end_time
        if time_delta.total_seconds() > max_lookback_hours * 3600:
            continue

        # Calculate various similarity metrics
        entity_overlap = calculate_entity_overlap(
            current_session.all_entities,
            historical_session.all_entities
        )

        theme_similarity = calculate_theme_similarity(
            current_session.dominant_themes,
            historical_session.dominant_themes
        )

        temporal_proximity = calculate_temporal_proximity(
            current_session.start_time,
            historical_session.end_time
        )

        content_similarity = calculate_semantic_similarity(
            current_session.content_embeddings,
            historical_session.content_embeddings
        )

        # Combined correlation score
        correlation_score = (0.3 * entity_overlap +
                           0.3 * theme_similarity +
                           0.2 * content_similarity +
                           0.2 * temporal_proximity)

        if correlation_score > 0.3:  # Threshold for meaningful correlation
            relationship_type = classify_session_relationship(
                entity_overlap, theme_similarity, temporal_proximity
            )

            correlations.append(SessionCorrelation(
                session_id=historical_session.id,
                correlation_score=correlation_score,
                relationship_type=relationship_type,
                shared_entities=get_shared_entities(current_session, historical_session),
                shared_themes=get_shared_themes(current_session, historical_session)
            ))

    return sorted(correlations, key=lambda x: x.correlation_score, reverse=True)
```

---

## 4) Algorithms & Components

### 4.1 Working Memory Manager

Central coordination service for active context management:

- **Session lifecycle:** Creates, maintains, and terminates working memory sessions
- **Capacity management:** Enforces memory limits with intelligent eviction
- **State synchronization:** Maintains consistency across concurrent access
- **Performance optimization:** Fast access patterns for active context

### 4.2 Admission Controller

Implements salience-based gating for working memory entry:

- **Salience computation:** Multi-factor scoring for admission decisions
- **Contextual relevance:** Assessment of fit with current session context
- **Capacity-aware thresholds:** Dynamic admission criteria based on memory pressure
- **Policy integration:** Respects access control and privacy constraints

### 4.3 LRU Eviction Engine

Manages capacity constraints with priority-aware eviction:

- **Priority calculation:** Multi-dimensional scoring for eviction decisions
- **Access pattern analysis:** Considers frequency and recency of access
- **Coherence preservation:** Protects items critical for session coherence
- **Graceful degradation:** Maintains core context under memory pressure

### 4.4 Cross-Session Tracker

Maintains relationships between different working memory sessions:

- **Session correlation:** Identifies related sessions based on content and timing
- **Relationship classification:** Categorizes session relationships (continuation, related, etc.)
- **Entity tracking:** Maintains entity persistence across session boundaries
- **Context bridging:** Facilitates context transfer between related sessions

### 4.5 Session State Monitor

Tracks and analyzes working memory session characteristics:

- **Coherence tracking:** Monitors thematic and entity consistency
- **Attention patterns:** Analyzes user focus and engagement signals
- **Performance metrics:** Tracks access patterns and memory utilization
- **Quality assessment:** Evaluates effectiveness of working memory management

---

## 5) Performance & Scaling

### 5.1 Memory Efficiency

- **Capacity limits:** Enforce realistic working memory bounds (7±2 chunks)
- **Reference management:** Use content references rather than full duplication
- **Compression strategies:** Compact inactive content while preserving accessibility
- **Memory pooling:** Efficient allocation and reuse of memory structures

### 5.2 Access Optimization

- **Cache-friendly access:** Optimize for temporal and spatial locality
- **Index structures:** Fast lookup by session, entity, and content type
- **Lazy loading:** Load full content only when accessed
- **Prefetching:** Anticipate access patterns for common operations

### 5.3 Concurrency Management

- **Session isolation:** Prevent cross-session interference
- **Lock-free access:** Use atomic operations for high-frequency operations
- **Read optimization:** Optimize for read-heavy access patterns
- **Batch updates:** Group related modifications for efficiency

---

## 6) Error Handling & Resilience

### 6.1 Capacity Management

- **Graceful degradation:** Maintain core functionality under memory pressure
- **Emergency eviction:** Force eviction when hard limits are reached
- **Quality preservation:** Protect high-value content during capacity crises
- **Recovery strategies:** Rebuild working memory from persistent state when needed

### 6.2 Session Recovery

- **State persistence:** Periodically checkpoint session state for recovery
- **Crash recovery:** Restore working memory sessions after system restart
- **Corruption detection:** Validate session integrity and recover from corruption
- **Partial recovery:** Maintain partial context when full recovery is impossible

---

## 7) Privacy & Security

### 7.1 Session Isolation

- **Actor-scoped sessions:** Prevent cross-user information leakage
- **Device boundaries:** Respect device-specific session isolation
- **Space inheritance:** Apply memory space access controls to working memory
- **Audit trails:** Log working memory access for security monitoring

### 7.2 Content Protection

- **Redaction awareness:** Respect redaction requirements in working memory
- **Temporary storage:** Ensure working memory content doesn't persist inappropriately
- **Secure eviction:** Securely clear evicted content from memory
- **Access logging:** Track all working memory access for compliance

---

## 8) Implementation Files

```
working_memory/
├── __init__.py                    # Module exports and version
├── manager.py                    # Main working memory coordination
├── admission_controller.py       # Salience-based admission gating
├── lru_eviction.py               # Priority-aware capacity management
├── cross_session_tracker.py      # Session relationship tracking
├── session_monitor.py            # Session state and performance monitoring
├── coherence_tracker.py          # Session coherence and thematic analysis
├── models/                       # Data models and structures
│   ├── session.py               # Working memory session model
│   ├── items.py                 # Working memory item structures
│   ├── coherence.py             # Coherence and correlation models
│   └── events.py                # Working memory event definitions
├── config/                       # Configuration files
│   ├── capacity.yaml            # Memory capacity and limits
│   ├── admission.yaml           # Admission control parameters
│   ├── eviction.yaml            # Eviction strategy configuration
│   └── correlation.yaml         # Cross-session correlation settings
└── tests/                        # Comprehensive test suite
    ├── test_manager.py          # Core manager functionality
    ├── test_admission.py        # Admission control validation
    ├── test_eviction.py         # Eviction algorithm correctness
    ├── test_correlation.py      # Cross-session correlation tests
    ├── test_coherence.py        # Session coherence tracking
    └── test_performance.py      # Performance and capacity tests
```

---

## 9) Observability & Metrics

### 9.1 Key Metrics

- `working_memory_items_total{session_type}` - Active working memory items
- `working_memory_admission_decisions{outcome}` - Admission accept/reject rates
- `working_memory_evictions_total{reason}` - Eviction events by reason
- `working_memory_capacity_utilization` - Memory utilization ratios
- `working_memory_session_coherence` - Session coherence scores

### 9.2 Cognitive Insights

- **Attention patterns:** Track user focus and engagement through working memory access
- **Cognitive load:** Monitor working memory pressure as cognitive load indicator
- **Context switching:** Analyze session transitions and context preservation
- **Memory effectiveness:** Measure working memory contribution to task completion

---

## 10) Testing Strategy

### 10.1 Cognitive Algorithm Validation

- **Admission accuracy:** Verify salience-based admission produces relevant selections
- **Eviction quality:** Test that eviction preserves important context
- **Coherence maintenance:** Validate session coherence tracking accuracy
- **Correlation detection:** Test cross-session relationship identification

### 10.2 Performance & Capacity Testing

- **Capacity compliance:** Verify working memory respects configured limits
- **Access performance:** Validate fast access to working memory content
- **Eviction efficiency:** Test eviction performance under various load conditions
- **Session scalability:** Validate performance with large numbers of concurrent sessions

---

**Stewardship:** Working Memory should remain the fast-access cognitive buffer while maintaining realistic capacity constraints and intelligent content management. Keep the prefrontal cortex metaphor grounded in practical session management and attention modeling.
