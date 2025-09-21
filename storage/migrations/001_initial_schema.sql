-- Storage Migration 001: Initial Schema
-- Description: Create core storage tables for MemoryOS
-- Epic: M4.3 Storage Hardening
-- Issue: Base schema creation

-- Migration metadata
-- Version: 001
-- Description: Create core storage tables
-- Author: Storage Hardening Plan
-- Date: 2025-09-14

-- =====================================================
-- EPISODIC STORAGE TABLES
-- =====================================================

-- Main episodic events table - following existing episodic_store.py schema
CREATE TABLE IF NOT EXISTS episodic_events (
    id TEXT PRIMARY KEY,
    envelope_id TEXT NOT NULL,
    space_id TEXT NOT NULL,
    ts INTEGER NOT NULL,
    ts_iso TEXT NOT NULL,
    band TEXT NOT NULL CHECK (band IN ('GREEN', 'AMBER', 'RED', 'BLACK')),
    author TEXT NOT NULL,
    device TEXT,
    event_type TEXT NOT NULL,
    event_data TEXT NOT NULL,
    content_json TEXT NOT NULL,
    features_json TEXT NOT NULL,
    mls_group TEXT NOT NULL,
    links_json TEXT,
    meta_json TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'deleted', 'archived')),
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch())
);

-- Episodic sequences table - following existing schema
CREATE TABLE IF NOT EXISTS episodic_sequences (
    sequence_id TEXT PRIMARY KEY,
    space_id TEXT NOT NULL,
    ts INTEGER NOT NULL,
    ts_iso TEXT NOT NULL,
    label TEXT,
    items_json TEXT NOT NULL,
    closed INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch())
);

-- =====================================================
-- VECTOR STORAGE TABLES
-- =====================================================

-- Vector embeddings table for similarity search
CREATE TABLE IF NOT EXISTS vectors (
    id TEXT PRIMARY KEY,
    space_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    embedding BLOB,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch())
);

-- =====================================================
-- MEMORY EVENTS TABLE
-- =====================================================

-- Memory events for consolidation and lifecycle tracking
CREATE TABLE IF NOT EXISTS memory_events (
    id TEXT PRIMARY KEY,
    memory_type TEXT NOT NULL,
    space_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    memory_content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'consolidating', 'consolidated', 'archived')),
    consolidation_status TEXT DEFAULT 'pending',
    created_at INTEGER DEFAULT (unixepoch()),
    updated_at INTEGER DEFAULT (unixepoch())
);

-- =====================================================
-- OUTBOX PATTERN TABLES
-- =====================================================

-- Outbox events table for reliable event publishing
CREATE TABLE IF NOT EXISTS outbox_events (
    id TEXT PRIMARY KEY,
    aggregate_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_data TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at INTEGER,
    error_details TEXT,
    created_at INTEGER DEFAULT (unixepoch()),
    processed_at INTEGER,
    updated_at INTEGER DEFAULT (unixepoch())
);

-- =====================================================
-- BASIC INDEXES FOR CORE FUNCTIONALITY
-- =====================================================

-- Episodic events basic indexes
CREATE INDEX IF NOT EXISTS idx_episodic_events_space_time
ON episodic_events(space_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_episodic_events_author
ON episodic_events(author);

CREATE INDEX IF NOT EXISTS idx_episodic_events_band
ON episodic_events(band);

-- Episodic sequences basic indexes
CREATE INDEX IF NOT EXISTS idx_episodic_sequences_space
ON episodic_sequences(space_id, ts DESC);

-- Vector basic indexes
CREATE INDEX IF NOT EXISTS idx_vectors_space_item
ON vectors(space_id, item_id);

CREATE INDEX IF NOT EXISTS idx_vectors_dimension
ON vectors(dimension);

-- Memory events basic indexes
CREATE INDEX IF NOT EXISTS idx_memory_events_space_time
ON memory_events(space_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_memory_events_type
ON memory_events(memory_type);

-- Outbox basic indexes
CREATE INDEX IF NOT EXISTS idx_outbox_events_status
ON outbox_events(status, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_outbox_events_aggregate
ON outbox_events(aggregate_id);

-- =====================================================
-- STATISTICS UPDATE
-- =====================================================

-- Update SQLite statistics for optimal query planning
ANALYZE episodic_events;
ANALYZE episodic_sequences;
ANALYZE vectors;
ANALYZE memory_events;
ANALYZE outbox_events;

-- Verify schema creation completed successfully
SELECT 'Base schema created successfully' as status;
