````prompt
# 🧊 Contract Freeze & Release Management Prompts

Use these prompts when creating SemVer contract releases with proper artifact management and CI integration.

---

## 📦 **Create Contract Freeze & Release**

```
I need to freeze current contracts under a new SemVer release with proper artifact management:

**Release Planning:**
- **Target Version:** [e.g., 1.2.0 for minor, 2.0.0 for major]
- **Change Type:** [MAJOR/MINOR/PATCH]
- **Change Summary:** [List of features/fixes/breaking changes]
- **Breaking Changes:** [Yes/No - if yes, requires migration plan]
- **Release Timeline:** [When this needs to be deployed]

**Pre-Release Validation:**
- Current contract state is stable and tested
- All contract validation passes
- Change impact assessment completed
- Migration plan ready (if breaking changes)

**Freeze Artifact Requirements:**
1. **Frozen Folder Structure:**
   ```
   contracts/frozen/<version>/
   ├── openapi.<version>.yaml      # Bundled API specification
   ├── envelope.<version>.schema.json  # Event envelope schema
   └── schema-index.json           # Index with SHA256 hashes
   ```

2. **Contract Index:**
   - Update `contracts/README.md` or `contracts/INDEX.md`
   - Version → files → dates → notes mapping
   - Clear migration path documentation

3. **Version Management:**
   - Update `info.version` in `contracts/api/openapi/main.yaml`
   - Minor/Patch: Additive changes only
   - Major: Mark breaking changes and link to migration

4. **Policy Documentation:**
   - Update `POLICY_VERSIONING.md`
   - Add release entry with SemVer, scope, and policy band impact
   - Document any policy implications

5. **CI Integration:**
   - Update workflow to compare current bundle to frozen artifacts
   - Fail CI if drift detected without explicit version bump
   - Prevent unintentional contract changes

**Freeze Process:**
1. **Bundle Current Contracts:**
   ```bash
   npx @redocly/cli@latest bundle contracts/api/openapi/main.yaml -o contracts/api/openapi.v1.yaml
   ```

2. **Create Frozen Artifacts:**
   - Copy bundled OpenAPI to `contracts/frozen/<version>/openapi.<version>.yaml`
   - Copy envelope schema to `contracts/frozen/<version>/envelope.<version>.schema.json`
   - Generate `schema-index.json` with file list and SHA256 hashes

3. **Update Documentation:**
   - Contract index with version mapping
   - Policy versioning documentation
   - Migration guides (if needed)

4. **Version Bump:**
   - Update OpenAPI version field
   - Tag breaking changes appropriately
   - Link to migration documentation

5. **CI Guard Implementation:**
   - Bundle comparison workflow
   - Drift detection and prevention
   - Version bump requirement enforcement

**Validation Commands:**
- Run VS Code task: `contracts:validate`
- Run VS Code task: `ci:fast`
- Verify bundle generation succeeds
- Validate frozen artifact integrity

**Breaking Change Protocol:**
If breaking changes are present:
1. MUST create migration plan first
2. Document backward incompatibilities
3. Provide adapter/bridge implementations
4. Plan phased rollout strategy
5. Coordinate with consumer teams

**Acceptance Criteria:**
- [ ] Frozen artifacts created in version directory
- [ ] Contract index updated with new version
- [ ] Version bumped in main OpenAPI specification
- [ ] Policy versioning documentation updated
- [ ] CI guard configured for drift prevention
- [ ] All validation passes
- [ ] Migration plan ready (if breaking)
- [ ] PR created with proper title format

**Deliverables:**
- New `contracts/frozen/<version>/*` files
- Updated contract index and documentation
- Version-bumped main contracts
- Enhanced CI workflow
- PR titled: `release(contracts): freeze v<version>`

Please help me create a proper contract freeze and release.
```

---

## 🔄 **Contract Version Management**

```
I need help managing contract versions and compatibility:

**Version Management Context:**
- **Current Version:** [Active contract version]
- **Proposed Version:** [Target version for changes]
- **Change Scope:** [Which contracts are affected]
- **Compatibility Impact:** [Backward/forward compatibility concerns]

**Version Strategy Questions:**
- Should this be MAJOR/MINOR/PATCH?
- Are there breaking changes?
- What's the migration strategy?
- How do we maintain compatibility?

**Documentation Needs:**
- Version history and changelog
- Migration guides and examples
- Compatibility matrix
- Consumer impact assessment

Please help me determine the appropriate versioning strategy and documentation approach.
```

---

## 🛡️ **CI Drift Prevention**

```
I need to implement CI safeguards to prevent contract drift:

**Current CI State:**
- **Workflow File:** [Current CI configuration]
- **Contract Validation:** [Existing validation steps]
- **Drift Detection:** [Current change detection method]
- **Guard Effectiveness:** [How well current guards work]

**Drift Prevention Requirements:**
- Automatic bundle comparison with frozen versions
- Version bump requirement enforcement
- Clear failure messages for unauthorized changes
- Integration with PR review process

**Implementation Needs:**
- CI workflow updates
- Comparison and validation scripts
- Error reporting and messaging
- Documentation for developers

Please help me design and implement robust contract drift prevention.
```
````
