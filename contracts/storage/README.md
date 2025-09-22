# FamilyOS Storage Contracts (v1.2)

This bundle contains JSON Schemas for the storages enumerated in the MemoryOS architecture.
Every schema uses Draft 2020-12 and shares common types from `common.schema.json`.

**Enhanced in v1.2:**
- Enhanced Unit of Work with performance monitoring and transaction receipts
- Migration system contracts for schema evolution
- SQLite optimization and connection pooling contracts
- Performance monitoring and health check schemas

**Stores covered** (mapping → schema):
- episodic_store → `episodic_record.schema.json`, `episodic_sequence.schema.json`
- fts_store → `fts_document.schema.json`
- vector_store → `vector_row.schema.json`
- embeddings_store → `embedding_record.schema.json`
- semantic_store → `semantic_item.schema.json`
- blob_store → `blob_manifest.schema.json`
- receipts_store → `write_receipt.schema.json`
- secure_store → `secure_item.schema.json`
- kg_store → `kg_entity.schema.json`, `kg_edge.schema.json`
- crdt_store → `crdt_log_entry.schema.json` + base `contracts/storage/crdt.schema.json`
- workspace_store → `workspace_state.schema.json`
- metacog_store → `metacog_report.schema.json`
- prospective_store → `prospective_task.schema.json`
- drives_store → `drives_state.schema.json`, `reward_event.schema.json`
- imagination_store → `imagination_snapshot.schema.json`
- affect_store → `affect_state.schema.json`
- hippocampus_store → `hippocampus_trace.schema.json`
- privacy_store → `privacy_request.schema.json`, `tombstone_record.schema.json`
- ml_store → `ml_run.schema.json`, `metric_point.schema.json`
- registries_store → `registry_tool.schema.json`, `registry_prompt.schema.json`, `rbac_role.schema.json`, `rbac_binding.schema.json`
- tiered_memory_service → `tiered_locator.schema.json`
- **unit_of_work → `unit_of_work_enhanced.schema.json` (v1.1+)**
- **migration_system → `migration_record.schema.json` (v1.0+)**
- pattern_detector → `pattern_detection.schema.json`
- index checkpoints (P13) → `index_checkpoint.schema.json`

**Migration Contracts:**
- storage-uow-enhancement-v1_1_0.md → Enhanced Unit of Work migration
- storage-sqlite-enhancement-v1_2_0.md → SQLite optimization migration

All IDs are ULIDs unless noted. `space_id` matches the memory space pattern.
Where applicable, fields align with the event `Envelope` contract.

## Contract Validation

Enhanced storage contracts include:
- **Performance Requirements**: SLO definitions and monitoring contracts
- **Error Handling**: Standardized error response schemas
- **Migration Safety**: Version control and rollback procedures
- **Receipt Integrity**: Cryptographic verification schemas
- **Health Monitoring**: Database health and performance metrics
