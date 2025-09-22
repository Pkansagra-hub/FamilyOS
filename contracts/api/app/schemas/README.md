# App Plane Schemas

This directory contains shared schemas for the App Plane APIs. These schemas follow the memory-centric architecture and family-aware design principles.

## Schema Categories

### Family-Aware Core Schemas
- `family_context.schema.json` - Family member and relationship schemas
- `device_coordination.schema.json` - Device management and family network schemas
- `memory_integration.schema.json` - Memory space and family intelligence schemas
- `privacy_boundaries.schema.json` - Family privacy and access control schemas

### Third-Party Integration Schemas
- `connector_management.schema.json` - App connector lifecycle and OAuth2 schemas
- `webhook_configuration.schema.json` - Webhook delivery and family coordination schemas
- `capability_discovery.schema.json` - App capability and family compatibility schemas

### Notification and Communication Schemas
- `notification_delivery.schema.json` - Family notification coordination schemas
- `presence_awareness.schema.json` - Family presence and availability schemas
- `emergency_protocols.schema.json` - Emergency alert and escalation schemas

### Data Management Schemas
- `family_data_governance.schema.json` - Data privacy and family consent schemas
- `sync_coordination.schema.json` - Cross-device family sync schemas
- `audit_tracking.schema.json` - Family activity and compliance schemas

## Usage Guidelines

1. **Memory-Centric Design**: All schemas integrate with the Family AI memory backbone
2. **Family Privacy**: Respect layered privacy boundaries (personal/selective/shared/extended/interfamily)
3. **Child Safety**: Include age-appropriate content filtering and parental controls
4. **Device Coordination**: Enable seamless family device ecosystem integration
5. **Relationship Awareness**: Consider family relationships in all data structures

## Schema Validation

All schemas follow JSON Schema Draft 2020-12 and include:
- Comprehensive validation rules
- Family-aware constraints
- Privacy protection annotations
- Memory integration metadata
- Cross-domain intelligence markers
