# Storage Migration: Unit of Work Enhancement (v1.0.0 → v1.1.0)

**Migration ID**: `storage-uow-enhancement-v1_1_0`
**Version**: 1.1.0
**Description**: Enhance Unit of Work with performance monitoring, receipts, and comprehensive error handling
**Author**: MemoryOS Migration System
**Created**: 2025-09-13

## Overview

This migration enhances the Unit of Work system with:
- Performance monitoring and analytics
- Comprehensive transaction receipts
- Enhanced error handling and recovery
- Contract compliance validation
- Improved observability

## Schema Changes

### New Fields Added to `unit_of_work` table:

```sql
-- Performance metrics
ALTER TABLE unit_of_work ADD COLUMN total_execution_time_ms INTEGER DEFAULT 0;
ALTER TABLE unit_of_work ADD COLUMN commit_time_ms INTEGER DEFAULT 0;
ALTER TABLE unit_of_work ADD COLUMN store_count INTEGER DEFAULT 0;
ALTER TABLE unit_of_work ADD COLUMN total_bytes_written INTEGER DEFAULT 0;
ALTER TABLE unit_of_work ADD COLUMN retry_count INTEGER DEFAULT 0;

-- Error tracking
ALTER TABLE unit_of_work ADD COLUMN error_type TEXT;
ALTER TABLE unit_of_work ADD COLUMN error_message TEXT;
ALTER TABLE unit_of_work ADD COLUMN failed_store TEXT;
ALTER TABLE unit_of_work ADD COLUMN error_ts TEXT;
ALTER TABLE unit_of_work ADD COLUMN recovery_attempted INTEGER DEFAULT 0;

-- Receipt and verification
ALTER TABLE unit_of_work ADD COLUMN receipt_hash TEXT;
ALTER TABLE unit_of_work ADD COLUMN receipt_signature TEXT;

-- Context and tracing
ALTER TABLE unit_of_work ADD COLUMN space_id TEXT;
ALTER TABLE unit_of_work ADD COLUMN actor_id TEXT;
ALTER TABLE unit_of_work ADD COLUMN device_id TEXT;
ALTER TABLE unit_of_work ADD COLUMN correlation_id TEXT;
ALTER TABLE unit_of_work ADD COLUMN band TEXT;
ALTER TABLE unit_of_work ADD COLUMN contract_version TEXT DEFAULT '1.1.0';
```

### Enhanced `writes` table structure:

```sql
-- Add new fields to track operation details
ALTER TABLE uow_writes ADD COLUMN operation_type TEXT DEFAULT 'create';
ALTER TABLE uow_writes ADD COLUMN bytes_written INTEGER DEFAULT 0;
ALTER TABLE uow_writes ADD COLUMN checksum TEXT;
```

## Migration SQL

### Forward Migration (UP)

```sql
-- Add performance metrics columns
ALTER TABLE unit_of_work ADD COLUMN total_execution_time_ms INTEGER DEFAULT 0;
ALTER TABLE unit_of_work ADD COLUMN commit_time_ms INTEGER DEFAULT 0;
ALTER TABLE unit_of_work ADD COLUMN store_count INTEGER DEFAULT 0;
ALTER TABLE unit_of_work ADD COLUMN total_bytes_written INTEGER DEFAULT 0;
ALTER TABLE unit_of_work ADD COLUMN retry_count INTEGER DEFAULT 0;

-- Add error tracking columns
ALTER TABLE unit_of_work ADD COLUMN error_type TEXT;
ALTER TABLE unit_of_work ADD COLUMN error_message TEXT;
ALTER TABLE unit_of_work ADD COLUMN failed_store TEXT;
ALTER TABLE unit_of_work ADD COLUMN error_ts TEXT;
ALTER TABLE unit_of_work ADD COLUMN recovery_attempted INTEGER DEFAULT 0;

-- Add receipt and verification columns
ALTER TABLE unit_of_work ADD COLUMN receipt_hash TEXT;
ALTER TABLE unit_of_work ADD COLUMN receipt_signature TEXT;

-- Add context and tracing columns
ALTER TABLE unit_of_work ADD COLUMN space_id TEXT;
ALTER TABLE unit_of_work ADD COLUMN actor_id TEXT;
ALTER TABLE unit_of_work ADD COLUMN device_id TEXT;
ALTER TABLE unit_of_work ADD COLUMN correlation_id TEXT;
ALTER TABLE unit_of_work ADD COLUMN band TEXT CHECK (band IN ('GREEN', 'AMBER', 'RED', 'BLACK'));
ALTER TABLE unit_of_work ADD COLUMN contract_version TEXT DEFAULT '1.1.0';

-- Enhance writes table if it exists
ALTER TABLE uow_writes ADD COLUMN operation_type TEXT DEFAULT 'create' CHECK (operation_type IN ('create', 'update', 'delete', 'upsert'));
ALTER TABLE uow_writes ADD COLUMN bytes_written INTEGER DEFAULT 0;
ALTER TABLE uow_writes ADD COLUMN checksum TEXT;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_uow_space_id ON unit_of_work(space_id);
CREATE INDEX IF NOT EXISTS idx_uow_actor_id ON unit_of_work(actor_id);
CREATE INDEX IF NOT EXISTS idx_uow_band ON unit_of_work(band);
CREATE INDEX IF NOT EXISTS idx_uow_status_created ON unit_of_work(status, created_ts);
CREATE INDEX IF NOT EXISTS idx_uow_correlation_id ON unit_of_work(correlation_id);

-- Update existing records to have contract version
UPDATE unit_of_work SET contract_version = '1.1.0' WHERE contract_version IS NULL;
```

### Backward Migration (DOWN)

```sql
-- Remove indexes
DROP INDEX IF EXISTS idx_uow_space_id;
DROP INDEX IF EXISTS idx_uow_actor_id;
DROP INDEX IF EXISTS idx_uow_band;
DROP INDEX IF EXISTS idx_uow_status_created;
DROP INDEX IF EXISTS idx_uow_correlation_id;

-- Note: SQLite doesn't support DROP COLUMN, so we create a new table
-- and copy data back for true rollback (implement if needed)

-- For now, we'll set columns to NULL to effectively disable them
UPDATE unit_of_work SET
  total_execution_time_ms = NULL,
  commit_time_ms = NULL,
  store_count = NULL,
  total_bytes_written = NULL,
  retry_count = NULL,
  error_type = NULL,
  error_message = NULL,
  failed_store = NULL,
  error_ts = NULL,
  recovery_attempted = NULL,
  receipt_hash = NULL,
  receipt_signature = NULL,
  space_id = NULL,
  actor_id = NULL,
  device_id = NULL,
  correlation_id = NULL,
  band = NULL,
  contract_version = '1.0.0';

-- Revert writes table changes
UPDATE uow_writes SET
  operation_type = NULL,
  bytes_written = NULL,
  checksum = NULL;
```

## Contract Validation

### Required Validations:
1. **Performance Metrics**: All execution times must be non-negative
2. **Error Consistency**: If status is 'failed', error_type must be present
3. **Receipt Integrity**: receipt_hash must be valid SHA-256 if present
4. **Band Validation**: band must be one of GREEN, AMBER, RED, BLACK
5. **Contract Version**: Must follow semantic versioning pattern

### Validation Queries:
```sql
-- Check for invalid metrics
SELECT COUNT(*) FROM unit_of_work WHERE total_execution_time_ms < 0 OR commit_time_ms < 0;

-- Check error consistency
SELECT COUNT(*) FROM unit_of_work WHERE status = 'failed' AND error_type IS NULL;

-- Check receipt hash format
SELECT COUNT(*) FROM unit_of_work WHERE receipt_hash IS NOT NULL AND length(receipt_hash) != 64;

-- Check band values
SELECT COUNT(*) FROM unit_of_work WHERE band IS NOT NULL AND band NOT IN ('GREEN', 'AMBER', 'RED', 'BLACK');
```

## Breaking Changes

**None** - This is a backward-compatible enhancement that adds new optional fields.

## Dependencies

- Requires Enhanced Unit of Work implementation (`storage/unit_of_work.py` v1.1.0+)
- Requires SQLite Enhanced manager for connection pooling
- Compatible with existing storage contracts

## Performance Impact

- **Positive**: Enhanced indexing improves query performance
- **Storage**: Approximately 20% increase in storage per UoW record
- **Query Performance**: New indexes improve filtering by space, actor, band

## Testing Requirements

1. **Schema Validation**: All new fields accept expected data types
2. **Constraint Testing**: Check constraints work properly
3. **Index Performance**: Verify query performance improvements
4. **Backward Compatibility**: Existing UoW records still function
5. **Contract Compliance**: Enhanced UoW implementation validates against new schema

## Rollback Strategy

If issues are discovered:
1. Set new fields to NULL to disable enhanced features
2. Application can fall back to basic UoW functionality
3. Full schema rollback requires table recreation (implement if needed)

## Contract Integration

This migration updates:
- `contracts/storage/schemas/unit_of_work_enhanced.schema.json`
- Storage interface documentation
- Unit of Work contract validation rules
- Performance monitoring expectations
