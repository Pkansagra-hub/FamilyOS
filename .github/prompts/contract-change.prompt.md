# 📋 Contract Change Prompts

Use these standardized prompts when requesting contract changes to ensure consistency and completeness.

---

## 🔄 **Contract Modification Request**

```
I need to modify a contract for [API/Events/Storage]. Here are the details:

**Change Type:** [Breaking/Non-breaking/Enhancement]
**Affected Contract:** [e.g., contracts/api/openapi/modules/memory-openapi.yaml OR contracts/events/modules/memory-catalog.json OR contracts/storage/schemas/memory-*.schema.json]
**Business Requirement:** [Specific functional requirement - be concrete]
**Breaking Change Impact:** [Specific services/clients affected - list actual services]
**Migration Strategy:** [Specific adapter/migration code needed]
**Version Bump:** [MAJOR/MINOR/PATCH with semver justification]

**Specific Changes:**
- Field additions: [exact field names and types]
- Schema modifications: [before/after JSON schema snippets]
- Endpoint changes: [exact HTTP methods and paths]
- Event modifications: [exact event topic and payload changes]

**Validation Commands to Run:**
- [ ] `python contracts/automation/validation_helper.py --file [contract-file]`
- [ ] `python contracts/automation/contract_suite.py validate --contract [contract-type]`
- [ ] `python scripts/contracts/storage_validate.py` (for storage contracts)
- [ ] `python scripts/contracts/check_envelope_invariants.py` (for events)

**Required Artifacts:**
- [ ] Updated contract file with exact changes
- [ ] Updated examples in contracts/examples/
- [ ] Migration documentation in contracts/_migration/
- [ ] Contract freeze created with `python contracts/automation/contract_suite.py freeze`

Please validate all changes before implementation.
```

---

## 🆕 **New Contract Creation**

```
I need to create new contracts for [Service/Feature Name]:

**Contract Files to Create:**
- [ ] contracts/api/openapi/modules/[service-name]-openapi.yaml
- [ ] contracts/events/modules/[service-name]-catalog.json
- [ ] contracts/storage/schemas/[service-name]-*.schema.json

**Service Details:**
- **Purpose:** [Specific business capability - avoid generic terms]
- **Tier:** [API/Events/Storage/Cognitive - affects pipeline placement P01-P20]
- **Dependencies:** [Exact service names from existing contracts/]
- **Security Band:** [GREEN/AMBER/RED/BLACK - affects policy enforcement]

**API Requirements:** (if applicable)
- **Endpoints:** [Exact HTTP methods: GET /api/v1/[resource], POST /api/v1/[resource]]
- **Authentication:** [Bearer token, API key, mTLS - be specific]
- **Rate Limiting:** [Exact limits: 100 req/min per user]
- **Error Codes:** [4xx/5xx codes to return]

**Event Requirements:** (if applicable)
- **Topics:** [Exact event names: memory.created, memory.updated]
- **Schemas:** [Reference existing envelope.schema.json structure]
- **Producers:** [Exact service names that emit these events]
- **Consumers:** [Exact service names that process these events]

**Storage Requirements:** (if applicable)
- **Entities:** [Exact table/collection names]
- **Relationships:** [Foreign key constraints, indices]
- **Query Patterns:** [Specific queries: find by user_id, search by content]

**Generation Commands:**
- [ ] `python contracts/automation/interactive_contract_builder.py` (guided creation)
- [ ] `python contracts/automation/contract_suite.py generate --service [service-name] --type [api|events|storage]`
- [ ] Validate with `python contracts/automation/validation_helper.py --service [service-name]`

**Brain Region Mapping:** (for cognitive services)
- [ ] Specify brain region: hippocampus, cortex, cerebellum, etc.
- [ ] Neural substrate: memory, attention, motor, sensory

Please create all contracts with concrete specifications.
```

---

## 🐛 **Contract Bug Fix**

```
I found an issue with a contract that needs fixing:

**Contract File:** [Path to problematic contract]
**Issue Description:** [What's wrong]
**Error Symptoms:** [How the bug manifests]
**Root Cause:** [Why this happened]

**Proposed Fix:**
- [Specific changes needed]
- [Impact assessment]
- [Compatibility considerations]

**Testing Requirements:**
- [ ] Validate fix resolves issue
- [ ] Ensure no regression
- [ ] Update examples if needed

This should be a PATCH version bump unless it's a breaking change.
```

---

## ⚡ **Emergency Contract Hotfix**

```
URGENT: Emergency contract fix needed

**Severity:** [Critical/High/Medium]
**Impact:** [What's broken in production]
**Contract:** [Affected contract file]
**Timeline:** [How urgent is this]

**Minimal Fix Required:**
- [Smallest possible change]
- [Immediate impact]
- [Rollback plan]

**Emergency Procedures:**
- [ ] Fast-track validation
- [ ] Emergency freeze creation
- [ ] Immediate deployment
- [ ] Post-fix full review

Please prioritize this fix and follow emergency procedures.
```

---

## 🔄 **Contract Version Migration**

```
I need help migrating from contract version X to Y:

**Current Version:** [Version being migrated from]
**Target Version:** [Version migrating to]
**Migration Scope:** [What needs to change]

**Breaking Changes:**
- [List each breaking change]
- [Impact on existing code]
- [Required adaptations]

**Migration Strategy:**
- [ ] Backward compatibility period
- [ ] Gradual rollout plan
- [ ] Fallback procedures
- [ ] Testing strategy

**Timeline:**
- **Start Date:** [When migration begins]
- **Completion Date:** [When migration finishes]
- **Milestones:** [Key checkpoints]

Please create migration documentation and adaptation guides.
```

---

## 📊 **Contract Impact Analysis**

```
I need an impact analysis for proposed contract changes:

**Proposed Changes:** [Summary of changes]
**Affected Systems:** [List systems that use this contract]
**Change Classification:** [Breaking/Non-breaking/Enhancement]

**Analysis Needed:**
- [ ] Breaking change assessment
- [ ] Performance impact
- [ ] Security implications
- [ ] Migration complexity
- [ ] Timeline estimation

**Stakeholders:**
- [List teams/systems affected]
- [Communication requirements]
- [Approval needed from whom]

Please analyze and provide recommendations for safe implementation.
```

---

## 🔍 **Contract Validation Request**

```
Please validate my contract changes:

**Changed Files:**
- [List all modified contract files]
- [Brief description of changes]

**Validation Requirements:**
- [ ] Syntax validation
- [ ] Schema compliance
- [ ] Example validation
- [ ] Breaking change check
- [ ] Performance impact

**Test Results:**
- [Attach any test outputs]
- [Note any failures or warnings]

**Questions/Concerns:**
- [Any specific areas to focus on]
- [Known issues to address]

Please run full contract validation suite and provide feedback.
```
