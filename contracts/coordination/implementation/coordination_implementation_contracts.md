# Cross-Store Coordination Implementation Contracts

## Implementation Architecture

### 1. Coordination Service Layer

```python
# Coordination service implementation contract
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import asyncio

class CoordinationType(Enum):
    TWO_PHASE_COMMIT = "two_phase_commit"
    SAGA_ORCHESTRATION = "saga_orchestration"
    SAGA_CHOREOGRAPHY = "saga_choreography"
    EVENT_SOURCING = "event_sourcing"
    EVENTUAL_CONSISTENCY = "eventual_consistency"

class TransactionState(Enum):
    INITIATED = "initiated"
    PREPARING = "preparing"
    PREPARED = "prepared"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ABORTING = "aborting"
    ABORTED = "aborted"
    FAILED = "failed"

@dataclass
class CoordinationRequest:
    coordination_id: str
    coordination_type: CoordinationType
    participating_stores: List[str]
    operations: List[Dict[str, Any]]
    timeout_seconds: int
    consistency_level: str
    metadata: Dict[str, Any]

@dataclass
class CoordinationResult:
    coordination_id: str
    success: bool
    final_state: TransactionState
    error_message: Optional[str]
    execution_duration_ms: int
    participating_stores: List[str]
    operations_completed: int
    operations_failed: int

class ICoordinationService(ABC):
    """
    Abstract interface for cross-store coordination service
    """

    @abstractmethod
    async def coordinate_transaction(
        self,
        request: CoordinationRequest
    ) -> CoordinationResult:
        """
        Coordinate a cross-store transaction
        """
        pass

    @abstractmethod
    async def get_coordination_status(
        self,
        coordination_id: str
    ) -> Optional[CoordinationResult]:
        """
        Get status of ongoing coordination
        """
        pass

    @abstractmethod
    async def abort_coordination(
        self,
        coordination_id: str,
        reason: str
    ) -> bool:
        """
        Abort ongoing coordination
        """
        pass

    @abstractmethod
    async def list_active_coordinations(self) -> List[str]:
        """
        List all active coordination IDs
        """
        pass

class CoordinationService(ICoordinationService):
    """
    Main coordination service implementation
    """

    def __init__(
        self,
        stores: Dict[str, 'IStorageStore'],
        consensus_service: 'IConsensusService',
        lock_manager: 'IDistributedLockManager',
        event_bus: 'IEventBus',
        metrics_collector: 'IMetricsCollector'
    ):
        self.stores = stores
        self.consensus = consensus_service
        self.lock_manager = lock_manager
        self.event_bus = event_bus
        self.metrics = metrics_collector
        self.active_coordinations: Dict[str, CoordinationContext] = {}

    async def coordinate_transaction(
        self,
        request: CoordinationRequest
    ) -> CoordinationResult:
        """
        Implementation contract for transaction coordination
        """
        coordination_context = CoordinationContext(
            coordination_id=request.coordination_id,
            coordination_type=request.coordination_type,
            participating_stores=request.participating_stores,
            operations=request.operations,
            timeout_seconds=request.timeout_seconds,
            started_at=datetime.utcnow()
        )

        self.active_coordinations[request.coordination_id] = coordination_context

        try:
            # Emit coordination started event
            await self.event_bus.publish_event({
                "type": "COORDINATION_STARTED",
                "coordination_id": request.coordination_id,
                "coordination_type": request.coordination_type.value,
                "participating_stores": request.participating_stores,
                "started_at": coordination_context.started_at.isoformat()
            })

            # Select coordination strategy
            if request.coordination_type == CoordinationType.TWO_PHASE_COMMIT:
                result = await self._execute_2pc(coordination_context)
            elif request.coordination_type == CoordinationType.SAGA_ORCHESTRATION:
                result = await self._execute_saga_orchestration(coordination_context)
            elif request.coordination_type == CoordinationType.SAGA_CHOREOGRAPHY:
                result = await self._execute_saga_choreography(coordination_context)
            elif request.coordination_type == CoordinationType.EVENT_SOURCING:
                result = await self._execute_event_sourcing(coordination_context)
            else:
                raise ValueError(f"Unsupported coordination type: {request.coordination_type}")

            # Emit coordination completed event
            await self.event_bus.publish_event({
                "type": "COORDINATION_COMPLETED",
                "coordination_id": request.coordination_id,
                "success": result.success,
                "final_state": result.final_state.value,
                "execution_duration_ms": result.execution_duration_ms
            })

            return result

        except Exception as e:
            # Handle coordination failure
            error_result = CoordinationResult(
                coordination_id=request.coordination_id,
                success=False,
                final_state=TransactionState.FAILED,
                error_message=str(e),
                execution_duration_ms=0,
                participating_stores=request.participating_stores,
                operations_completed=0,
                operations_failed=len(request.operations)
            )

            await self.event_bus.publish_event({
                "type": "COORDINATION_FAILED",
                "coordination_id": request.coordination_id,
                "error_message": str(e),
                "failed_at": datetime.utcnow().isoformat()
            })

            return error_result

        finally:
            # Cleanup coordination context
            if request.coordination_id in self.active_coordinations:
                del self.active_coordinations[request.coordination_id]

    async def _execute_2pc(
        self,
        context: 'CoordinationContext'
    ) -> CoordinationResult:
        """
        Two-phase commit implementation contract
        """
        start_time = datetime.utcnow()

        # Phase 1: PREPARE
        context.state = TransactionState.PREPARING
        prepare_results = await self._send_prepare_messages(context)

        if not all(result.vote == "COMMIT" for result in prepare_results.values()):
            # Some participants voted ABORT
            context.state = TransactionState.ABORTING
            await self._send_abort_messages(context)

            return CoordinationResult(
                coordination_id=context.coordination_id,
                success=False,
                final_state=TransactionState.ABORTED,
                error_message="One or more participants voted ABORT",
                execution_duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                participating_stores=context.participating_stores,
                operations_completed=0,
                operations_failed=len(context.operations)
            )

        # Phase 2: COMMIT
        context.state = TransactionState.COMMITTING
        commit_results = await self._send_commit_messages(context)

        if all(result.status == "SUCCESS" for result in commit_results.values()):
            context.state = TransactionState.COMMITTED
            return CoordinationResult(
                coordination_id=context.coordination_id,
                success=True,
                final_state=TransactionState.COMMITTED,
                error_message=None,
                execution_duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                participating_stores=context.participating_stores,
                operations_completed=len(context.operations),
                operations_failed=0
            )
        else:
            # Commit phase failed - this is a serious error
            context.state = TransactionState.FAILED
            await self._handle_commit_failure(context, commit_results)

            return CoordinationResult(
                coordination_id=context.coordination_id,
                success=False,
                final_state=TransactionState.FAILED,
                error_message="Commit phase failed - manual intervention required",
                execution_duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                participating_stores=context.participating_stores,
                operations_completed=sum(1 for r in commit_results.values() if r.status == "SUCCESS"),
                operations_failed=sum(1 for r in commit_results.values() if r.status == "FAILED")
            )

    async def _send_prepare_messages(
        self,
        context: 'CoordinationContext'
    ) -> Dict[str, 'PrepareResult']:
        """
        Send PREPARE messages to all participants
        """
        prepare_tasks = []
        for store_name in context.participating_stores:
            store = self.stores[store_name]
            task = asyncio.create_task(
                self._send_prepare_to_store(store, context)
            )
            prepare_tasks.append((store_name, task))

        results = {}
        for store_name, task in prepare_tasks:
            try:
                result = await asyncio.wait_for(task, timeout=30.0)
                results[store_name] = result
            except asyncio.TimeoutError:
                results[store_name] = PrepareResult(
                    store_name=store_name,
                    vote="ABORT",
                    reason="Prepare timeout"
                )

        return results

    async def _send_prepare_to_store(
        self,
        store: 'IStorageStore',
        context: 'CoordinationContext'
    ) -> 'PrepareResult':
        """
        Send prepare message to individual store
        """
        try:
            # Get store-specific operations
            store_operations = [
                op for op in context.operations
                if op.get('store') == store.store_name
            ]

            # Send prepare request
            prepare_request = PrepareRequest(
                transaction_id=context.coordination_id,
                operations=store_operations,
                timeout_seconds=context.timeout_seconds
            )

            result = await store.prepare_transaction(prepare_request)
            return result

        except Exception as e:
            return PrepareResult(
                store_name=store.store_name,
                vote="ABORT",
                reason=f"Prepare failed: {str(e)}"
            )
```

### 2. Consensus Service Implementation

```python
# Consensus service for coordination decisions
class IConsensusService(ABC):
    """
    Interface for consensus-based decision making
    """

    @abstractmethod
    async def propose_coordination_decision(
        self,
        coordination_id: str,
        decision: str,
        evidence: Dict[str, Any]
    ) -> bool:
        """
        Propose a coordination decision and achieve consensus
        """
        pass

    @abstractmethod
    async def get_consensus_status(
        self,
        coordination_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current consensus status for coordination
        """
        pass

class RaftConsensusService(IConsensusService):
    """
    Raft-based consensus implementation for coordination
    """

    def __init__(
        self,
        node_id: str,
        cluster_nodes: List[str],
        election_timeout_ms: int = 5000,
        heartbeat_interval_ms: int = 1000
    ):
        self.node_id = node_id
        self.cluster_nodes = cluster_nodes
        self.election_timeout_ms = election_timeout_ms
        self.heartbeat_interval_ms = heartbeat_interval_ms
        self.current_term = 0
        self.voted_for = None
        self.log_entries = []
        self.commit_index = 0
        self.last_applied = 0
        self.state = "follower"  # follower, candidate, leader
        self.leader_id = None

    async def propose_coordination_decision(
        self,
        coordination_id: str,
        decision: str,
        evidence: Dict[str, Any]
    ) -> bool:
        """
        Consensus implementation contract for coordination decisions
        """
        if self.state != "leader":
            # Redirect to current leader
            if self.leader_id:
                return await self._forward_to_leader(
                    coordination_id, decision, evidence
                )
            else:
                # No leader available
                return False

        # Create log entry for decision
        log_entry = LogEntry(
            term=self.current_term,
            index=len(self.log_entries),
            coordination_id=coordination_id,
            decision=decision,
            evidence=evidence,
            timestamp=datetime.utcnow()
        )

        # Append to local log
        self.log_entries.append(log_entry)

        # Replicate to majority of followers
        replication_success = await self._replicate_to_majority(log_entry)

        if replication_success:
            # Update commit index
            self.commit_index = log_entry.index
            await self._apply_log_entry(log_entry)
            return True
        else:
            # Remove from log if replication failed
            self.log_entries.remove(log_entry)
            return False

    async def _replicate_to_majority(self, log_entry: 'LogEntry') -> bool:
        """
        Replicate log entry to majority of cluster nodes
        """
        replication_tasks = []
        for node_id in self.cluster_nodes:
            if node_id != self.node_id:
                task = asyncio.create_task(
                    self._send_append_entries(node_id, log_entry)
                )
                replication_tasks.append(task)

        # Wait for majority to respond positively
        success_count = 1  # Include self
        required_majority = (len(self.cluster_nodes) // 2) + 1

        for task in asyncio.as_completed(replication_tasks):
            try:
                result = await task
                if result.success:
                    success_count += 1
                    if success_count >= required_majority:
                        return True
            except Exception:
                continue

        return success_count >= required_majority
```

### 3. Distributed Lock Manager Implementation

```python
# Distributed lock manager implementation contract
class IDistributedLockManager(ABC):
    """
    Interface for distributed lock management
    """

    @abstractmethod
    async def acquire_lock(
        self,
        resource_id: str,
        lock_type: 'LockType',
        requester_id: str,
        timeout_seconds: int = 300
    ) -> 'LockAcquisitionResult':
        """
        Acquire distributed lock on resource
        """
        pass

    @abstractmethod
    async def release_lock(
        self,
        lock_id: str,
        requester_id: str
    ) -> bool:
        """
        Release distributed lock
        """
        pass

    @abstractmethod
    async def check_lock_status(
        self,
        resource_id: str
    ) -> List['LockInfo']:
        """
        Check current lock status for resource
        """
        pass

class ZooKeeperLockManager(IDistributedLockManager):
    """
    ZooKeeper-based distributed lock implementation
    """

    def __init__(
        self,
        zk_connection_string: str,
        lock_root_path: str = "/memory_os/locks",
        session_timeout_ms: int = 30000
    ):
        self.zk_connection_string = zk_connection_string
        self.lock_root_path = lock_root_path
        self.session_timeout_ms = session_timeout_ms
        self.zk_client = None
        self.active_locks: Dict[str, 'ActiveLock'] = {}

    async def acquire_lock(
        self,
        resource_id: str,
        lock_type: LockType,
        requester_id: str,
        timeout_seconds: int = 300
    ) -> LockAcquisitionResult:
        """
        ZooKeeper lock acquisition implementation contract
        """
        lock_path = f"{self.lock_root_path}/{resource_id}/{lock_type.value}"
        ephemeral_sequential_path = f"{lock_path}/{requester_id}-"

        try:
            # Create ephemeral sequential node
            actual_path = await self.zk_client.create(
                ephemeral_sequential_path,
                data=json.dumps({
                    "requester_id": requester_id,
                    "lock_type": lock_type.value,
                    "requested_at": datetime.utcnow().isoformat(),
                    "timeout_seconds": timeout_seconds
                }).encode('utf-8'),
                ephemeral=True,
                sequence=True
            )

            # Check if we have the lock
            children = await self.zk_client.get_children(lock_path)
            children.sort()

            our_sequence = int(actual_path.split('-')[-1])

            # Check lock compatibility with predecessors
            can_acquire = await self._check_lock_compatibility(
                lock_path, our_sequence, lock_type, children
            )

            if can_acquire:
                # We have the lock
                lock_id = f"{resource_id}:{lock_type.value}:{our_sequence}"
                active_lock = ActiveLock(
                    lock_id=lock_id,
                    resource_id=resource_id,
                    lock_type=lock_type,
                    requester_id=requester_id,
                    zk_path=actual_path,
                    acquired_at=datetime.utcnow()
                )

                self.active_locks[lock_id] = active_lock

                return LockAcquisitionResult.success(
                    lock_id=lock_id,
                    acquired_at=active_lock.acquired_at
                )
            else:
                # Wait for lock availability
                return await self._wait_for_lock(
                    actual_path, lock_path, lock_type,
                    requester_id, timeout_seconds
                )

        except Exception as e:
            return LockAcquisitionResult.failed(
                error_message=f"Lock acquisition failed: {str(e)}"
            )

    async def _check_lock_compatibility(
        self,
        lock_path: str,
        our_sequence: int,
        our_lock_type: LockType,
        all_children: List[str]
    ) -> bool:
        """
        Check if our lock is compatible with existing locks
        """
        # Get all nodes with lower sequence numbers
        predecessors = [
            child for child in all_children
            if int(child.split('-')[-1]) < our_sequence
        ]

        for predecessor in predecessors:
            predecessor_path = f"{lock_path}/{predecessor}"

            try:
                data, _ = await self.zk_client.get(predecessor_path)
                predecessor_info = json.loads(data.decode('utf-8'))
                predecessor_lock_type = LockType(predecessor_info['lock_type'])

                # Check compatibility matrix
                if not self._are_locks_compatible(our_lock_type, predecessor_lock_type):
                    return False

            except Exception:
                # Predecessor node might have been deleted
                continue

        return True

    def _are_locks_compatible(
        self,
        lock_type1: LockType,
        lock_type2: LockType
    ) -> bool:
        """
        Lock compatibility matrix implementation
        """
        compatibility_matrix = {
            (LockType.EXCLUSIVE, LockType.EXCLUSIVE): False,
            (LockType.EXCLUSIVE, LockType.SHARED): False,
            (LockType.SHARED, LockType.EXCLUSIVE): False,
            (LockType.SHARED, LockType.SHARED): True,
            (LockType.INTENT_EXCLUSIVE, LockType.INTENT_EXCLUSIVE): True,
            (LockType.INTENT_EXCLUSIVE, LockType.INTENT_SHARED): True,
            (LockType.INTENT_SHARED, LockType.INTENT_EXCLUSIVE): True,
            (LockType.INTENT_SHARED, LockType.INTENT_SHARED): True,
        }

        return compatibility_matrix.get((lock_type1, lock_type2), False)
```

### 4. Event Bus Integration

```python
# Event bus integration for coordination events
class CoordinationEventHandler:
    """
    Event handler for coordination-related events
    """

    def __init__(
        self,
        coordination_service: ICoordinationService,
        metrics_collector: 'IMetricsCollector',
        alerting_service: 'IAlertingService'
    ):
        self.coordination_service = coordination_service
        self.metrics = metrics_collector
        self.alerting = alerting_service

    async def handle_coordination_event(self, event: Dict[str, Any]) -> None:
        """
        Handle coordination-related events
        """
        event_type = event.get('type')

        if event_type == 'COORDINATION_STARTED':
            await self._handle_coordination_started(event)
        elif event_type == 'COORDINATION_COMPLETED':
            await self._handle_coordination_completed(event)
        elif event_type == 'COORDINATION_FAILED':
            await self._handle_coordination_failed(event)
        elif event_type == 'DEADLOCK_DETECTED':
            await self._handle_deadlock_detected(event)
        elif event_type == 'PARTITION_DETECTED':
            await self._handle_partition_detected(event)

    async def _handle_coordination_started(self, event: Dict[str, Any]) -> None:
        """
        Handle coordination started event
        """
        coordination_id = event['coordination_id']
        coordination_type = event['coordination_type']

        # Update metrics
        self.metrics.increment_counter(
            'coordination_transactions_started_total',
            labels={'type': coordination_type}
        )

        # Log coordination start
        logger.info(
            f"Coordination started: {coordination_id} "
            f"(type: {coordination_type})"
        )

    async def _handle_coordination_completed(self, event: Dict[str, Any]) -> None:
        """
        Handle coordination completed event
        """
        coordination_id = event['coordination_id']
        success = event['success']
        duration_ms = event['execution_duration_ms']

        # Update metrics
        self.metrics.increment_counter(
            'coordination_transactions_completed_total',
            labels={'success': str(success)}
        )

        self.metrics.record_histogram(
            'coordination_transaction_duration_seconds',
            duration_ms / 1000.0
        )

        # Log completion
        logger.info(
            f"Coordination completed: {coordination_id} "
            f"(success: {success}, duration: {duration_ms}ms)"
        )

    async def _handle_deadlock_detected(self, event: Dict[str, Any]) -> None:
        """
        Handle deadlock detection event
        """
        victim_transaction = event['victim_transaction']
        deadlock_cycle = event['deadlock_cycle']

        # Update metrics
        self.metrics.increment_counter('coordination_deadlocks_detected_total')

        # Send alert
        await self.alerting.send_alert(
            severity='medium',
            title='Deadlock Detected',
            message=f"Deadlock detected, aborting transaction: {victim_transaction}",
            details={'deadlock_cycle': deadlock_cycle}
        )

        # Log deadlock
        logger.warning(
            f"Deadlock detected, victim: {victim_transaction}, "
            f"cycle: {deadlock_cycle}"
        )
```

## Implementation Database Schemas

### 1. Coordination State Storage

```sql
-- Coordination transaction log
CREATE TABLE coordination_transactions (
    coordination_id VARCHAR(128) PRIMARY KEY,
    coordination_type VARCHAR(50) NOT NULL,
    participating_stores TEXT[] NOT NULL,
    operations JSONB NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'initiated',
    timeout_seconds INTEGER NOT NULL,
    consistency_level VARCHAR(20) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,

    CONSTRAINT valid_state CHECK (state IN (
        'initiated', 'preparing', 'prepared', 'committing',
        'committed', 'aborting', 'aborted', 'failed'
    )),
    CONSTRAINT valid_coordination_type CHECK (coordination_type IN (
        'two_phase_commit', 'saga_orchestration', 'saga_choreography',
        'event_sourcing', 'eventual_consistency'
    ))
);

-- Coordination operation log
CREATE TABLE coordination_operations (
    operation_id VARCHAR(128) PRIMARY KEY,
    coordination_id VARCHAR(128) NOT NULL REFERENCES coordination_transactions(coordination_id),
    store_name VARCHAR(100) NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    operation_data JSONB NOT NULL,
    sequence_number INTEGER NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_operation_state CHECK (state IN (
        'pending', 'executing', 'completed', 'failed', 'retrying'
    ))
);

-- Distributed locks registry
CREATE TABLE distributed_locks (
    lock_id VARCHAR(128) PRIMARY KEY,
    resource_id VARCHAR(256) NOT NULL,
    lock_type VARCHAR(20) NOT NULL,
    holder_id VARCHAR(128) NOT NULL,
    coordination_id VARCHAR(128) REFERENCES coordination_transactions(coordination_id),
    acquired_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    renewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,

    CONSTRAINT valid_lock_type CHECK (lock_type IN (
        'exclusive', 'shared', 'intent_exclusive', 'intent_shared'
    ))
);

-- Lock wait queue
CREATE TABLE lock_wait_queue (
    wait_id VARCHAR(128) PRIMARY KEY,
    resource_id VARCHAR(256) NOT NULL,
    lock_type VARCHAR(20) NOT NULL,
    requester_id VARCHAR(128) NOT NULL,
    coordination_id VARCHAR(128) REFERENCES coordination_transactions(coordination_id),
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    timeout_at TIMESTAMP WITH TIME ZONE NOT NULL,
    position_in_queue INTEGER NOT NULL,
    metadata JSONB
);

-- Consensus log for coordination decisions
CREATE TABLE consensus_log (
    log_index BIGSERIAL PRIMARY KEY,
    term_number INTEGER NOT NULL,
    coordination_id VARCHAR(128) NOT NULL,
    decision_type VARCHAR(50) NOT NULL,
    decision_data JSONB NOT NULL,
    evidence JSONB,
    proposed_by VARCHAR(128) NOT NULL,
    proposed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    committed_at TIMESTAMP WITH TIME ZONE,
    applied_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX idx_coordination_transactions_state ON coordination_transactions(state);
CREATE INDEX idx_coordination_transactions_created_at ON coordination_transactions(created_at);
CREATE INDEX idx_coordination_operations_coordination_id ON coordination_operations(coordination_id);
CREATE INDEX idx_coordination_operations_state ON coordination_operations(state);
CREATE INDEX idx_distributed_locks_resource_id ON distributed_locks(resource_id);
CREATE INDEX idx_distributed_locks_expires_at ON distributed_locks(expires_at);
CREATE INDEX idx_lock_wait_queue_resource_id ON lock_wait_queue(resource_id);
CREATE INDEX idx_lock_wait_queue_timeout_at ON lock_wait_queue(timeout_at);
CREATE INDEX idx_consensus_log_coordination_id ON consensus_log(coordination_id);
```

### 2. Configuration Schema

```yaml
# Coordination service configuration
coordination_service:
  # Database configuration
  database:
    connection_string: "postgresql://user:pass@localhost:5432/memory_os"
    connection_pool:
      min_connections: 5
      max_connections: 20
      idle_timeout_seconds: 300

  # Consensus configuration
  consensus:
    algorithm: "raft"
    cluster_nodes:
      - "coordination-node-1:7000"
      - "coordination-node-2:7000"
      - "coordination-node-3:7000"
    election_timeout_ms: 5000
    heartbeat_interval_ms: 1000
    log_compaction_threshold: 10000

  # Lock manager configuration
  lock_manager:
    backend: "zookeeper"
    zookeeper:
      connection_string: "zk1:2181,zk2:2181,zk3:2181"
      session_timeout_ms: 30000
      lock_root_path: "/memory_os/locks"

    deadlock_detection:
      enabled: true
      detection_interval_seconds: 10
      max_wait_time_seconds: 300

  # Transaction timeout configuration
  timeouts:
    default_transaction_timeout_seconds: 300
    prepare_phase_timeout_seconds: 30
    commit_phase_timeout_seconds: 60
    lock_acquisition_timeout_seconds: 30

  # Performance tuning
  performance:
    max_concurrent_coordinations: 100
    coordination_worker_threads: 20
    batch_size: 50
    batch_timeout_ms: 100

  # Monitoring configuration
  monitoring:
    metrics_enabled: true
    distributed_tracing_enabled: true
    trace_sampling_rate: 0.1

    alerts:
      high_failure_rate_threshold: 0.05
      high_latency_threshold_ms: 5000
      deadlock_rate_threshold_per_hour: 10
```

This comprehensive implementation contract provides the foundation for building a robust cross-store coordination system that ensures consistency, handles failures gracefully, and scales with the MemoryOS requirements.
