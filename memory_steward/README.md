# memory_steward/ — Hippocampal Memory Formation Orchestration

**Version:** memory-steward @ 2025-09-16T00:00:00Z
**Scope:** Single, authoritative spec for the `memory_steward/` component in MemoryOS. Explains **why** it exists, **how** it orchestrates memory formation, the **envelopes** it consumes/produces, where it **fits** in the cognitive architecture, the **algorithms** behind hippocampal-inspired memory processing, and the **operational patterns** (UnitOfWork, redaction, deduplication). Written to be understandable and maintainable for decades.

---

## 0) Problem & Philosophy

**Problem.** MemoryOS receives memory write requests that need sophisticated orchestration: space resolution, content redaction, deduplication against existing memories, transactional commitment with outbox pattern, and audit trail generation. This requires coordinating multiple subsystems while maintaining ACID properties and cognitive coherence.

**Neuroscience inspiration.** The design abstracts the **hippocampus** as the memory formation hub that coordinates encoding, consolidation, and storage. The hippocampus receives convergent inputs from multiple cortical areas, performs pattern separation and completion, coordinates with policy systems (prefrontal cortex) for appropriate encoding, and manages the transition from temporary to permanent storage. Our Memory Steward mirrors these functions in a distributed system context.

**Philosophy.**
- **Hippocampal orchestration:** Central coordination of complex memory formation workflows
- **Transactional integrity:** ACID properties with UnitOfWork and outbox patterns
- **Policy-aware encoding:** Integration with redaction and access control systems
- **Content intelligence:** Deduplication and merge logic for semantic coherence
- **Audit transparency:** Complete provenance and receipt generation for all operations

---

## 1) Interfaces (Envelopes)

### 1.1 Input — Memory Write Request

> Emitted by **Attention Gate** after ADMIT decision for WriteIntent requests.

```json
{
  "request_id": "req-2025-09-16-0001",
  "actor": {"person_id": "alice", "role": "member", "device_id": "phone-123"},
  "space_id": "shared:household",
  "write_intent": {
    "content": "Had a great conversation with mom about the family reunion",
    "attachments": [{"type": "image", "url": "local://photo-123", "metadata": {}}],
    "context": {"location": "home", "activity": "call"},
    "temporal": {"occurred_at": "2025-09-16T14:30:00Z", "duration_minutes": 45}
  },
  "policy_obligations": ["mask:pii:phone_numbers", "redact:location:precise"],
  "salience": {"priority": 0.78, "urgency": 0.6, "novelty": 0.8},
  "trace_id": "trace-abc123",
  "version": "memory-steward:2025-09-16"
}
```

### 1.2 Output — Memory Formation Events

```json
{
  "memory_formation": {
    "event_id": "mem-2025-09-16-0001",
    "request_id": "req-2025-09-16-0001",
    "status": "committed",
    "memory_id": "memory-uuid-456",
    "space_id": "shared:household",
    "processing_stage": "committed",
    "deduplication": {
      "merged_with": ["memory-uuid-123"],
      "similarity_score": 0.85,
      "merge_strategy": "append_context"
    },
    "redaction_applied": ["phone_numbers", "precise_location"],
    "receipt_id": "receipt-789",
    "ts": "2025-09-16T14:35:00Z"
  },
  "cognitive_events": [
    {"topic": "cognitive.memory.write.initiated", "payload": {...}},
    {"topic": "cognitive.memory.write.space_resolved", "payload": {...}},
    {"topic": "cognitive.memory.write.redacted", "payload": {...}},
    {"topic": "cognitive.memory.write.committed", "payload": {...}}
  ]
}
```

### 1.3 Output — Memory Receipt & Audit Trail

```json
{
  "memory_receipt": {
    "receipt_id": "receipt-789",
    "memory_id": "memory-uuid-456",
    "actor": {"person_id": "alice", "device_id": "phone-123"},
    "space_id": "shared:household",
    "operation": "create",
    "content_hash": "sha256:abc123...",
    "policy_version": "2025-09-16",
    "redaction_applied": ["phone_numbers", "precise_location"],
    "provenance": {
      "source": "user_input",
      "confidence": 0.95,
      "processing_pipeline": ["space_resolution", "redaction", "deduplication", "encoding"]
    },
    "timestamp": "2025-09-16T14:35:00Z",
    "signature": "ecdsa:...",
    "mls_group_epoch": 42
  }
}
```

---

## 2) System Fit (MemoryOS Cognitive Architecture)

- **Attention Gate → Memory Steward:** ADMIT decisions for WriteIntent trigger orchestration workflow
- **Memory Steward → Storage:** Coordinates with BaseStore implementations for transactional writes
- **Memory Steward → Policy:** Integrates redaction_coordinator and space_policy for safe encoding
- **Memory Steward → Events:** Publishes cognitive events for downstream pipeline processing
- **Memory Steward → Outbox:** Uses reliable outbox pattern for event delivery guarantees
- **Memory Steward → Receipts:** Generates cryptographic receipts for audit and compliance

---

## 3) Hippocampal Processing Stages

### 3.1 Space Resolution (Dentate Gyrus Pattern Separation)

Determines target memory space based on context, actor permissions, and content analysis:

```python
def resolve_target_space(request, context):
    # Multi-factor space determination
    candidate_spaces = get_permitted_spaces(request.actor)
    content_hints = extract_space_hints(request.content)
    social_context = analyze_social_participants(request.content)

    # Pattern separation logic
    if explicit_space_hint:
        return validate_and_return(explicit_space_hint)
    elif social_context.indicates_shared:
        return select_shared_space(candidate_spaces, social_context)
    else:
        return request.actor.default_personal_space
```

### 3.2 Content Redaction (Policy Integration)

Coordinates with policy systems to apply appropriate data minimization:

```python
async def apply_redaction_coordination(content, obligations, space_context):
    redaction_plan = await redaction_coordinator.plan_redaction(
        content=content,
        obligations=obligations,
        space_policy=space_context.policy,
        actor_permissions=space_context.actor_permissions
    )

    redacted_content = await redaction_coordinator.execute_redaction(
        content=content,
        plan=redaction_plan
    )

    return redacted_content, redaction_plan.applied_redactions
```

### 3.3 Deduplication & Memory Consolidation (CA3 Pattern Completion)

Implements hippocampal pattern completion for similar memory integration:

```python
async def deduplicate_and_merge(new_memory, existing_memories):
    # Semantic similarity search
    similar_memories = await find_similar_memories(
        content=new_memory.content,
        space_id=new_memory.space_id,
        threshold=0.8,
        time_window_hours=168  # 1 week
    )

    if not similar_memories:
        return new_memory, []

    # Pattern completion decision
    best_match = max(similar_memories, key=lambda m: m.similarity_score)

    if best_match.similarity_score > 0.9:
        # High similarity - merge contexts
        merged_memory = merge_memory_contexts(best_match.memory, new_memory)
        return merged_memory, [best_match.memory.id]
    else:
        # Sufficient novelty - store separately but link
        new_memory.related_memories = [m.id for m in similar_memories]
        return new_memory, []
```

### 3.4 Transactional Commitment (CA1 Output)

Implements ACID transaction with outbox pattern for reliable event publishing:

```python
async def commit_memory_formation(memory, events, receipt):
    async with UnitOfWork() as uow:
        # Atomic transaction
        memory_id = await uow.memories.add(memory)
        receipt.memory_id = memory_id
        receipt_id = await uow.receipts.add(receipt)

        # Outbox pattern for reliable event delivery
        for event in events:
            await uow.outbox.add(OutboxEvent(
                topic=event.topic,
                payload=event.payload,
                trace_id=event.trace_id
            ))

        # Commit transaction
        await uow.commit()

        # Trigger outbox drainer
        await outbox_drainer.notify_new_events()

        return memory_id, receipt_id
```

---

## 4) Algorithms & Components

### 4.1 Memory Steward Orchestrator

Central coordination service that manages the complete memory formation workflow:

- **Input validation:** Schema and policy pre-checks
- **Workflow orchestration:** Coordinates all processing stages
- **Error handling:** Rollback and compensation for failed operations
- **Observability:** Comprehensive tracing and metrics

### 4.2 Space Resolver

Determines appropriate memory space based on content and context:

- **Permission analysis:** Actor capabilities and space membership
- **Content analysis:** Entity recognition and sharing hints
- **Social context:** Participant analysis and conversation scope
- **Default policies:** Fallback rules for ambiguous cases

### 4.3 Redaction Coordinator

Integrates with policy framework for content protection:

- **Obligation analysis:** Parses policy obligations into redaction plans
- **Content scanning:** Identifies PII and sensitive information
- **Redaction execution:** Applies data minimization transformations
- **Audit trail:** Records all redaction operations for compliance

### 4.4 Deduplication Engine

Implements semantic deduplication and memory consolidation:

- **Similarity search:** Vector-based content matching within time windows
- **Merge strategies:** Various approaches for combining similar memories
- **Pattern completion:** Hippocampal-inspired memory integration
- **Link maintenance:** Relationship tracking between related memories

### 4.5 Commit Manager

Handles transactional memory persistence with ACID guarantees:

- **UnitOfWork coordination:** Manages distributed transaction boundaries
- **Outbox implementation:** Reliable event publishing with delivery guarantees
- **Rollback handling:** Compensation logic for failed operations
- **Consistency checks:** Validates memory integrity before commitment

### 4.6 Receipt Generator

Creates cryptographic audit trails for all memory operations:

- **Content hashing:** SHA-256 fingerprints for integrity verification
- **Digital signatures:** ECDSA signatures for non-repudiation
- **Provenance tracking:** Complete processing history and metadata
- **MLS integration:** Group encryption epoch tracking for space isolation

---

## 5) Error Handling & Resilience

### 5.1 Compensation Patterns

When errors occur during memory formation, the system implements compensation:

- **Space resolution failure:** Fall back to actor's default personal space
- **Redaction failure:** Apply conservative redaction and flag for review
- **Deduplication failure:** Store memory without merging, log for manual review
- **Commit failure:** Full rollback with detailed error reporting

### 5.2 Circuit Breakers

Protect downstream systems from cascading failures:

- **Storage circuit breaker:** Prevent overload of memory stores
- **Policy circuit breaker:** Graceful degradation when policy systems are slow
- **Deduplication circuit breaker:** Skip similarity search under high load

### 5.3 Retry Strategies

Implement exponential backoff with jitter for transient failures:

- **Immediate retry:** Network blips and transient errors
- **Exponential backoff:** Systematic failures with increasing delays
- **Dead letter queue:** Permanent failures for manual intervention

---

## 6) Privacy & Security

### 6.1 Content Protection

- **Policy integration:** Mandatory redaction based on space policies and obligations
- **PII detection:** Automated scanning for personally identifiable information
- **Content hashing:** Secure fingerprinting without revealing content
- **MLS encryption:** Group-scoped encryption for space isolation

### 6.2 Audit Requirements

- **Complete provenance:** Full tracking of content transformations
- **Cryptographic receipts:** Non-repudiable audit trails
- **Policy compliance:** Documentation of all redaction and access control decisions
- **Retention management:** Lifecycle tracking for compliance requirements

---

## 7) Performance & Scaling

### 7.1 Processing Budgets

- **Deduplication limits:** Bounded similarity search to prevent performance degradation
- **Batch processing:** Group similar operations for efficiency
- **Async processing:** Non-blocking workflows with reactive patterns
- **Resource monitoring:** Track CPU, memory, and I/O usage

### 7.2 Optimization Strategies

- **Content caching:** Temporary caching of processing results
- **Similarity indexing:** Efficient vector search with approximate algorithms
- **Parallel processing:** Concurrent execution of independent operations
- **Load shedding:** Graceful degradation under extreme load

---

## 8) Implementation Files

```
memory_steward/
├── __init__.py                    # Module exports and version
├── orchestrator.py               # Main workflow coordination
├── space_resolver.py             # Target space determination
├── redaction_coordinator.py      # Policy-aware content protection
├── deduplication_engine.py       # Semantic similarity and merging
├── commit_manager.py             # Transactional persistence with UoW
├── receipt_generator.py          # Cryptographic audit trail creation
├── outbox_publisher.py           # Reliable event publishing
├── config/                       # Configuration files
│   ├── steward.yaml             # Service configuration
│   ├── deduplication.yaml       # Similarity thresholds and strategies
│   └── redaction.yaml           # Default redaction policies
└── tests/                        # Comprehensive test suite
    ├── test_orchestrator.py     # Workflow integration tests
    ├── test_space_resolver.py   # Space determination logic
    ├── test_redaction.py        # Content protection verification
    ├── test_deduplication.py    # Similarity and merging tests
    ├── test_commit_manager.py   # Transaction integrity tests
    └── test_receipt_generation.py # Audit trail validation
```

---

## 9) Observability & Metrics

### 9.1 Key Metrics

- `memory_formation_requests_total{status}` - Total formation attempts
- `memory_formation_duration_seconds` - End-to-end processing time
- `deduplication_similarity_score` - Distribution of similarity scores
- `redaction_operations_total{type}` - Count of redaction operations
- `space_resolution_decisions{strategy}` - Space determination outcomes

### 9.2 Distributed Tracing

All operations participate in distributed tracing with cognitive_trace_id correlation:

- **Span names:** `memory_steward.{component}.{operation}`
- **Span attributes:** space_id, actor_id, content_hash, similarity_scores
- **Error tracking:** Detailed error contexts and stack traces
- **Performance tracking:** Processing stage latencies and resource usage

---

## 10) Testing Strategy

### 10.1 Unit Tests

- **Component isolation:** Test each module independently with mocks
- **Edge cases:** Boundary conditions and error scenarios
- **Policy compliance:** Verify redaction and access control integration
- **Algorithm correctness:** Validate deduplication and merging logic

### 10.2 Integration Tests

- **End-to-end workflows:** Complete memory formation cycles
- **Error recovery:** Compensation and rollback scenarios
- **Performance:** Load testing and resource usage validation
- **Security:** Privacy and audit trail verification

---

**Stewardship:** The Memory Steward should remain the authoritative orchestrator for memory formation while maintaining clear interfaces with other cognitive components. Keep the hippocampal metaphor grounded in practical distributed systems patterns.
