````prompt
# 🚀 Contract-First Feature Development Prompts

Use these prompts when implementing features following MemoryOS's contracts-first methodology with full guardrails.

---

## 🏗️ **Implement Contract-First Feature**

```
I need to implement a new feature following the contracts-first approach:

**Feature Requirements:**
- **Feature Name:** [Descriptive name of the feature]
- **Business Value:** [What problem this solves]
- **User Story:** [As a user, I want... so that...]
- **Scope:** [API endpoints/Events/Storage/All components affected]

**Contract Planning:**
- **API Changes:** [New endpoints or modifications needed]
- **Event Changes:** [New events or envelope modifications]
- **Storage Changes:** [New schemas or data structure changes]
- **Integration Points:** [Which existing systems will be affected]

**Implementation Approach:**
1. **Read Foundation Documents:**
   - Review `.github/copilot-instructions.md`
   - Study `.github/instructions/contracts.instructions.md`
   - Understand existing contract patterns

2. **Contract-First Design:**
   - Identify minimal additive contract changes
   - Design OpenAPI specifications first
   - Define event schemas and envelope changes
   - Plan storage schema updates

3. **Contract Validation:**
   - Update contracts in `contracts/**` with examples
   - Run VS Code task `contracts:validate`
   - Fallback: `poetry run python scripts/contracts/storage_validate.py`
   - Ensure all contract validation passes

4. **Implementation with Guardrails:**
   - Generate code changes behind config/feature flag
   - Add comprehensive observability (metrics+spans+logs)
   - Respect band classifications and PEP checks
   - No PII in logs or telemetry

5. **Quality Assurance:**
   - Add tests (unit+integration+contract)
   - Run VS Code task `ci:fast`
   - Fallback: `poetry run ruff check . && poetry run mypy --strict . && poetry run python -m ward -p tests`
   - Achieve required coverage thresholds

6. **Delivery:**
   - Open small, focused PR
   - Fill PR template completely
   - Include contract validation evidence
   - Document feature flag usage

**Guardrails & Constraints:**
- **DO NOT** auto-edit `.env*`, lockfiles, or `.vscode/*.json` without explicit approval
- **RESPECT** band classifications and security policies
- **NO PII** in logs, metrics, or traces
- **CONFIG-GATED** new functionality with feature flags
- **MINIMAL** changes with maximum backward compatibility

**Validation Checklist:**
- [ ] Contracts updated first and validated
- [ ] All contract validation passes
- [ ] Code implemented behind feature flag
- [ ] Observability properly instrumented
- [ ] All tests pass (unit+integration+contract)
- [ ] No PII in telemetry data
- [ ] Security and band policies respected
- [ ] PR template filled completely

**Acceptance Criteria:**
- Contracts pass validation suite
- Feature works behind flag configuration
- Comprehensive test coverage achieved
- Observability metrics/spans/logs present
- Security and privacy requirements met
- Small, reviewable PR created

Please help me implement this feature following the contracts-first methodology.
```

---

## 🔄 **Contract Delta Analysis**

```
I need to analyze the contract changes required for a feature:

**Feature Context:**
- **Feature Description:** [What the feature does]
- **Current System State:** [Existing functionality that will be affected]
- **Integration Requirements:** [How it connects to existing systems]

**Contract Analysis Needed:**
- **API Impact:** [Which endpoints need changes]
- **Event Impact:** [Which events need modifications]
- **Storage Impact:** [Which schemas need updates]
- **Breaking Changes:** [Any backward compatibility concerns]

**Change Assessment:**
- Identify minimal additive changes
- Assess backward compatibility impact
- Plan migration strategy if needed
- Estimate implementation complexity

Please help me analyze the contract delta for this feature.
```

---

## 🛡️ **Feature Flag Implementation**

```
I need to implement proper feature flagging for a new feature:

**Feature Flag Requirements:**
- **Flag Name:** [Descriptive flag identifier]
- **Default State:** [Enabled/Disabled by default]
- **Scope:** [Global/Per-user/Per-space/etc.]
- **Rollout Strategy:** [How to gradually enable]

**Implementation Details:**
- Configuration management
- Runtime flag evaluation
- Observability and metrics
- Rollback procedures

**Safety Measures:**
- Graceful degradation when disabled
- No impact on existing functionality
- Monitoring and alerting integration
- Clear documentation for operators

Please help me implement robust feature flagging for this new functionality.
```
````
