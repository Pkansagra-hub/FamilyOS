# Contract Change Quick Reference
## Essential Commands & Checklists

### 🚀 Quick Start
```bash
# 1. Validate current state
python scripts/contracts/storage_validate.py

# 2. Make your changes to contracts/
# 3. Create examples and update tests
# 4. Validate changes
python scripts/contracts/storage_validate.py

# 5. Create contract freeze
python scripts/contracts/contracts_freeze.py create v1.x.x-description
```

### 📋 Change Type Decision Tree
```
Is this a breaking change?
├─ YES → MAJOR version (2.0.0)
│   ├─ Field removal
│   ├─ Required field addition
│   ├─ Schema restructure
│   └─ API endpoint removal
│
└─ NO → Minor/Patch version
    ├─ New endpoint → MINOR (1.x.0)
    ├─ Optional field → MINOR (1.x.0)
    ├─ Bug fix → PATCH (1.1.x)
    └─ Documentation → PATCH (1.1.x)
```

### ⚡ Essential Commands

#### Validation
```bash
# Schema-example validation
python scripts/contracts/storage_validate.py

# Envelope invariants check
python scripts/contracts/check_envelope_invariants.py

# ULID format testing
python scripts/contracts/test_ulid.py

# Generate valid ULIDs
python scripts/contracts/gen_ulids.py
```

#### Contract Management
```bash
# Create freeze
python scripts/contracts/contracts_freeze.py create v1.2.0-feature-name

# List all freezes
python scripts/contracts/contracts_freeze.py list

# Compare freezes
python scripts/contracts/contracts_freeze.py diff v1.1.0 v1.2.0

# Restore from freeze (emergency)
python scripts/contracts/contracts_freeze.py restore v1.1.0-stable
```

#### Testing
```bash
# Contract tests only
python -m ward test --path tests/storage/ --pattern "*contract*"

# Full test suite
python -m ward test

# Specific contract test
python -m ward test tests/storage/test_semantic_store_contracts.py
```

### 🔍 Pre-Commit Checklist
- [ ] Schema validates (JSON Schema Draft 2020-12)
- [ ] Examples validate against schemas (0 mismatches)
- [ ] ULIDs use proper Crockford Base32 format
- [ ] API endpoints have 4xx error responses
- [ ] Event schemas include obligations field
- [ ] Tests updated and passing
- [ ] Version number bumped appropriately
- [ ] Contract freeze created

### 🚨 Emergency Procedures

#### Fast Rollback
```bash
# 1. Find last stable freeze
python scripts/contracts/contracts_freeze.py list

# 2. Restore immediately
python scripts/contracts/contracts_freeze.py restore v1.1.0-stable

# 3. Validate restoration
python scripts/contracts/storage_validate.py
```

#### Hotfix Process
```bash
# 1. Minimal change only
# 2. Skip normal approvals for critical issues
# 3. Fast-track CI validation
# 4. Create freeze immediately after merge
```

### 📁 Key File Locations
```
contracts/
├── api/openapi/main.yaml                    # API specs
├── events/envelope.schema.json              # FROZEN INVARIANTS
├── storage/schemas/*.schema.json            # Storage schemas
├── storage/examples/*.example.json          # Valid examples
├── CONTRACT_CHANGE_PROCESS.md               # Full guide
├── CONTRACT_CHANGE_QUICK_REF.md             # This file
└── _frozen/freeze-latest.json               # Latest freeze

scripts/
├── storage_validate.py                     # Main validator
├── contracts_freeze.py                     # Freeze system
├── check_envelope_invariants.py            # Envelope protection
└── gen_ulids.py                            # ULID generator
```

### 🔒 Frozen Envelope Invariants
**NEVER REMOVE THESE FIELDS** from `events/envelope.schema.json`:
- `band`, `obligations`, `policy_version`
- `id`, `ts`, `topic`
- `actor`, `device`, `space_id`
- `qos`, `hashes`, `signature`

### 💡 Common Patterns

#### Adding New Schema
```bash
# 1. Copy template
cp contracts/storage/schemas/template.schema.json contracts/storage/schemas/my_new.schema.json

# 2. Edit schema with proper validation
# 3. Create example
python scripts/gen_ulids.py  # Get valid ULIDs
# Edit contracts/storage/examples/my_new.example.json

# 4. Validate
python scripts/storage_validate.py | grep my_new

# 5. Should show [PASS] for your new schema
```

#### Adding API Endpoint
```yaml
# In contracts/api/openapi/main.yaml
paths:
  /new-endpoint:
    post:
      security:
        - bearerAuth: []
        - mtlsAuth: []
      responses:
        '200':
          description: Success
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '500':
          $ref: '#/components/responses/InternalServerError'
```

#### Version Bumping
```yaml
# contracts/api/openapi/main.yaml
info:
  version: "1.2.0"  # Update this

# contracts/modules/*/versions.yaml
version: "1.2.0"
changes:
  - "Added my_new_feature"
```

---

**Quick Reference Card v1.1.0**
*For detailed procedures, see CONTRACT_CHANGE_PROCESS.md*
