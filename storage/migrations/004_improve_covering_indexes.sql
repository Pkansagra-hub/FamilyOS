-- Migration 004: Improve Covering Indexes for Better Query Performance
-- Addresses remaining queries that are not using covering indexes

-- Drop existing indexes that need to be enhanced
DROP INDEX IF EXISTS idx_episodic_events_space_time;
DROP INDEX IF EXISTS idx_vectors_space_item;

-- Enhanced covering index for episodic events by space with ts ordering
-- Covers: space_id, ts (for WHERE and ORDER BY), id, event_type (for SELECT)
CREATE INDEX idx_episodic_space_ts_cover ON episodic_events(space_id, ts DESC, id, event_type);

-- Enhanced covering index for vectors by space with created_at ordering
-- Covers: space_id, created_at (for WHERE and ORDER BY), id, dimension (for SELECT)
CREATE INDEX idx_vectors_space_ts_cover ON vectors(space_id, created_at DESC, id, dimension);

-- Additional covering indexes for common query patterns

-- Episodic events by author with time ordering
CREATE INDEX idx_episodic_author_cover ON episodic_events(author, ts DESC, id, event_type, space_id);

-- Memory events recent activity
CREATE INDEX idx_memory_recent_cover ON memory_events(space_id, timestamp DESC, id, memory_type, memory_content);

-- Vectors by space and item
CREATE INDEX idx_vectors_item_cover ON vectors(item_id, space_id, created_at DESC, id, dimension);

-- Outbox events priority processing
CREATE INDEX idx_outbox_priority_cover ON outbox_events(priority DESC, status, id, event_type, created_at);

-- Episodic events for timeline queries
CREATE INDEX idx_episodic_timeline_cover ON episodic_events(ts DESC, space_id, id, event_type, author);

-- Memory events by content hash (for deduplication)
CREATE INDEX idx_memory_hash_cover ON memory_events(content_hash, space_id, id, memory_type, timestamp);

-- Cross-space queries optimization
CREATE INDEX idx_episodic_cross_cover ON episodic_events(event_type, ts DESC, space_id, id, author);

-- Vector item lookup optimization
CREATE INDEX idx_vectors_lookup_cover ON vectors(item_id, dimension, space_id, id, created_at);
