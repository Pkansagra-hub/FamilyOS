````prompt
# 🛡️ Contract CI Hardening Prompts

Use these prompts when implementing CI/CD safeguards to prevent contract drift and ensure stability.

---

## 🔒 **Implement Contract Stability Guards**

```
I need to implement CI hardening to prevent unintentional contract changes:

**Current State:**
- **CI Pipeline:** [Current GitHub Actions workflow status]
- **Contract Structure:** [Location of main contracts and frozen versions]
- **Version Management:** [Current versioning approach]
- **Validation Tools:** [Existing contract validation setup]

**Hardening Requirements:**
1. **Contract Drift Prevention:**
   - Bundle from `contracts/api/openapi/main.yaml` to temp file
   - Diff against latest frozen `contracts/frozen/<version>/openapi.<version>.yaml`
   - Fail CI if different unless `info.version` bumped and new freeze present

2. **Schema Validation:**
   - Validate envelope schema presence using `scripts/contracts/storage_validate.py`
   - Check contract invariants and structural requirements
   - Ensure all required schemas are present and valid

3. **Linting Integration:**
   - Add Spectral linter step with recommended rules
   - Configure zero-error tolerance for contract quality
   - Integrate with existing CI quality gates

4. **Reporting & Visibility:**
   - GitHub Check summary with endpoint counts
   - Schema inventory and frozen artifact tracking
   - Clear failure messages for contract violations

**Implementation Tasks:**
1. Update `.github/workflows/ci.yml` with contract guards
2. Configure contract bundling and diff validation
3. Integrate envelope schema validation
4. Add Spectral linting with strict rules
5. Implement GitHub Check reporting
6. Document guard mechanism in `contracts/README.md`

**CI Workflow Steps:**
```yaml
- name: Contract Stability Check
  run: |
    # Bundle current contracts
    npx @redocly/cli bundle contracts/api/openapi/main.yaml -o temp-bundle.yaml

    # Compare with frozen version
    diff temp-bundle.yaml contracts/frozen/$VERSION/openapi.$VERSION.yaml || check_version_bump

    # Validate schemas and invariants
    python scripts/contracts/storage_validate.py

    # Lint with zero tolerance
    npx spectral lint contracts/api/openapi/main.yaml --fail-on-unmatched-globs
```

**Acceptance Criteria:**
- [ ] CI fails on contract changes without version bump
- [ ] Schema validation integrated into pipeline
- [ ] Spectral linting enforced with zero errors
- [ ] GitHub Check reports contract metrics
- [ ] Documentation updated for guard mechanism
- [ ] Frozen artifacts properly managed
- [ ] Clear error messages for violations
- [ ] No false positives in stability checks

**Deliverables:**
- Updated `.github/workflows/ci.yml`
- Enhanced contract validation scripts
- GitHub Check reporting integration
- Documentation in `contracts/README.md`

Please help me implement comprehensive contract CI hardening.
```

---

## 📋 **Contract Version Management**

```
I need to improve contract version management and freeze processes:

**Version Control Issues:**
- **Current Versioning:** [How contracts are currently versioned]
- **Freeze Process:** [Existing freeze/release workflow]
- **Drift Detection:** [How contract changes are detected]
- **Breaking Changes:** [How breaking changes are managed]

**Version Management Requirements:**
- Semantic versioning for contract changes
- Automated freeze generation on version bumps
- Clear migration paths for breaking changes
- Backward compatibility validation

**Freeze Workflow:**
1. Version bump triggers freeze creation
2. Frozen artifacts stored in version-specific directories
3. Migration documentation generated
4. Compatibility matrix updated

Please help me design a robust contract version management system.
```

---

## 🔍 **CI Troubleshooting**

```
I'm having issues with contract CI hardening implementation:

**Problem Details:**
- **CI Failures:** [Specific CI failures related to contracts]
- **Tool Errors:** [Bundling/linting/validation errors]
- **False Positives:** [Incorrect failure detection]
- **Performance Issues:** [CI pipeline performance problems]

**Error Context:**
- **Workflow Stage:** [Which CI step is failing]
- **Error Messages:** [Detailed error output]
- **Contract Changes:** [Recent contract modifications]
- **Tool Versions:** [Redocly, Spectral, validation script versions]

**Diagnostic Information:**
- Current contract state vs frozen versions
- Bundling and diff output
- Validation script results
- Linting rule violations

Please help me troubleshoot and resolve the contract CI hardening issues.
```
```` Hardening

Goal: Enforce contract stability in CI so contracts can’t drift unintentionally.

Tasks:
1) Add a CI step to **bundle** from `contracts/api/openapi/main.yaml` to a temp file; **diff** with latest frozen `contracts/frozen/<version>/openapi.<version>.yaml`. If different → fail unless `info.version` bumped and new freeze artifacts present.
2) Validate envelope schema presence and invariants using `scripts/contracts_validate.py`.
3) Optional: Add a `spectral` linter step with recommended rules; no errors allowed.
4) Post a GitHub Check summary with counts of endpoints, schemas, and frozen artifacts.

Deliverables:
- Updated `.github/workflows/ci.yml`.
- Short README note in `contracts/` on how the guard works.
