# Contract Change Process Guide
## Complete Workflow for MemoryOS Contract Evolution

**Version:** 1.1.0
**Last Updated:** September 12, 2025
**Status:** Production Ready ✅

---

## 🎯 Overview

This guide documents the complete process for making contract changes in MemoryOS, following the Contract Council's "contracts are law" principles. All contract changes must follow this workflow to maintain system integrity and backward compatibility.

## 📋 Quick Reference

| Change Type | Version Bump | Approval Required | Breaking Change? |
|-------------|--------------|-------------------|------------------|
| **API endpoint addition** | Minor (1.x.0) | Tech Lead | No |
| **New optional field** | Patch (1.1.x) | Code Review | No |
| **Required field addition** | Major (2.0.0) | Architecture Board | Yes |
| **Field removal** | Major (2.0.0) | Architecture Board | Yes |
| **Schema restructure** | Major (2.0.0) | Architecture Board | Yes |

---

## 🔄 Complete Workflow

### Phase 1: Preparation & Analysis

#### 1.1 Validate Current State
```bash
# Run contract validation
python scripts/contracts/storage_validate.py

# Check envelope invariants
python scripts/contracts/check_envelope_invariants.py

# Review current freeze
python scripts/contracts/contracts_freeze.py list
```

#### 1.2 Impact Assessment
- [ ] **Breaking change assessment**: Will this break existing clients?
- [ ] **Backward compatibility**: Can old clients still function?
- [ ] **Migration complexity**: How difficult is the upgrade path?
- [ ] **Performance impact**: Will this affect SLOs?

#### 1.3 Version Planning
```yaml
# Determine version bump following SemVer
MAJOR.MINOR.PATCH

# MAJOR: Breaking changes, field removal, schema restructure
# MINOR: New endpoints, optional fields, additive changes
# PATCH: Bug fixes, documentation, non-functional changes
```

### Phase 2: Contract Design

#### 2.1 Schema Design
```bash
# For new schemas
cp contracts/storage/schemas/template.schema.json contracts/storage/schemas/new_schema.schema.json

# Edit with proper JSON Schema Draft 2020-12
# Include all required fields, validation rules, examples
```

#### 2.2 API Design (if applicable)
```yaml
# Update OpenAPI spec
# File: contracts/api/openapi/main.yaml

# Add new endpoints with:
# - Proper security schemes
# - 4xx error responses
# - Request/response schemas
# - Operation descriptions
```

#### 2.3 Event Schema Design (if applicable)
```json
// Update event schemas
// File: contracts/events/schemas/new_event.schema.json

// Ensure envelope compliance:
// - Required obligations field
// - Proper event type
// - Space ID validation
```

### Phase 3: Implementation

#### 3.1 Create Examples
```bash
# Generate valid examples for new schemas
python scripts/contracts/gen_ulids.py  # For proper ULID format

# Create examples:
# contracts/storage/examples/new_schema.example.json
# contracts/events/examples/new_event.example.json
```

#### 3.2 Update Storage Layer
```python
# Update storage implementations
# Files: storage/semantic_store.py, storage/vector_store.py

# Ensure contract compliance:
# - Schema validation on write
# - Proper error handling
# - ULID generation
# - Atomic operations
```

#### 3.3 Update Tests
```python
# Update contract tests
# Files: tests/storage/test_*_contracts.py

# Include:
# - Schema validation tests
# - Contract compliance tests
# - Error condition tests
# - Migration tests (if applicable)
```

### Phase 4: Validation

#### 4.1 Run Contract Validation
```bash
# Full validation suite
python scripts/contracts/storage_validate.py

# Should show 0 mismatches for new schemas
# May show existing drift for unchanged schemas
```

#### 4.2 Syntax Validation
```bash
# Validate JSON schemas
find contracts/ -name "*.json" -exec python -m json.tool {} \; > /dev/null

# Validate YAML files
find contracts/ -name "*.yaml" -exec python -c "import yaml; yaml.safe_load(open('{}'))" \;
```

#### 4.3 Run Tests
```bash
# Run contract tests
python -m ward test --path tests/storage/ --pattern "*contract*"

# Run full test suite if major changes
python -m ward test
```

### Phase 5: Documentation

#### 5.1 Update Version Files
```yaml
# Update module version files
# Example: contracts/modules/*/versions.yaml

version: "1.2.0"
changes:
  - "Added new_field to schema X"
  - "Deprecated old_field (will remove in v2.0)"
migration:
  required: false
  scripts: []
```

#### 5.2 Migration Documentation
```markdown
# For breaking changes, create migration guide
# File: docs/migrations/v1_to_v2_migration.md

## Breaking Changes
- Field X removed from schema Y
- Schema Z restructured

## Migration Steps
1. Update client code to handle new schema
2. Run migration script: `python scripts/contracts/migrate_v1_to_v2.py`
3. Verify data integrity

## Rollback Plan
- Restore from v1.1.x backup
- Run rollback script if needed
```

### Phase 6: Version Bump & Freeze

#### 6.1 Update Version Numbers
```bash
# Update API version
# File: contracts/api/openapi/main.yaml
version: "1.2.0"

# Update affected module versions
# Files: contracts/modules/*/versions.yaml
```

#### 6.2 Create Contract Freeze
```bash
# Create new contract freeze with descriptive version
python scripts/contracts/contracts_freeze.py create v1.2.0-add-new-schema

# This preserves all contract artifacts with SHA256 integrity
```

#### 6.3 Update Changelog
```markdown
# File: contracts/CHANGELOG.md

## [1.2.0] - 2025-09-12

### Added
- New schema for feature X
- Optional field Y to existing schema Z

### Changed
- Improved validation for field A

### Deprecated
- Field B in schema C (will remove in v2.0.0)

### Security
- Enhanced validation for PII fields
```

### Phase 7: CI/CD & Deployment

#### 7.1 Commit Changes
```bash
git add contracts/
git commit -m "feat: add new schema for feature X

- Add new_schema.schema.json with proper validation
- Create example and tests for contract compliance
- Update API to v1.2.0 with backward compatibility
- Freeze contracts at v1.2.0-add-new-schema

Breaking change: false
Migration required: false"
```

#### 7.2 CI Validation
```yaml
# The contract-guard.yml workflow will:
# - Detect contract changes
# - Run validation suite
# - Check envelope invariants
# - Verify syntax
# - Comment on PR with impact assessment
```

#### 7.3 Review Process
- [ ] **Code review**: Technical correctness
- [ ] **Contract review**: Schema design, backward compatibility
- [ ] **Security review**: PII handling, validation rules
- [ ] **Architecture review**: For breaking changes

---

## 🛠️ Tools & Scripts

### Validation Tools
```bash
# Storage schema validation
python scripts/contracts/storage_validate.py

# ULID generation and testing
python scripts/contracts/gen_ulids.py
python scripts/contracts/test_ulid.py

# Field normalization
python scripts/contracts/normalize_fields.py

# Envelope invariant checking
python scripts/contracts/check_envelope_invariants.py
```

### Contract Management
```bash
# Contract freezing
python scripts/contracts/contracts_freeze.py create <version>
python scripts/contracts/contracts_freeze.py list
python scripts/contracts/contracts_freeze.py diff <v1> <v2>

# API enhancement
python scripts/contracts/add_missing_4xx.py
```

### Example Commands
```bash
# Complete validation workflow
./scripts/validate_all_contracts.sh

# Create new schema from template
./scripts/new_schema.sh storage my_new_schema

# Check for breaking changes
./scripts/check_breaking_changes.sh main HEAD
```

---

## 🚨 Emergency Procedures

### Rollback Process
```bash
# 1. Identify last good freeze
python scripts/contracts/contracts_freeze.py list

# 2. Restore contracts from freeze
python scripts/contracts/contracts_freeze.py restore v1.1.0-stable

# 3. Update version numbers back
# 4. Re-run validation
# 5. Deploy rollback
```

### Hotfix Process
```bash
# 1. Create hotfix branch from main
git checkout -b hotfix/critical-schema-fix

# 2. Make minimal fix
# 3. Skip normal approval for critical issues
# 4. Fast-track through CI
# 5. Merge to main and develop
```

---

## 📏 Quality Gates

### Pre-Commit Checklist
- [ ] Schema validates with JSON Schema Draft 2020-12
- [ ] Examples validate against schemas (0 mismatches)
- [ ] ULID format correct (Crockford Base32)
- [ ] API endpoints have 4xx responses
- [ ] Event schemas include obligations field
- [ ] Tests updated and passing
- [ ] Version bumped appropriately
- [ ] Contract freeze created

### Pre-Merge Checklist
- [ ] CI validation passes
- [ ] Code review approved
- [ ] Architecture review (if breaking)
- [ ] Migration plan documented (if needed)
- [ ] Backward compatibility verified
- [ ] Performance impact assessed
- [ ] Security review passed

### Post-Merge Checklist
- [ ] Contract freeze created and verified
- [ ] Documentation updated
- [ ] Migration scripts tested (if applicable)
- [ ] Rollback plan verified
- [ ] Stakeholders notified of changes

---

## 📚 Reference

### Key Files
```
contracts/
├── api/openapi/main.yaml              # API specifications
├── events/envelope.schema.json        # Event envelope (FROZEN INVARIANTS)
├── events/schemas/                    # Event payload schemas
├── storage/schemas/                   # Storage schemas
├── storage/examples/                  # Valid examples
├── CHANGELOG.md                       # Version history
└── _frozen/                          # Contract snapshots

scripts/
├── storage_validate.py               # Schema-example validation
├── contracts_freeze.py               # Contract preservation
├── check_envelope_invariants.py      # Envelope protection
├── gen_ulids.py                      # ULID generation
└── normalize_fields.py               # Field normalization

tests/storage/
├── test_*_contracts.py               # Contract compliance tests
└── contract_test_base.py             # Testing utilities
```

### Frozen Envelope Invariants
These fields in `events/envelope.schema.json` are **FROZEN** and can never be removed:
- `band`, `obligations`, `policy_version`
- `id`, `ts`, `topic`
- `actor`, `device`, `space_id`
- `qos`, `hashes`, `signature`

### SemVer Guidelines
```
1.2.3
│ │ │
│ │ └─ PATCH: Bug fixes, docs, non-breaking changes
│ └─── MINOR: New features, optional fields, additive changes
└───── MAJOR: Breaking changes, field removal, incompatible changes
```

---

## 🎓 Training Examples

### Example 1: Adding Optional Field
```json
// BEFORE (schema v1.1.0)
{
  "type": "object",
  "required": ["id", "name"],
  "properties": {
    "id": {"$ref": "#/$defs/ULID"},
    "name": {"type": "string"}
  }
}

// AFTER (schema v1.2.0) - MINOR bump
{
  "type": "object",
  "required": ["id", "name"],
  "properties": {
    "id": {"$ref": "#/$defs/ULID"},
    "name": {"type": "string"},
    "description": {"type": "string"}  // NEW optional field
  }
}
```

### Example 2: Breaking Change (MAJOR bump required)
```json
// BEFORE (schema v1.2.0)
{
  "required": ["id", "name", "email"]
}

// AFTER (schema v2.0.0) - MAJOR bump required
{
  "required": ["id", "full_name"]  // BREAKING: removed email, renamed name->full_name
}
```

---

**Contract Change Process Guide**
*Making "Contracts Are Law" Operational*
**Contract Council Approved** ✅

---

*For questions or clarifications, contact the Contract Council or Architecture Team.*
