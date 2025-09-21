-- Memory-Centric Family AI - Episodic Memory Storage Schema
-- Core storage schema for episodic memories in the Memory Backbone
-- Supports family context, relationship awareness, and E2EE sync

-- =============================================================================
-- Episodic Memory Tables
-- =============================================================================

-- Core episodic memory storage with family context
CREATE TABLE IF NOT EXISTS episodic_memories (
    -- Identity & Versioning
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version INTEGER NOT NULL DEFAULT 1,
    schema_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',

    -- Ownership & Family Context
    owner_user_id UUID NOT NULL,
    family_id UUID NOT NULL,
    family_member_id UUID NOT NULL,
    relationship_context VARCHAR(100), -- e.g., 'ab', 'abc', 'family'

    -- Memory Classification
    memory_type VARCHAR(20) NOT NULL CHECK (memory_type IN ('episodic', 'semantic', 'procedural', 'working')),
    memory_space VARCHAR(20) NOT NULL CHECK (memory_space IN ('personal', 'selective', 'shared', 'extended', 'interfamily')),
    content_type VARCHAR(50) NOT NULL, -- conversation, photo, event, etc.

    -- Temporal Context
    event_timestamp TIMESTAMPTZ NOT NULL, -- When the original event occurred
    memory_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- When memory was formed
    last_accessed TIMESTAMPTZ,
    last_modified TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Memory Content (Encrypted at rest)
    content_encrypted BYTEA NOT NULL, -- Encrypted memory content
    content_hash VARCHAR(64) NOT NULL, -- SHA-256 hash for integrity
    content_size_bytes INTEGER NOT NULL,

    -- Emotional & Contextual Metadata
    emotional_valence DECIMAL(3,2) CHECK (emotional_valence BETWEEN -1.0 AND 1.0), -- -1 (negative) to 1 (positive)
    emotional_intensity DECIMAL(3,2) CHECK (emotional_intensity BETWEEN 0.0 AND 1.0),
    importance_score DECIMAL(3,2) CHECK (importance_score BETWEEN 0.0 AND 1.0),
    confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0.0 AND 1.0),

    -- Privacy & Security
    encryption_key_id VARCHAR(100) NOT NULL, -- Reference to encryption key
    access_control_hash VARCHAR(64), -- Hash of access control list
    privacy_level VARCHAR(20) NOT NULL CHECK (privacy_level IN ('public', 'family', 'parents_only', 'private')),
    band VARCHAR(10) NOT NULL CHECK (band IN ('GREEN', 'AMBER', 'RED', 'BLACK')),

    -- Consolidation & Lifecycle
    consolidation_stage VARCHAR(20) NOT NULL DEFAULT 'encoding'
        CHECK (consolidation_stage IN ('encoding', 'storage', 'retrieval', 'reconsolidation', 'consolidated', 'forgetting')),
    consolidation_strength DECIMAL(3,2) DEFAULT 0.5 CHECK (consolidation_strength BETWEEN 0.0 AND 1.0),
    forgetting_curve_params JSONB, -- Parameters for Ebbinghaus forgetting curve

    -- Device & Sync Context
    source_device_id VARCHAR(100) NOT NULL,
    sync_status VARCHAR(20) NOT NULL DEFAULT 'local'
        CHECK (sync_status IN ('local', 'syncing', 'synced', 'conflict', 'deleted')),
    sync_vector_clock JSONB, -- Vector clock for CRDT sync
    conflict_resolution_data JSONB,

    -- Family Relationship Context
    participants JSONB, -- Array of family member IDs involved
    witness_members JSONB, -- Array of family members who witnessed/participated
    relationship_tags TEXT[], -- Tags for relationship context
    social_context VARCHAR(50), -- Type of social interaction

    -- Environmental Context
    location_context JSONB, -- Physical/virtual location information
    device_context JSONB, -- Device and environment details
    activity_context JSONB, -- What activity was happening

    -- TTL & Retention
    retention_policy VARCHAR(50) NOT NULL DEFAULT 'family_standard',
    auto_delete_after INTERVAL, -- Automatic deletion interval
    manual_retention_until TIMESTAMPTZ, -- Manual retention override

    -- Audit & Compliance
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ, -- Soft delete timestamp
    audit_trail JSONB, -- Audit information

    -- Performance Optimization
    search_vector tsvector, -- Full-text search vector
    embedding_vector vector(1536), -- Semantic embedding vector (OpenAI ada-002 dimensions)

    -- Constraints
    CONSTRAINT valid_owner_family CHECK (
        (memory_space = 'personal' AND owner_user_id IS NOT NULL) OR
        (memory_space IN ('selective', 'shared', 'extended', 'interfamily') AND family_id IS NOT NULL)
    ),

    CONSTRAINT valid_memory_timestamps CHECK (event_timestamp <= memory_timestamp),
    CONSTRAINT valid_emotional_context CHECK (
        (emotional_valence IS NULL AND emotional_intensity IS NULL) OR
        (emotional_valence IS NOT NULL AND emotional_intensity IS NOT NULL)
    )
);

-- Memory associations for building memory networks
CREATE TABLE IF NOT EXISTS episodic_memory_associations (
    association_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Association endpoints
    source_memory_id UUID NOT NULL REFERENCES episodic_memories(memory_id) ON DELETE CASCADE,
    target_memory_id UUID NOT NULL REFERENCES episodic_memories(memory_id) ON DELETE CASCADE,

    -- Association properties
    association_type VARCHAR(50) NOT NULL, -- causal, temporal, semantic, emotional, etc.
    association_strength DECIMAL(3,2) NOT NULL DEFAULT 0.5 CHECK (association_strength BETWEEN 0.0 AND 1.0),
    association_direction VARCHAR(20) NOT NULL DEFAULT 'bidirectional'
        CHECK (association_direction IN ('forward', 'backward', 'bidirectional')),

    -- Family & Context
    family_id UUID NOT NULL,
    created_by_user_id UUID NOT NULL,

    -- Temporal context
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_strengthened TIMESTAMPTZ,

    -- Association metadata
    association_metadata JSONB,
    confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0.0 AND 1.0),

    -- Prevent self-associations and duplicates
    CONSTRAINT no_self_association CHECK (source_memory_id != target_memory_id),
    CONSTRAINT unique_association UNIQUE (source_memory_id, target_memory_id, association_type)
);

-- Memory access log for auditing and learning
CREATE TABLE IF NOT EXISTS episodic_memory_access_log (
    access_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Memory and user context
    memory_id UUID NOT NULL REFERENCES episodic_memories(memory_id) ON DELETE CASCADE,
    accessed_by_user_id UUID NOT NULL,
    family_member_id UUID NOT NULL,

    -- Access details
    access_type VARCHAR(20) NOT NULL CHECK (access_type IN ('read', 'write', 'delete', 'share', 'sync')),
    access_method VARCHAR(50) NOT NULL, -- api, search, association, reminder, etc.
    device_id VARCHAR(100),

    -- Context
    query_context JSONB, -- Search query or access context
    result_relevance DECIMAL(3,2) CHECK (result_relevance BETWEEN 0.0 AND 1.0),

    -- Family relationship
    relationship_context VARCHAR(100),
    family_id UUID NOT NULL,

    -- Timing
    access_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    response_time_ms INTEGER,

    -- Privacy and permissions
    permission_level VARCHAR(20),
    access_granted BOOLEAN NOT NULL,
    denial_reason VARCHAR(200),

    -- Learning signals
    user_satisfaction DECIMAL(3,2) CHECK (user_satisfaction BETWEEN 0.0 AND 1.0),
    memory_usefulness DECIMAL(3,2) CHECK (memory_usefulness BETWEEN 0.0 AND 1.0)
);

-- Family memory permissions for selective sharing
CREATE TABLE IF NOT EXISTS episodic_memory_permissions (
    permission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Memory and permission details
    memory_id UUID NOT NULL REFERENCES episodic_memories(memory_id) ON DELETE CASCADE,
    family_id UUID NOT NULL,

    -- Grantee information
    grantee_user_id UUID, -- Specific user
    grantee_family_role VARCHAR(20), -- Role-based permission
    grantee_relationship VARCHAR(100), -- Relationship-based permission

    -- Permission details
    permission_type VARCHAR(20) NOT NULL CHECK (permission_type IN ('read', 'write', 'share', 'delete', 'admin')),
    granted_by_user_id UUID NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Permission constraints
    expires_at TIMESTAMPTZ,
    conditions JSONB, -- Additional permission conditions
    revoked_at TIMESTAMPTZ,
    revoked_by_user_id UUID,

    -- Context
    grant_reason VARCHAR(200),
    permission_scope JSONB, -- Scope limitations

    CONSTRAINT valid_grantee CHECK (
        (grantee_user_id IS NOT NULL) OR
        (grantee_family_role IS NOT NULL) OR
        (grantee_relationship IS NOT NULL)
    )
);

-- Memory consolidation tracking
CREATE TABLE IF NOT EXISTS episodic_memory_consolidation (
    consolidation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Memory reference
    memory_id UUID NOT NULL REFERENCES episodic_memories(memory_id) ON DELETE CASCADE,
    family_id UUID NOT NULL,

    -- Consolidation process
    consolidation_stage VARCHAR(20) NOT NULL,
    previous_stage VARCHAR(20),
    stage_entered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Hippocampal processing
    hippocampal_pattern_id UUID, -- Reference to hippocampal pattern
    cortical_binding_strength DECIMAL(3,2) CHECK (cortical_binding_strength BETWEEN 0.0 AND 1.0),
    pattern_separation_score DECIMAL(3,2) CHECK (pattern_separation_score BETWEEN 0.0 AND 1.0),
    pattern_completion_score DECIMAL(3,2) CHECK (pattern_completion_score BETWEEN 0.0 AND 1.0),

    -- Sleep-like consolidation
    consolidation_cycles INTEGER DEFAULT 0,
    replay_strength DECIMAL(3,2) CHECK (replay_strength BETWEEN 0.0 AND 1.0),
    integration_score DECIMAL(3,2) CHECK (integration_score BETWEEN 0.0 AND 1.0),

    -- Family memory integration
    family_relevance_score DECIMAL(3,2) CHECK (family_relevance_score BETWEEN 0.0 AND 1.0),
    relationship_integration JSONB, -- How memory integrates with family relationships

    -- Processing metadata
    processing_metadata JSONB,
    consolidation_errors JSONB,

    -- Performance tracking
    processing_duration_ms INTEGER,
    cpu_time_ms INTEGER,
    memory_usage_bytes BIGINT
);

-- =============================================================================
-- Indexes for Performance
-- =============================================================================

-- Core lookup indexes
CREATE INDEX IF NOT EXISTS idx_episodic_memories_owner_family
ON episodic_memories(owner_user_id, family_id);

CREATE INDEX IF NOT EXISTS idx_episodic_memories_family_space
ON episodic_memories(family_id, memory_space);

CREATE INDEX IF NOT EXISTS idx_episodic_memories_relationship_context
ON episodic_memories(family_id, relationship_context);

-- Temporal indexes
CREATE INDEX IF NOT EXISTS idx_episodic_memories_event_time
ON episodic_memories(event_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_episodic_memories_memory_time
ON episodic_memories(memory_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_episodic_memories_last_accessed
ON episodic_memories(last_accessed DESC) WHERE last_accessed IS NOT NULL;

-- Search and retrieval indexes
CREATE INDEX IF NOT EXISTS idx_episodic_memories_search_vector
ON episodic_memories USING gin(search_vector);

CREATE INDEX IF NOT EXISTS idx_episodic_memories_embedding_vector
ON episodic_memories USING ivfflat(embedding_vector vector_cosine_ops) WITH (lists = 100);

-- Content and metadata indexes
CREATE INDEX IF NOT EXISTS idx_episodic_memories_content_type
ON episodic_memories(content_type, family_id);

CREATE INDEX IF NOT EXISTS idx_episodic_memories_emotional_context
ON episodic_memories(emotional_valence, emotional_intensity)
WHERE emotional_valence IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_episodic_memories_importance
ON episodic_memories(importance_score DESC) WHERE importance_score IS NOT NULL;

-- Privacy and security indexes
CREATE INDEX IF NOT EXISTS idx_episodic_memories_privacy_band
ON episodic_memories(privacy_level, band);

CREATE INDEX IF NOT EXISTS idx_episodic_memories_consolidation
ON episodic_memories(consolidation_stage, consolidation_strength);

-- Sync and device indexes
CREATE INDEX IF NOT EXISTS idx_episodic_memories_sync_status
ON episodic_memories(sync_status, source_device_id);

CREATE INDEX IF NOT EXISTS idx_episodic_memories_device_family
ON episodic_memories(source_device_id, family_id);

-- TTL and retention indexes
CREATE INDEX IF NOT EXISTS idx_episodic_memories_retention
ON episodic_memories(auto_delete_after, manual_retention_until)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_episodic_memories_soft_delete
ON episodic_memories(deleted_at) WHERE deleted_at IS NOT NULL;

-- Association indexes
CREATE INDEX IF NOT EXISTS idx_episodic_associations_source
ON episodic_memory_associations(source_memory_id, association_type);

CREATE INDEX IF NOT EXISTS idx_episodic_associations_target
ON episodic_memory_associations(target_memory_id, association_type);

CREATE INDEX IF NOT EXISTS idx_episodic_associations_strength
ON episodic_memory_associations(association_strength DESC);

CREATE INDEX IF NOT EXISTS idx_episodic_associations_family
ON episodic_memory_associations(family_id, created_at DESC);

-- Access log indexes
CREATE INDEX IF NOT EXISTS idx_episodic_access_log_memory_time
ON episodic_memory_access_log(memory_id, access_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_episodic_access_log_user_time
ON episodic_memory_access_log(accessed_by_user_id, access_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_episodic_access_log_family_time
ON episodic_memory_access_log(family_id, access_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_episodic_access_log_access_type
ON episodic_memory_access_log(access_type, access_granted);

-- Permission indexes
CREATE INDEX IF NOT EXISTS idx_episodic_permissions_memory
ON episodic_memory_permissions(memory_id, permission_type)
WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_episodic_permissions_grantee
ON episodic_memory_permissions(grantee_user_id, permission_type)
WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_episodic_permissions_family_role
ON episodic_memory_permissions(family_id, grantee_family_role, permission_type)
WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_episodic_permissions_expiry
ON episodic_memory_permissions(expires_at)
WHERE expires_at IS NOT NULL AND revoked_at IS NULL;

-- Consolidation indexes
CREATE INDEX IF NOT EXISTS idx_episodic_consolidation_memory
ON episodic_memory_consolidation(memory_id, consolidation_stage);

CREATE INDEX IF NOT EXISTS idx_episodic_consolidation_stage_time
ON episodic_memory_consolidation(consolidation_stage, stage_entered_at);

CREATE INDEX IF NOT EXISTS idx_episodic_consolidation_family_relevance
ON episodic_memory_consolidation(family_id, family_relevance_score DESC);

-- =============================================================================
-- Views for Common Queries
-- =============================================================================

-- Active family memories view
CREATE OR REPLACE VIEW family_active_memories AS
SELECT
    m.*,
    ma.access_timestamp as last_family_access,
    mc.consolidation_stage,
    mc.family_relevance_score
FROM episodic_memories m
LEFT JOIN episodic_memory_access_log ma ON m.memory_id = ma.memory_id
    AND ma.access_timestamp = (
        SELECT MAX(access_timestamp)
        FROM episodic_memory_access_log ma2
        WHERE ma2.memory_id = m.memory_id
    )
LEFT JOIN episodic_memory_consolidation mc ON m.memory_id = mc.memory_id
    AND mc.stage_entered_at = (
        SELECT MAX(stage_entered_at)
        FROM episodic_memory_consolidation mc2
        WHERE mc2.memory_id = m.memory_id
    )
WHERE m.deleted_at IS NULL
    AND m.sync_status != 'deleted'
    AND (m.auto_delete_after IS NULL OR m.created_at + m.auto_delete_after > NOW())
    AND (m.manual_retention_until IS NULL OR m.manual_retention_until > NOW());

-- Memory association network view
CREATE OR REPLACE VIEW memory_association_network AS
SELECT
    ma.association_id,
    ma.source_memory_id,
    ma.target_memory_id,
    ma.association_type,
    ma.association_strength,
    m1.content_type as source_content_type,
    m1.emotional_valence as source_emotion,
    m1.memory_space as source_space,
    m2.content_type as target_content_type,
    m2.emotional_valence as target_emotion,
    m2.memory_space as target_space,
    ma.family_id,
    ma.created_at as association_created
FROM episodic_memory_associations ma
JOIN episodic_memories m1 ON ma.source_memory_id = m1.memory_id
JOIN episodic_memories m2 ON ma.target_memory_id = m2.memory_id
WHERE m1.deleted_at IS NULL AND m2.deleted_at IS NULL;

-- Family memory permissions summary
CREATE OR REPLACE VIEW family_memory_access_summary AS
SELECT
    p.family_id,
    p.memory_id,
    m.content_type,
    m.memory_space,
    m.privacy_level,
    array_agg(DISTINCT p.grantee_user_id) FILTER (WHERE p.grantee_user_id IS NOT NULL) as individual_access,
    array_agg(DISTINCT p.grantee_family_role) FILTER (WHERE p.grantee_family_role IS NOT NULL) as role_access,
    array_agg(DISTINCT p.grantee_relationship) FILTER (WHERE p.grantee_relationship IS NOT NULL) as relationship_access,
    count(*) as total_permissions
FROM episodic_memory_permissions p
JOIN episodic_memories m ON p.memory_id = m.memory_id
WHERE p.revoked_at IS NULL
    AND (p.expires_at IS NULL OR p.expires_at > NOW())
    AND m.deleted_at IS NULL
GROUP BY p.family_id, p.memory_id, m.content_type, m.memory_space, m.privacy_level;

-- =============================================================================
-- Functions for Memory Operations
-- =============================================================================

-- Function to update search vector when content changes
CREATE OR REPLACE FUNCTION update_memory_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    -- Update search vector based on decrypted content (handled by application)
    -- This trigger is called after content decryption in application layer
    IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND NEW.content_encrypted != OLD.content_encrypted) THEN
        -- Search vector will be updated by application after decryption
        NEW.updated_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to enforce memory retention policies
CREATE OR REPLACE FUNCTION enforce_memory_retention()
RETURNS TRIGGER AS $$
BEGIN
    -- Set deletion timestamp if retention period exceeded
    IF NEW.auto_delete_after IS NOT NULL THEN
        IF NEW.created_at + NEW.auto_delete_after < NOW() THEN
            NEW.deleted_at = NOW();
            NEW.sync_status = 'deleted';
        END IF;
    END IF;

    -- Respect manual retention override
    IF NEW.manual_retention_until IS NOT NULL AND NEW.manual_retention_until <= NOW() THEN
        NEW.deleted_at = NOW();
        NEW.sync_status = 'deleted';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to strengthen memory associations on access
CREATE OR REPLACE FUNCTION strengthen_memory_associations()
RETURNS TRIGGER AS $$
BEGIN
    -- Strengthen associations when memory is accessed
    IF NEW.access_type = 'read' AND NEW.access_granted = true THEN
        UPDATE episodic_memory_associations
        SET
            association_strength = LEAST(1.0, association_strength + 0.1),
            last_strengthened = NOW()
        WHERE source_memory_id = NEW.memory_id
           OR target_memory_id = NEW.memory_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Triggers
-- =============================================================================

-- Update search vector trigger
CREATE TRIGGER trigger_update_memory_search_vector
    BEFORE INSERT OR UPDATE ON episodic_memories
    FOR EACH ROW EXECUTE FUNCTION update_memory_search_vector();

-- Retention policy enforcement trigger
CREATE TRIGGER trigger_enforce_memory_retention
    BEFORE UPDATE ON episodic_memories
    FOR EACH ROW EXECUTE FUNCTION enforce_memory_retention();

-- Association strengthening trigger
CREATE TRIGGER trigger_strengthen_memory_associations
    AFTER INSERT ON episodic_memory_access_log
    FOR EACH ROW EXECUTE FUNCTION strengthen_memory_associations();

-- =============================================================================
-- Comments and Documentation
-- =============================================================================

-- Table comments
COMMENT ON TABLE episodic_memories IS 'Core episodic memory storage with family context, E2EE encryption, and relationship awareness';
COMMENT ON TABLE episodic_memory_associations IS 'Memory association network for building connected memory graphs';
COMMENT ON TABLE episodic_memory_access_log IS 'Audit log for memory access patterns and learning signals';
COMMENT ON TABLE episodic_memory_permissions IS 'Fine-grained permission system for family memory sharing';
COMMENT ON TABLE episodic_memory_consolidation IS 'Memory consolidation tracking with hippocampal processing metadata';

-- Key column comments
COMMENT ON COLUMN episodic_memories.memory_space IS 'Memory accessibility scope: personal → selective → shared → extended → interfamily';
COMMENT ON COLUMN episodic_memories.relationship_context IS 'Active family relationship context (e.g., ab=pair, abc=trio, family=all)';
COMMENT ON COLUMN episodic_memories.content_encrypted IS 'E2EE encrypted memory content, decrypted only on authorized devices';
COMMENT ON COLUMN episodic_memories.consolidation_stage IS 'Hippocampal consolidation stage following neuroscience research';
COMMENT ON COLUMN episodic_memories.sync_vector_clock IS 'CRDT vector clock for conflict-free family memory sync';
COMMENT ON COLUMN episodic_memories.embedding_vector IS 'Semantic embedding for similarity search and memory retrieval';

-- Performance and usage notes
COMMENT ON INDEX idx_episodic_memories_embedding_vector IS 'Vector similarity index for semantic memory retrieval - tune lists parameter based on data size';
COMMENT ON VIEW family_active_memories IS 'Optimized view for active family memories excluding deleted and expired entries';
COMMENT ON FUNCTION update_memory_search_vector IS 'Updates full-text search vector after content encryption/decryption in application layer';

-- =============================================================================
-- Schema Version and Migration Support
-- =============================================================================

-- Schema version tracking
CREATE TABLE IF NOT EXISTS episodic_schema_versions (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description TEXT,
    migration_script TEXT
);

-- Insert current schema version
INSERT INTO episodic_schema_versions (version, description)
VALUES ('1.0.0', 'Initial episodic memory schema with family context and E2EE support')
ON CONFLICT (version) DO NOTHING;
