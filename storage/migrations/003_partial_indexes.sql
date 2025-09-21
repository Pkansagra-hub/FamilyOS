-- Storage Migration 003: Enhanced Partial Indexes
-- Description: Additional partial indexes for specialized query patterns
-- Target: Further optimize specific query patterns and reduce index size
-- Database: SQLite

-- Migration metadata
-- Version: 003
-- Description: Enhanced partial indexes for specialized queries
-- Author: Storage Hardening Plan
-- Date: 2025-09-14

-- =====================================================
-- SPECIALIZED PARTIAL INDEXES
-- =====================================================

-- Recent high-priority outbox events (last 24 hours)
-- Optimizes urgent event processing
CREATE INDEX IF NOT EXISTS idx_outbox_recent_high_priority
ON outbox_events(priority DESC, created_at ASC)
WHERE status = 'pending'
  AND priority >= 8
  AND created_at > strftime('%s', 'now', '-1 day');

-- Failed events needing retry (within retry window)
-- Optimizes retry processing workflow
CREATE INDEX IF NOT EXISTS idx_outbox_retry_window
ON outbox_events(next_retry_at ASC, retry_count ASC)
WHERE status = 'failed'
  AND retry_count < max_retries
  AND next_retry_at <= strftime('%s', 'now');

-- Active episodic events with high salience (for quick recall)
-- Optimizes important memory retrieval
CREATE INDEX IF NOT EXISTS idx_episodic_high_salience
ON episodic_events(space_id, ts DESC)
WHERE status = 'active'
  AND json_extract(features_json, '$.salience') > 0.7;

-- Recent episodic events by author (last 7 days)
-- Optimizes user activity tracking
CREATE INDEX IF NOT EXISTS idx_episodic_recent_author
ON episodic_events(author, ts DESC, event_type)
WHERE status = 'active'
  AND ts > strftime('%s', 'now', '-7 days');

-- Memory events pending consolidation
-- Optimizes hippocampus consolidation queries
CREATE INDEX IF NOT EXISTS idx_memory_pending_consolidation
ON memory_events(space_id, timestamp ASC, memory_type)
WHERE consolidation_status IN ('pending', 'in_progress')
  AND status = 'active';

-- Large vectors for dimension reduction candidates
-- Optimizes vector storage management
CREATE INDEX IF NOT EXISTS idx_vectors_large_embeddings
ON vectors(space_id, dimension DESC, created_at DESC)
WHERE embedding IS NOT NULL
  AND dimension > 512;

-- Recently accessed memory events (cache optimization)
-- Optimizes frequently accessed content
CREATE INDEX IF NOT EXISTS idx_memory_recently_accessed
ON memory_events(space_id, timestamp DESC, memory_type)
WHERE status = 'active'
  AND updated_at > strftime('%s', 'now', '-1 hour');

-- Episodic events with device context (mobile optimization)
-- Optimizes mobile device specific queries
CREATE INDEX IF NOT EXISTS idx_episodic_mobile_context
ON episodic_events(device, space_id, ts DESC)
WHERE device IS NOT NULL
  AND device LIKE '%mobile%'
  AND status = 'active';

-- Vector embeddings by creation time clusters
-- Optimizes batch processing and cleanup
CREATE INDEX IF NOT EXISTS idx_vectors_time_clusters
ON vectors(created_at DESC, space_id, dimension)
WHERE embedding IS NOT NULL
  AND created_at > strftime('%s', 'now', '-30 days');

-- =====================================================
-- COMPOSITE PARTIAL INDEXES FOR ANALYTICS
-- =====================================================

-- Space analytics for active content only
-- Optimizes dashboard and reporting queries
CREATE INDEX IF NOT EXISTS idx_analytics_active_content
ON episodic_events(space_id, event_type, ts DESC)
WHERE status = 'active'
  AND ts > strftime('%s', 'now', '-90 days');

-- Error tracking for operational monitoring
-- Optimizes error analysis and debugging
CREATE INDEX IF NOT EXISTS idx_operational_errors
ON episodic_events(status, ts DESC, author, event_type)
WHERE status IN ('failed', 'error')
  AND ts > strftime('%s', 'now', '-7 days');

-- Memory lifecycle tracking
-- Optimizes memory management analytics
CREATE INDEX IF NOT EXISTS idx_memory_lifecycle
ON memory_events(memory_type, consolidation_status, timestamp DESC)
WHERE status != 'archived'
  AND timestamp > strftime('%s', 'now', '-30 days');

-- =====================================================
-- STATISTICS UPDATE
-- =====================================================

-- Update SQLite statistics to include new partial indexes
ANALYZE episodic_events;
ANALYZE vectors;
ANALYZE memory_events;
ANALYZE outbox_events;

-- Verify partial index creation completed successfully
SELECT 'Enhanced partial indexes created successfully' as status;
