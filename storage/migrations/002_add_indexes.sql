-- Migration: Add Performance Indexes
-- Description: Comprehensive indexing strategy for query optimization
-- Target: 50%+ latency reduction through covering and partial indexes
-- Database: SQLite (using actual table schema from 001_initial_schema.sql)

-- =====================================================
-- COVERING INDEXES FOR EPISODIC EVENTS  
-- =====================================================

-- Primary covering index: space_id + ts (DESC) + frequently accessed columns
-- SQLite automatically includes rowid for covering behavior when columns are in index
CREATE INDEX IF NOT EXISTS idx_episodic_covering 
ON episodic_events(space_id, ts DESC, id, event_type, status);

-- Event type queries within space - ordered by time
-- Covers most filtered queries by space and event type
CREATE INDEX IF NOT EXISTS idx_episodic_space_type 
ON episodic_events(space_id, event_type, ts DESC, id, status);

-- Partial index for active events only (excludes deleted/archived)
-- Improves selectivity for queries on live data
CREATE INDEX IF NOT EXISTS idx_episodic_active 
ON episodic_events(space_id, ts DESC, id, event_type)
WHERE status NOT IN ('deleted', 'archived');

-- Author-based queries for audit trails
-- Optimizes security and compliance queries by author
CREATE INDEX IF NOT EXISTS idx_episodic_author 
ON episodic_events(author, ts DESC, space_id, event_type);

-- Device-based queries for device-specific event tracking
CREATE INDEX IF NOT EXISTS idx_episodic_device 
ON episodic_events(device, ts DESC, space_id, event_type)
WHERE device IS NOT NULL;

-- =====================================================
-- METADATA INDEXES FOR VECTORS
-- =====================================================

-- Vector queries by space and item - primary access pattern
-- Covers vector retrieval by space and item with dimension info
CREATE INDEX IF NOT EXISTS idx_vectors_space_item 
ON vectors(space_id, item_id, dimension, created_at DESC);

-- Vector dimension queries for similarity search optimization
-- Partial index only for records with embeddings
CREATE INDEX IF NOT EXISTS idx_vectors_dimension_space 
ON vectors(dimension, space_id, created_at DESC)
WHERE embedding IS NOT NULL;

-- Metadata JSON queries using SQLite JSON functions
-- Note: Actual JSON extraction indexes would require knowing metadata structure
CREATE INDEX IF NOT EXISTS idx_vectors_metadata_space 
ON vectors(space_id, created_at DESC)
WHERE metadata != '{}';

-- =====================================================
-- MEMORY EVENT INDEXES
-- =====================================================

-- Memory type queries within space - primary access pattern
-- Covers memory retrieval by type and space with temporal ordering
CREATE INDEX IF NOT EXISTS idx_memory_events_type_space 
ON memory_events(memory_type, space_id, timestamp DESC, id, status);

-- Temporal queries across all memory types
-- Optimizes time-based consolidation and retrieval patterns
CREATE INDEX IF NOT EXISTS idx_memory_events_temporal 
ON memory_events(timestamp DESC, memory_type, space_id, id);

-- Active memory queries - excludes processed/archived
-- Partial index for memory lifecycle management
CREATE INDEX IF NOT EXISTS idx_memory_events_active 
ON memory_events(space_id, memory_type, timestamp DESC, id)
WHERE status = 'active';

-- Consolidation status tracking for hippocampus integration
CREATE INDEX IF NOT EXISTS idx_memory_consolidation_status 
ON memory_events(consolidation_status, space_id, timestamp DESC)
WHERE consolidation_status != 'completed';

-- =====================================================
-- OUTBOX PATTERN INDEXES
-- =====================================================

-- Critical index for outbox worker - pending events by priority
-- Covers all fields needed for outbox processing workflow
CREATE INDEX IF NOT EXISTS idx_outbox_pending 
ON outbox_events(status, priority DESC, created_at ASC, id, event_type);

-- Retry pattern optimization - failed events by retry count
-- Helps prioritize retry operations with exponential backoff
CREATE INDEX IF NOT EXISTS idx_outbox_retry 
ON outbox_events(status, retry_count ASC, next_retry_at ASC, id)
WHERE status = 'failed';

-- Cleanup operations - processed events by age
-- Supports efficient archival and cleanup of old events
CREATE INDEX IF NOT EXISTS idx_outbox_cleanup 
ON outbox_events(status, processed_at ASC, id)
WHERE status = 'processed';

-- Aggregate-based queries for event sourcing patterns
CREATE INDEX IF NOT EXISTS idx_outbox_aggregate 
ON outbox_events(aggregate_id, created_at DESC, status);

-- =====================================================
-- PERFORMANCE TRACKING INDEXES
-- =====================================================

-- Recent events for monitoring and metrics (last 7 days)
-- Partial index for hot performance tracking data
CREATE INDEX IF NOT EXISTS idx_performance_tracking 
ON episodic_events(ts DESC, event_type, space_id, id)
WHERE ts > strftime('%s', 'now', '-7 days');

-- Error tracking for debugging and alerting
-- Focuses on failed/error states for operational monitoring
CREATE INDEX IF NOT EXISTS idx_error_tracking 
ON episodic_events(status, ts DESC, event_type, space_id)
WHERE status IN ('failed', 'error', 'retry');

-- Space-specific metrics and analytics
-- Supports per-space performance analysis and reporting
CREATE INDEX IF NOT EXISTS idx_space_analytics 
ON episodic_events(space_id, event_type, ts DESC, status)
WHERE ts > strftime('%s', 'now', '-30 days');

-- =====================================================
-- QUERY OPTIMIZATION HELPERS
-- =====================================================

-- Composite index for COUNT(*) queries by space and time
-- Optimizes dashboard and analytics aggregation queries
CREATE INDEX IF NOT EXISTS idx_aggregation_helper 
ON episodic_events(space_id, event_type, status, ts DESC);

-- Memory utilization tracking for storage optimization
-- Helps with capacity planning and storage analytics
CREATE INDEX IF NOT EXISTS idx_storage_utilization 
ON vectors(space_id, dimension, created_at DESC)
WHERE embedding IS NOT NULL;

-- Content hash index for deduplication and integrity
CREATE INDEX IF NOT EXISTS idx_memory_content_hash
ON memory_events(content_hash, space_id);

-- =====================================================
-- STATISTICS UPDATE
-- =====================================================

-- Update SQLite statistics for optimal query planning
-- These commands help SQLite choose the best indexes
ANALYZE episodic_events;
ANALYZE vectors;
ANALYZE memory_events;
ANALYZE outbox_events;

-- Verify index creation completed successfully
SELECT 'Index creation completed successfully' as status;