# Cross-Store Coordination Protocols

## Overview

The Cross-Store Coordination system provides comprehensive distributed coordination mechanisms for MemoryOS Storage service. This document defines the protocols, algorithms, and implementation patterns for ensuring consistency, resolving conflicts, and coordinating operations across multiple storage stores.

## Coordination Patterns

### 1. Two-Phase Commit (2PC) Protocol

The 2PC protocol ensures ACID properties for distributed transactions across multiple stores.

#### Protocol Flow

```
Coordinator                 Participant 1              Participant 2
    |                           |                          |
    |---- PREPARE(txn_id) ----->|                          |
    |---- PREPARE(txn_id) ----------------------------->|
    |                           |                          |
    |<--- VOTE-COMMIT -----------|                          |
    |<--- VOTE-COMMIT ------------------------------|
    |                           |                          |
    |---- COMMIT(txn_id) ------->|                          |
    |---- COMMIT(txn_id) ------------------------------>|
    |                           |                          |
    |<--- ACK -------------------|                          |
    |<--- ACK -----------------------------|
    |                           |                          |
```

#### Implementation Contract

```yaml
two_phase_commit:
  coordinator:
    responsibilities:
      - Initiate transaction with all participants
      - Send PREPARE messages to all participants
      - Collect votes from all participants
      - Make commit/abort decision based on votes
      - Send COMMIT/ABORT to all participants
      - Handle coordinator failure recovery

    timeouts:
      prepare_timeout: 30s
      commit_timeout: 60s
      participant_response_timeout: 10s

    failure_handling:
      coordinator_failure: "Participants timeout and abort"
      participant_failure: "Coordinator aborts transaction"
      network_partition: "Abort transaction to maintain consistency"

  participant:
    responsibilities:
      - Prepare transaction resources (acquire locks, validate)
      - Vote COMMIT if can guarantee transaction completion
      - Vote ABORT if cannot guarantee completion
      - Execute COMMIT/ABORT based on coordinator decision
      - Release resources after completion

    voting_criteria:
      vote_commit_conditions:
        - All constraints satisfied
        - All locks acquired successfully
        - Sufficient resources available
        - No conflicts detected

      vote_abort_conditions:
        - Constraint violations detected
        - Lock acquisition failed
        - Resource exhaustion
        - Data conflicts present

    state_persistence:
      prepare_log: "Persist PREPARED state before voting"
      commit_log: "Persist COMMITTED state before acknowledging"
      abort_log: "Persist ABORTED state for cleanup"
```

### 2. Saga Pattern for Long-Running Transactions

For operations that span multiple stores and may take extended time, the Saga pattern provides eventual consistency with compensation.

#### Saga Implementation

```yaml
saga_pattern:
  coordination_types:
    choreography:
      description: "Event-driven coordination without central coordinator"
      pros: ["Loose coupling", "High availability", "Scalability"]
      cons: ["Complex debugging", "Eventual consistency only"]

    orchestration:
      description: "Central orchestrator manages saga execution"
      pros: ["Centralized control", "Easier monitoring", "Clear error handling"]
      cons: ["Single point of failure", "Tight coupling"]

  saga_step_definition:
    forward_operation:
      store: "EpisodicStore"
      operation: "insert_episode"
      parameters:
        episode_id: "{{saga.episode_id}}"
        content: "{{saga.episode_content}}"
      timeout: 30s
      idempotency_key: "{{saga.saga_id}}_step_{{step.step_id}}"

    compensation_operation:
      store: "EpisodicStore"
      operation: "delete_episode"
      parameters:
        episode_id: "{{saga.episode_id}}"
      timeout: 15s
      idempotency_key: "{{saga.saga_id}}_comp_{{step.step_id}}"

    retry_policy:
      max_attempts: 3
      backoff_strategy: "exponential"
      base_delay: 1s
      max_delay: 30s

  saga_execution_states:
    - "created"        # Saga definition created
    - "started"        # Saga execution began
    - "step_executing" # Individual step executing
    - "step_completed" # Step completed successfully
    - "step_failed"    # Step failed, may retry
    - "compensating"   # Running compensation operations
    - "completed"      # All steps completed successfully
    - "aborted"        # Saga aborted due to failures
    - "failed"         # Saga failed with unrecoverable error
```

### 3. Event Sourcing Coordination

For eventually consistent operations where event ordering matters.

#### Event Coordination Protocol

```yaml
event_sourcing_coordination:
  event_ordering:
    strategy: "logical_timestamps"
    implementation: "vector_clocks"
    conflict_resolution: "application_defined"

  event_stream_coordination:
    partitioning_strategy:
      type: "aggregate_id_hash"
      partition_count: 24
      partition_assignment: "consistent_hashing"

    ordering_guarantees:
      per_aggregate: "total_order"
      cross_aggregate: "partial_order"
      global: "causal_consistency"

  coordination_events:
    - type: "COORDINATION_STARTED"
      payload:
        coordination_id: "coord_{{uuid}}"
        participating_stores: ["EpisodicStore", "SemanticStore"]
        coordination_type: "event_sourcing"
        started_at: "{{timestamp}}"

    - type: "COORDINATION_CHECKPOINT"
      payload:
        coordination_id: "coord_{{uuid}}"
        checkpoint_id: "ckpt_{{sequence}}"
        processed_events_count: "{{count}}"
        last_event_timestamp: "{{timestamp}}"

    - type: "COORDINATION_COMPLETED"
      payload:
        coordination_id: "coord_{{uuid}}"
        total_events_processed: "{{count}}"
        duration_ms: "{{duration}}"
        completed_at: "{{timestamp}}"
```

## Consistency Protocols

### 1. Strong Consistency Validation

```yaml
strong_consistency:
  validation_rules:
    referential_integrity:
      - rule_id: "episodic_semantic_reference"
        description: "Every episode must have corresponding semantic nodes"
        source_store: "EpisodicStore"
        target_store: "SemanticStore"
        validation_query: |
          SELECT e.episode_id
          FROM episodic.episodes e
          LEFT JOIN semantic.nodes s ON e.episode_id = s.episode_id
          WHERE s.episode_id IS NULL
        severity: "critical"
        auto_repair: false

      - rule_id: "receipt_transaction_reference"
        description: "Every receipt must reference valid transaction"
        source_store: "ReceiptsStore"
        target_store: "EpisodicStore"
        validation_query: |
          SELECT r.receipt_id
          FROM receipts.transaction_receipts r
          LEFT JOIN episodic.transactions t ON r.transaction_id = t.transaction_id
          WHERE t.transaction_id IS NULL
        severity: "high"
        auto_repair: true

    temporal_ordering:
      - rule_id: "episode_temporal_order"
        description: "Episode timestamps must be monotonically increasing"
        stores: ["EpisodicStore"]
        validation_logic: |
          Check that for each user_id:
          episodes.created_at[i] < episodes.created_at[i+1]
        severity: "medium"
        auto_repair: false

    data_duplication:
      - rule_id: "unique_episode_content_hash"
        description: "Episode content hashes must be unique"
        stores: ["EpisodicStore"]
        validation_query: |
          SELECT content_hash, COUNT(*) as duplicate_count
          FROM episodic.episodes
          GROUP BY content_hash
          HAVING COUNT(*) > 1
        severity: "low"
        auto_repair: true
        repair_strategy: "merge_duplicates"

  validation_scheduling:
    full_validation:
      frequency: "daily"
      time: "02:00 UTC"
      parallelism: 4
      timeout: "2 hours"

    incremental_validation:
      frequency: "every_15_minutes"
      window: "last_30_minutes"
      parallelism: 2
      timeout: "5 minutes"

    real_time_validation:
      trigger: "on_transaction_commit"
      scope: "affected_entities_only"
      timeout: "10 seconds"
```

### 2. Eventual Consistency Management

```yaml
eventual_consistency:
  convergence_strategies:
    conflict_free_replicated_data_types:
      - type: "G_Counter"
        use_case: "Event counters across stores"
        stores: ["MetricsStore", "ObservabilityStore"]
        merge_function: "max(local_count, remote_count)"

      - type: "LWW_Register"
        use_case: "Configuration updates"
        stores: ["ConfigStore", "CacheStore"]
        merge_function: "last_writer_wins_by_timestamp"

      - type: "OR_Set"
        use_case: "Tag collections"
        stores: ["EpisodicStore", "SemanticStore"]
        merge_function: "union_with_tombstones"

    anti_entropy_protocols:
      merkle_tree_sync:
        frequency: "hourly"
        tree_depth: 8
        hash_algorithm: "sha256"
        comparison_granularity: "1000_records"

      gossip_protocol:
        gossip_interval: "30s"
        fanout: 3
        gossip_payload_max_size: "64KB"
        suspicion_timeout: "60s"

  conflict_resolution:
    resolution_strategies:
      - strategy: "last_writer_wins"
        applicability: "Configuration and metadata updates"
        implementation: "Compare timestamps and use most recent"
        risks: "May lose concurrent updates"

      - strategy: "application_merge"
        applicability: "Complex data structures"
        implementation: "Custom merge logic per data type"
        risks: "Requires domain-specific knowledge"

      - strategy: "manual_intervention"
        applicability: "Critical data conflicts"
        implementation: "Flag for human review"
        risks: "Delays resolution"

    conflict_detection:
      vector_clocks:
        enabled: true
        max_actors: 100
        clock_increment: "on_write"
        compaction_threshold: 1000

      checksums:
        algorithm: "sha256"
        granularity: "per_record"
        storage: "in_metadata"
        verification_frequency: "on_read"
```

## Distributed Locking

### 1. Lock Coordination Protocol

```yaml
distributed_locking:
  lock_manager:
    consensus_algorithm: "raft"
    leader_election: "automatic"
    lease_duration: "30s"
    heartbeat_interval: "5s"

  lock_types:
    exclusive_lock:
      description: "Full exclusive access to resource"
      compatibility_matrix:
        exclusive: false
        shared: false
        intent_exclusive: false
        intent_shared: false

    shared_lock:
      description: "Shared read access to resource"
      compatibility_matrix:
        exclusive: false
        shared: true
        intent_exclusive: false
        intent_shared: true

    intent_exclusive:
      description: "Intent to acquire exclusive lock on child resources"
      compatibility_matrix:
        exclusive: false
        shared: false
        intent_exclusive: true
        intent_shared: true

    intent_shared:
      description: "Intent to acquire shared lock on child resources"
      compatibility_matrix:
        exclusive: false
        shared: true
        intent_exclusive: true
        intent_shared: true

  deadlock_detection:
    algorithm: "wait_for_graph"
    detection_interval: "10s"
    resolution_strategy: "victim_selection"
    victim_criteria:
      - "Youngest transaction"
      - "Fewest locks held"
      - "Lowest priority"

  lock_escalation:
    triggers:
      - "Too many row locks (>1000)"
      - "Memory pressure"
      - "Long-running transaction"

    escalation_path:
      row_lock: "table_lock"
      table_lock: "database_lock"
      database_lock: "store_lock"
```

### 2. Lock Implementation Patterns

```python
# Pseudo-code for distributed lock implementation
class DistributedLockManager:
    def __init__(self, consensus_service, lease_manager):
        self.consensus = consensus_service
        self.lease_manager = lease_manager
        self.lock_registry = {}

    async def acquire_lock(
        self,
        resource_id: str,
        lock_type: LockType,
        requester_id: str,
        timeout: int = 300
    ) -> LockAcquisitionResult:
        """
        Acquire distributed lock with consensus-based coordination
        """
        lock_request = LockRequest(
            resource_id=resource_id,
            lock_type=lock_type,
            requester_id=requester_id,
            timeout=timeout,
            request_timestamp=time.utc_now()
        )

        # Check lock compatibility
        if not await self.check_lock_compatibility(lock_request):
            return await self.handle_lock_conflict(lock_request)

        # Acquire lock through consensus
        lock_id = await self.consensus.propose_lock_acquisition(lock_request)

        if lock_id:
            # Set up lease management
            lease = await self.lease_manager.create_lease(
                lock_id, timeout, auto_renew=True
            )

            self.lock_registry[lock_id] = DistributedLock(
                lock_id=lock_id,
                resource_id=resource_id,
                lock_type=lock_type,
                holder_id=requester_id,
                lease=lease,
                acquired_at=time.utc_now()
            )

            return LockAcquisitionResult.success(lock_id)
        else:
            return LockAcquisitionResult.failed("Consensus failed")

    async def check_lock_compatibility(
        self,
        lock_request: LockRequest
    ) -> bool:
        """
        Check if requested lock is compatible with existing locks
        """
        existing_locks = await self.get_locks_for_resource(
            lock_request.resource_id
        )

        for existing_lock in existing_locks:
            if not self.are_locks_compatible(
                lock_request.lock_type,
                existing_lock.lock_type
            ):
                return False

        return True

    async def handle_lock_conflict(
        self,
        lock_request: LockRequest
    ) -> LockAcquisitionResult:
        """
        Handle lock conflicts with wait queues and deadlock detection
        """
        # Add to wait queue
        await self.add_to_wait_queue(lock_request)

        # Check for potential deadlocks
        if await self.detect_deadlock(lock_request.requester_id):
            await self.resolve_deadlock(lock_request.requester_id)
            return LockAcquisitionResult.aborted("Deadlock detected")

        # Wait for lock availability
        try:
            lock_id = await self.wait_for_lock_availability(
                lock_request, timeout=lock_request.timeout
            )
            return LockAcquisitionResult.success(lock_id)
        except TimeoutError:
            await self.remove_from_wait_queue(lock_request)
            return LockAcquisitionResult.timeout()
```

## Partition Tolerance

### 1. Network Partition Handling

```yaml
partition_tolerance:
  detection:
    mechanisms:
      - "Consensus heartbeat failure"
      - "Cross-store communication timeout"
      - "Coordinator election failure"

    thresholds:
      heartbeat_miss_count: 3
      communication_timeout: "30s"
      election_timeout: "60s"

  response_strategies:
    availability_priority:
      description: "Continue operations with reduced consistency"
      actions:
        - "Switch to eventual consistency mode"
        - "Allow reads from any available store"
        - "Queue writes for later synchronization"
      risks: ["Data divergence", "Conflict accumulation"]

    consistency_priority:
      description: "Halt operations to maintain consistency"
      actions:
        - "Reject writes to minority partition"
        - "Allow reads only from majority partition"
        - "Maintain strong consistency guarantees"
      risks: ["Reduced availability", "Service disruption"]

    hybrid_approach:
      description: "Different strategies for different data types"
      rules:
        critical_data: "consistency_priority"
        operational_data: "availability_priority"
        cache_data: "availability_priority"
        audit_data: "consistency_priority"

  recovery_protocols:
    partition_healing:
      detection: "Restored heartbeat communication"
      steps:
        - "Identify divergent data"
        - "Apply conflict resolution strategies"
        - "Synchronize state across partitions"
        - "Resume normal operations"

    conflict_resolution:
      strategies:
        - "Vector clock comparison"
        - "Application-specific merge"
        - "Manual intervention for conflicts"

    state_synchronization:
      methods:
        - "Merkle tree comparison"
        - "Event log replay"
        - "Full state transfer (last resort)"
```

## Performance Optimization

### 1. Coordination Performance Tuning

```yaml
performance_optimization:
  batching:
    transaction_batching:
      max_batch_size: 100
      batch_timeout: "100ms"
      adaptive_batching: true

    lock_batching:
      enabled: true
      batch_window: "10ms"
      max_locks_per_batch: 50

  caching:
    lock_status_cache:
      ttl: "5s"
      max_entries: 10000
      invalidation: "on_lock_change"

    consistency_cache:
      ttl: "30s"
      max_entries: 1000
      invalidation: "on_data_change"

  parallelization:
    validation_parallelism: 4
    coordination_workers: 8
    max_concurrent_transactions: 100

  resource_pooling:
    connection_pools:
      initial_size: 10
      max_size: 100
      idle_timeout: "300s"

    thread_pools:
      coordination_threads: 20
      validation_threads: 10
      conflict_resolution_threads: 5
```

## Monitoring and Observability

### 1. Coordination Metrics

```yaml
coordination_monitoring:
  metrics:
    transaction_metrics:
      - "coordination_transactions_total"
      - "coordination_transaction_duration_seconds"
      - "coordination_transaction_failure_rate"
      - "coordination_deadlock_count"

    lock_metrics:
      - "coordination_active_locks_count"
      - "coordination_lock_wait_time_seconds"
      - "coordination_lock_contention_rate"
      - "coordination_deadlock_detection_time"

    consistency_metrics:
      - "coordination_consistency_violations_total"
      - "coordination_consistency_check_duration"
      - "coordination_auto_repair_success_rate"
      - "coordination_manual_intervention_count"

  alerts:
    high_priority:
      - "Transaction failure rate > 5%"
      - "Average lock wait time > 10s"
      - "Critical consistency violations detected"
      - "Coordinator election failure"

    medium_priority:
      - "Deadlock detection > 10/hour"
      - "Lock contention ratio > 20%"
      - "Partition detection events"
      - "Auto-repair failure rate > 10%"

  distributed_tracing:
    trace_sampling: 0.1  # 10% of coordination operations
    span_attributes:
      - "coordination.type"
      - "coordination.participants"
      - "coordination.duration"
      - "coordination.outcome"

    trace_propagation:
      headers: ["x-trace-id", "x-span-id", "x-parent-span-id"]
      context_injection: "automatic"
```

This comprehensive cross-store coordination system provides the foundation for reliable distributed operations across MemoryOS storage stores while maintaining consistency, availability, and partition tolerance according to the specific requirements of each operation type.
