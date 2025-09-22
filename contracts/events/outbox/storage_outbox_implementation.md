# Enhanced Outbox Pattern Implementation Contracts

## Overview

The Enhanced Outbox Pattern provides reliable event publishing for the MemoryOS Storage service with transactional guarantees, dead letter queue handling, and retry mechanisms. This implementation integrates seamlessly with the Events Bus Infrastructure including EventBus, validation, persistence, WAL, and pipeline components.

## Architecture Components

### 1. Outbox Table Schema

```sql
-- Storage outbox table for transactional event publishing
CREATE TABLE storage_outbox (
    -- Primary identification
    outbox_id VARCHAR(32) PRIMARY KEY,
    aggregate_id VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,

    -- Event information
    event_type VARCHAR(100) NOT NULL,
    event_payload JSONB NOT NULL,
    event_metadata JSONB NOT NULL DEFAULT '{}',

    -- Ordering and sequencing
    sequence_number BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Delivery tracking
    delivery_attempts INTEGER NOT NULL DEFAULT 0,
    delivery_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    first_attempt_at TIMESTAMP WITH TIME ZONE,
    last_attempt_at TIMESTAMP WITH TIME ZONE,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,

    -- Target information
    target_topic VARCHAR(255) NOT NULL,
    partition_key VARCHAR(255),

    -- Retry configuration
    max_attempts INTEGER NOT NULL DEFAULT 5,
    base_delay_ms INTEGER NOT NULL DEFAULT 1000,
    max_delay_ms INTEGER NOT NULL DEFAULT 60000,
    backoff_multiplier DECIMAL(3,2) NOT NULL DEFAULT 2.0,

    -- Constraints and indexes
    CONSTRAINT valid_delivery_status CHECK (delivery_status IN ('pending', 'processing', 'delivered', 'failed', 'dlq')),
    CONSTRAINT valid_retry_config CHECK (max_attempts > 0 AND base_delay_ms > 0 AND max_delay_ms >= base_delay_ms)
);

-- Indexes for efficient processing
CREATE INDEX idx_outbox_delivery_status ON storage_outbox(delivery_status);
CREATE INDEX idx_outbox_next_retry ON storage_outbox(next_retry_at) WHERE delivery_status IN ('pending', 'failed');
CREATE INDEX idx_outbox_aggregate ON storage_outbox(aggregate_id, aggregate_type, sequence_number);
CREATE INDEX idx_outbox_created_at ON storage_outbox(created_at);
CREATE INDEX idx_outbox_event_type ON storage_outbox(event_type);

-- Sequence for ordering within aggregates
CREATE SEQUENCE storage_outbox_sequence_seq;
```

### 2. Dead Letter Queue Table

```sql
-- Dead letter queue for failed events
CREATE TABLE storage_outbox_dlq (
    -- Inherit all fields from outbox
    LIKE storage_outbox INCLUDING ALL,

    -- DLQ specific fields
    dlq_id VARCHAR(32) PRIMARY KEY,
    moved_to_dlq_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    dlq_reason VARCHAR(50) NOT NULL,
    failure_details JSONB NOT NULL DEFAULT '{}',
    recovery_instructions JSONB DEFAULT '{}',

    -- Reference to original outbox entry
    original_outbox_id VARCHAR(32) NOT NULL REFERENCES storage_outbox(outbox_id),

    CONSTRAINT valid_dlq_reason CHECK (dlq_reason IN (
        'max_retries_exceeded',
        'poison_message',
        'schema_validation_failed',
        'processing_timeout',
        'permanent_failure'
    ))
);

CREATE INDEX idx_outbox_dlq_moved_at ON storage_outbox_dlq(moved_to_dlq_at);
CREATE INDEX idx_outbox_dlq_reason ON storage_outbox_dlq(dlq_reason);
CREATE INDEX idx_outbox_dlq_original ON storage_outbox_dlq(original_outbox_id);
```

### 3. WAL Integration Table

```sql
-- Write-ahead log integration for durability
CREATE TABLE storage_outbox_wal (
    wal_id VARCHAR(32) PRIMARY KEY,
    outbox_id VARCHAR(32) NOT NULL REFERENCES storage_outbox(outbox_id),
    operation_type VARCHAR(20) NOT NULL,
    wal_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    wal_lsn pg_lsn NOT NULL,
    transaction_id VARCHAR(50),
    checkpoint_data JSONB DEFAULT '{}',

    CONSTRAINT valid_operation_type CHECK (operation_type IN ('insert', 'update', 'delete', 'checkpoint'))
);

CREATE INDEX idx_outbox_wal_outbox_id ON storage_outbox_wal(outbox_id);
CREATE INDEX idx_outbox_wal_lsn ON storage_outbox_wal(wal_lsn);
CREATE INDEX idx_outbox_wal_timestamp ON storage_outbox_wal(wal_timestamp);
```

## Implementation Patterns

### 1. Transactional Event Publishing

```python
# Pseudo-code for transactional outbox pattern
async def publish_event_transactionally(
    aggregate_id: str,
    aggregate_type: str,
    event_type: str,
    event_payload: dict,
    metadata: dict,
    connection: AsyncConnection
) -> str:
    """
    Publish event through outbox pattern within existing transaction
    """
    # Generate unique outbox ID
    outbox_id = f"outbox_{generate_uuid()}"

    # Get next sequence number for aggregate
    sequence_number = await get_next_sequence_number(
        aggregate_id, aggregate_type, connection
    )

    # Insert into outbox table within same transaction
    await connection.execute("""
        INSERT INTO storage_outbox (
            outbox_id, aggregate_id, aggregate_type,
            event_type, event_payload, event_metadata,
            sequence_number, target_topic, partition_key
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    """, [
        outbox_id, aggregate_id, aggregate_type,
        event_type, event_payload, metadata,
        sequence_number, get_target_topic(event_type), aggregate_id
    ])

    # Log WAL entry for durability
    await log_wal_entry(outbox_id, 'insert', connection)

    return outbox_id

async def get_next_sequence_number(
    aggregate_id: str,
    aggregate_type: str,
    connection: AsyncConnection
) -> int:
    """
    Get next sequence number for aggregate to ensure ordering
    """
    result = await connection.fetchrow("""
        SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq
        FROM storage_outbox
        WHERE aggregate_id = $1 AND aggregate_type = $2
    """, aggregate_id, aggregate_type)

    return result['next_seq']
```

### 2. Event Publisher Service

```python
# Pseudo-code for outbox event publisher
class OutboxEventPublisher:
    def __init__(self, kafka_producer, db_pool, retry_policy):
        self.kafka_producer = kafka_producer
        self.db_pool = db_pool
        self.retry_policy = retry_policy

    async def process_pending_events(self):
        """
        Process all pending events from outbox table
        """
        while True:
            # Get batch of pending events ordered by sequence
            events = await self.get_pending_events_batch()

            for event in events:
                try:
                    await self.publish_single_event(event)
                    await self.mark_event_delivered(event['outbox_id'])
                except Exception as e:
                    await self.handle_publish_failure(event, e)

            await asyncio.sleep(self.retry_policy.poll_interval)

    async def get_pending_events_batch(self, batch_size: int = 100):
        """
        Get batch of pending events ready for processing
        """
        async with self.db_pool.acquire() as conn:
            return await conn.fetch("""
                SELECT * FROM storage_outbox
                WHERE delivery_status IN ('pending', 'failed')
                  AND (next_retry_at IS NULL OR next_retry_at <= NOW())
                ORDER BY created_at, sequence_number
                LIMIT $1
                FOR UPDATE SKIP LOCKED
            """, batch_size)

    async def publish_single_event(self, event: dict):
        """
        Publish single event to Kafka with validation
        """
        # Update status to processing
        await self.update_delivery_status(
            event['outbox_id'], 'processing'
        )

        # Validate event payload
        await self.validate_event_schema(event)

        # Construct Kafka message
        kafka_message = {
            'key': event['partition_key'],
            'value': {
                **event['event_payload'],
                'metadata': {
                    **event['event_metadata'],
                    'outbox_id': event['outbox_id'],
                    'sequence_number': event['sequence_number']
                }
            },
            'headers': {
                'event_type': event['event_type'],
                'aggregate_id': event['aggregate_id'],
                'correlation_id': event['event_metadata'].get('correlation_id')
            }
        }

        # Publish to Kafka
        await self.kafka_producer.send(
            event['target_topic'],
            kafka_message
        )

    async def handle_publish_failure(self, event: dict, error: Exception):
        """
        Handle event publishing failure with retry logic
        """
        attempts = event['delivery_attempts'] + 1

        if attempts >= event['max_attempts']:
            # Move to DLQ after max retries
            await self.move_to_dlq(event, 'max_retries_exceeded', str(error))
        else:
            # Schedule retry with exponential backoff
            next_retry = self.calculate_next_retry(event, attempts)
            await self.schedule_retry(event['outbox_id'], attempts, next_retry)

    def calculate_next_retry(self, event: dict, attempt: int) -> datetime:
        """
        Calculate next retry time with exponential backoff and jitter
        """
        base_delay = event['base_delay_ms']
        max_delay = event['max_delay_ms']
        multiplier = event['backoff_multiplier']

        # Exponential backoff: delay = base * (multiplier ^ (attempt - 1))
        delay_ms = min(base_delay * (multiplier ** (attempt - 1)), max_delay)

        # Add jitter (±25% random variation)
        jitter = random.uniform(0.75, 1.25)
        final_delay_ms = delay_ms * jitter

        return datetime.utcnow() + timedelta(milliseconds=final_delay_ms)
```

### 3. Event Validation Service

```python
# Pseudo-code for event validation
class EventValidationService:
    def __init__(self, schema_registry):
        self.schema_registry = schema_registry

    async def validate_event_schema(self, event: dict):
        """
        Validate event against registered schema
        """
        schema = await self.schema_registry.get_schema(
            event['event_type'],
            event['event_metadata'].get('event_version', '1.0.0')
        )

        try:
            jsonschema.validate(event['event_payload'], schema)
        except jsonschema.ValidationError as e:
            raise EventValidationError(
                f"Event validation failed: {e.message}",
                event_type=event['event_type'],
                validation_error=str(e)
            )

    async def validate_business_rules(self, event: dict):
        """
        Validate business rules and constraints
        """
        # Example: Validate transaction events have required stores
        if event['event_type'].startswith('STORAGE_TRANSACTION_'):
            if not event['event_payload'].get('stores_involved'):
                raise BusinessRuleViolation(
                    "Transaction events must specify involved stores"
                )

        # Example: Validate sequence numbers are increasing
        if event['aggregate_id']:
            await self.validate_sequence_ordering(
                event['aggregate_id'],
                event['aggregate_type'],
                event['sequence_number']
            )
```

### 4. Dead Letter Queue Management

```python
# Pseudo-code for DLQ management
class DLQManager:
    def __init__(self, db_pool, notification_service):
        self.db_pool = db_pool
        self.notification_service = notification_service

    async def move_to_dlq(
        self,
        event: dict,
        reason: str,
        failure_details: dict
    ):
        """
        Move failed event to Dead Letter Queue
        """
        dlq_id = f"dlq_{generate_uuid()}"

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Insert into DLQ table
                await conn.execute("""
                    INSERT INTO storage_outbox_dlq
                    SELECT *, $1, NOW(), $2, $3, $4, outbox_id
                    FROM storage_outbox
                    WHERE outbox_id = $5
                """, [dlq_id, reason, failure_details, {}, event['outbox_id']])

                # Update original event status
                await conn.execute("""
                    UPDATE storage_outbox
                    SET delivery_status = 'dlq',
                        last_attempt_at = NOW()
                    WHERE outbox_id = $1
                """, event['outbox_id'])

        # Notify operations team
        await self.notification_service.send_dlq_alert(
            event_type=event['event_type'],
            aggregate_id=event['aggregate_id'],
            reason=reason,
            dlq_id=dlq_id
        )

    async def replay_from_dlq(self, dlq_id: str) -> bool:
        """
        Replay event from DLQ after manual intervention
        """
        async with self.db_pool.acquire() as conn:
            # Get DLQ event
            dlq_event = await conn.fetchrow("""
                SELECT * FROM storage_outbox_dlq WHERE dlq_id = $1
            """, dlq_id)

            if not dlq_event:
                return False

            # Reset for replay
            new_outbox_id = f"outbox_{generate_uuid()}"

            async with conn.transaction():
                # Create new outbox entry
                await conn.execute("""
                    INSERT INTO storage_outbox (
                        outbox_id, aggregate_id, aggregate_type,
                        event_type, event_payload, event_metadata,
                        sequence_number, target_topic, partition_key,
                        delivery_attempts, delivery_status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 0, 'pending')
                """, [
                    new_outbox_id, dlq_event['aggregate_id'],
                    dlq_event['aggregate_type'], dlq_event['event_type'],
                    dlq_event['event_payload'], dlq_event['event_metadata'],
                    dlq_event['sequence_number'], dlq_event['target_topic'],
                    dlq_event['partition_key']
                ])

                # Mark DLQ event as replayed
                await conn.execute("""
                    UPDATE storage_outbox_dlq
                    SET recovery_instructions = recovery_instructions ||
                        jsonb_build_object('replayed_at', NOW(), 'new_outbox_id', $2)
                    WHERE dlq_id = $1
                """, dlq_id, new_outbox_id)

        return True
```

## Configuration

### Retry Policy Configuration

```yaml
# Enhanced Outbox Configuration
outbox:
  # Database configuration
  database:
    table_name: "storage_outbox"
    dlq_table_name: "storage_outbox_dlq"
    wal_table_name: "storage_outbox_wal"

  # Publisher configuration
  publisher:
    batch_size: 100
    poll_interval_ms: 1000
    max_concurrent_publishers: 5
    enable_wal_integration: true

  # Retry policy defaults
  retry_policy:
    default_max_attempts: 5
    default_base_delay_ms: 1000
    default_max_delay_ms: 60000
    default_backoff_multiplier: 2.0
    enable_jitter: true
    jitter_range: [0.75, 1.25]

  # DLQ configuration
  dlq:
    auto_dlq_after_max_retries: true
    dlq_notification_enabled: true
    dlq_retention_days: 30
    enable_manual_replay: true

  # Validation configuration
  validation:
    enable_schema_validation: true
    enable_business_rule_validation: true
    schema_registry_url: "https://schema-registry.memoryos.ai"

  # Monitoring configuration
  monitoring:
    enable_metrics: true
    metrics_prefix: "memoryos.storage.outbox"
    enable_health_checks: true
    alert_on_dlq_events: true
```

## Metrics and Monitoring

### Key Metrics

1. **Throughput Metrics**
   - `outbox_events_published_total`
   - `outbox_events_delivered_total`
   - `outbox_events_failed_total`
   - `outbox_events_dlq_total`

2. **Latency Metrics**
   - `outbox_delivery_duration_seconds`
   - `outbox_retry_delay_seconds`
   - `outbox_end_to_end_latency_seconds`

3. **Error Metrics**
   - `outbox_validation_errors_total`
   - `outbox_network_errors_total`
   - `outbox_timeout_errors_total`

4. **Resource Metrics**
   - `outbox_table_size_bytes`
   - `outbox_pending_events_count`
   - `outbox_dlq_events_count`

### Health Checks

1. **Publisher Health**
   - Check if publisher service is running
   - Verify database connectivity
   - Check Kafka producer status

2. **Performance Health**
   - Monitor event processing lag
   - Check retry queue depth
   - Validate delivery success rate

3. **Data Health**
   - Check for orphaned events
   - Verify WAL consistency
   - Monitor DLQ growth rate
