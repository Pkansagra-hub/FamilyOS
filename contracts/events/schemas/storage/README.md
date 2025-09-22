# Storage Event Schemas

This directory contains JSON Schema definitions for all MemoryOS Storage service events.
These schemas provide validation, documentation, and type safety for event-driven
communication across the MemoryOS ecosystem.

## Schema Organization

### Base Schemas
- `base_event.json` - Common fields for all storage events
- `error_details.json` - Standard error detail structure
- `store_reference.json` - Store identification and metadata

### Transaction Event Schemas
- `transaction_started.json` - Transaction initiation events
- `transaction_prepared.json` - Two-phase commit prepare events
- `transaction_committed.json` - Successful transaction completion
- `transaction_rolled_back.json` - Transaction rollback events
- `transaction_failed.json` - Transaction failure events

### Migration Event Schemas
- `migration_started.json` - Schema migration initiation
- `migration_completed.json` - Successful migration completion
- `migration_failed.json` - Migration failure events

### Policy Event Schemas
- `policy_violation.json` - Policy violation detection
- `policy_enforced.json` - Policy enforcement actions

### Performance Event Schemas
- `performance_degraded.json` - SLA breach notifications
- `performance_recovered.json` - Performance recovery events
- `performance_alert.json` - Performance warnings and alerts

### Backup Event Schemas
- `backup_started.json` - Backup operation initiation
- `backup_completed.json` - Successful backup completion
- `backup_failed.json` - Backup failure events

### Coordination Event Schemas
- `coordination_started.json` - Cross-store coordination initiation
- `coordination_completed.json` - Coordination completion
- `consistency_violation.json` - Consistency violation detection

## Schema Validation

All schemas follow JSON Schema Draft 2020-12 specification with:
- Strict validation rules
- Comprehensive examples
- Detailed descriptions
- Format validation
- Pattern matching
- Enum constraints

## Usage

These schemas are used for:
- Event validation at publish/consume time
- API documentation generation
- Code generation for event types
- Integration testing
- Contract validation

## Integration

Event schemas integrate with:
- AsyncAPI specification (`../asyncapi/storage.yaml`)
- OpenAPI contracts (`../api/`)
- Event bus infrastructure
- Schema registry services
- Monitoring and observability systems
