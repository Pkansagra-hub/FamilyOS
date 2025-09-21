````prompt
# 📋 Event Envelope Schema Audit Prompts

Use these prompts when validating and maintaining the event envelope schema with strict invariant preservation.

---

## 🔍 **Envelope Schema Validation & Audit**

```
I need to validate and potentially fix the event envelope schema while preserving all invariants:

**Schema Context:**
- **Schema File:** `contracts/events/envelope.schema.json`
- **Current Issues:** [List any validation errors or concerns]
- **Recent Changes:** [What modifications were made recently]
- **Validation Target:** JSON Schema 2020-12 compliance

**Critical Invariants (MUST BE PRESERVED):**
All these fields must exist or be derivable:
- `band` - Security band classification
- `obligations` - Policy enforcement requirements
- `policy_version` - Policy schema version
- `id` - Event identifier (ULID OR UUID)
- `ts` - Timestamp (ISO 8601)
- `topic` - Event topic/category
- `actor` - Event originator
- `device` - Device identifier
- `space_id` - Space scope identifier
- `qos` - Quality of service level
- `hashes` - Content integrity hashes
- `signature` - Cryptographic signature

**Conditional Logic Requirements:**
1. **MLS Group Requirement:**
   - IF band = AMBER|RED|BLACK
   - THEN `mls_group` field is required

2. **Tombstone Obligations:**
   - IF topic = TOMBSTONE_APPLIED
   - THEN `obligations` contains `TOMBSTONE_ON_DELETE`

3. **Audit Access Requirements:**
   - IF topic = DSAR_EXPORT|SAFETY_BAND_CHANGED|MEMORY_RECEIPT_CREATED
   - THEN `obligations` contains `AUDIT_ACCESS`

**Schema Format Requirements:**
- `$schema`: JSON Schema 2020-12
- `$id`: Proper schema identifier
- `$defs`: Reusable schema definitions
- `ingest_ts`: May be null (type: ["string","null"], format: date-time)
- Crypto fields: Use `contentEncoding: "base64"`
- Comments: Only `$comment` fields (no non-standard keys)

**Validation Tasks:**
1. Confirm `$schema` is JSON Schema 2020-12
2. Verify `$id` and `$defs` structure
3. Validate conditional logic syntax (if/then)
4. Ensure all invariants are present
5. Check property definitions and types
6. Validate crypto field encodings
7. Clean up non-standard comment keys

**Validation Process:**
1. Review current schema against invariants
2. Make minimal necessary fixes only
3. Run VS Code task `contracts:validate`
4. Verify all validation passes
5. Document changes in CHANGELOG

**Breaking Change Protocol:**
- If changes would break existing consumers
- STOP immediately
- Invoke "Contract Freeze & Migration" process
- Do not proceed without migration plan

**Acceptance Criteria:**
- [ ] All critical invariants preserved
- [ ] Conditional logic properly implemented
- [ ] JSON Schema 2020-12 compliance
- [ ] Contract validation passes
- [ ] Minimal diff from original schema
- [ ] No breaking changes for consumers
- [ ] CHANGELOG updated with changes

**Deliverables:**
- Updated `contracts/events/envelope.schema.json`
- CHANGELOG note fragment
- Validation evidence

Please help me audit and fix the envelope schema while preserving all invariants.
```

---

## 🔧 **Schema Invariant Troubleshooting**

```
I'm having issues with envelope schema invariant validation:

**Problem Details:**
- **Failing Invariants:** [Which invariants are not being enforced]
- **Validation Errors:** [Specific schema validation failures]
- **Conditional Logic Issues:** [Problems with if/then rules]
- **Format Violations:** [JSON Schema 2020-12 compliance issues]

**Error Context:**
- **Schema Sections:** [Which parts of the schema have issues]
- **Test Cases:** [Failing validation test cases]
- **Consumer Impact:** [How changes affect existing consumers]
- **Migration Needs:** [Whether breaking changes are necessary]

**Debugging Information:**
- Current schema structure
- Failing validation examples
- Conditional rule evaluation
- Consumer compatibility assessment

Please help me troubleshoot and resolve the envelope schema invariant issues.
```

---

## 📊 **Schema Migration Planning**

```
I need to plan a migration for envelope schema changes:

**Migration Context:**
- **Breaking Changes:** [List of breaking schema changes]
- **Consumer Impact:** [Which systems will be affected]
- **Migration Timeline:** [When changes need to be deployed]
- **Rollback Requirements:** [How to safely revert changes]

**Migration Strategy:**
- Version management approach
- Backward compatibility plan
- Consumer update coordination
- Testing and validation strategy

**Risk Assessment:**
- Data compatibility issues
- Consumer breakage scenarios
- Performance impact considerations
- Security and privacy implications

Please help me design a safe migration plan for envelope schema changes.
```
````
