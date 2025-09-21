---
description: Complete step-by-step process for making contract changes while maintaining system stability and compliance.
applyTo: "contracts/**/*"
---
# 📋 Contract Change Workflow

---

## 🎯 **Quick Start**

```bash
# 1. Use VS Code Task: "Validate Current Contracts"
# 2. Follow this workflow
# 3. Use prompts from .github/prompts/contract-change.md
# 4. Execute VS Code Task: "Create Contract Freeze"
```

---

## 📝 **Pre-Change Checklist**

- [ ] **Business requirement** clearly defined
- [ ] **Breaking change impact** assessed
- [ ] **Version strategy** determined (MAJOR/MINOR/PATCH)
- [ ] **Migration plan** drafted (if breaking)
- [ ] **Stakeholder approval** obtained

---

## 🔄 **Step-by-Step Process**

### **Step 1: Analysis & Planning**

1. **Identify Change Scope**
   ```bash
   # Run contract validation to see current state
   python scripts/contracts/contracts_validate.py
   
   # Check which contracts will be affected
   python scripts/contracts/contract_helper.py validate
   ```

2. **Assess Breaking Changes**
   - Review `contracts/POLICY_VERSIONING.md`
   - Check frozen envelope invariants
   - Identify dependent services

3. **Plan Version Strategy**
   - **MAJOR** (X.y.z): Breaking changes, API incompatibility
   - **MINOR** (x.Y.z): New features, backward compatible
   - **PATCH** (x.y.Z): Bug fixes, no API changes

### **Step 2: Contract Updates**

1. **Update Contracts First** (ALWAYS)
   ```bash
   # For API changes
   edit contracts/api/openapi/main.yaml
   
   # For event changes  
   edit contracts/events/envelope.schema.json
   edit contracts/events/schemas/*.schema.json
   
   # For storage changes
   edit contracts/storage/schemas/*.schema.json
   ```

2. **Validate Syntax**
   ```bash
   # Use VS Code Task: "Validate Contract Syntax"
   # Or manually:
   python scripts/contracts/storage_validate.py
   ```

3. **Check Envelope Invariants** (if touching events)
   ```bash
   python scripts/contracts/check_envelope_invariants.py
   ```

### **Step 3: Implementation**

1. **Update Implementation Code**
   - Follow contract specifications exactly
   - Update related modules
   - Maintain backward compatibility where possible

2. **Update Tests**
   ```bash
   # Update contract tests
   edit tests/contracts/*.md
   
   # Update example files
   edit contracts/*/examples/*.json
   ```

3. **Update Documentation**
   - Module READMEs
   - API documentation
   - Migration guides (if breaking)

### **Step 4: Validation**

1. **Run Complete Validation**
   ```bash
   # Use VS Code Task: "Run Contract Validation Suite"
   # Or manually:
   python scripts/contracts/contract_helper.py validate
   ```

2. **Test Implementation**
   ```bash
   # Run affected tests
   python -m ward test --path tests/
   
   # Run integration tests
   python -m ward test --path tests/integration/
   ```

3. **Check CI Pipeline**
   - Ensure GitHub Actions pass
   - Verify contract guard workflow succeeds

### **Step 5: Versioning & Freeze**

1. **Bump Versions**
   ```bash
   # Use contract helper
   python scripts/contracts/contract_helper.py bump-version --type major|minor|patch
   ```

2. **Create Contract Freeze**
   ```bash
   # Use VS Code Task: "Create Contract Freeze"
   # Or manually:
   python scripts/contracts/contracts_freeze.py create v1.x.x-description
   ```

3. **Update Change Log**
   ```bash
   edit contracts/CHANGELOG.md
   ```

### **Step 6: Communication & Deployment**

1. **Create Migration Guide** (if breaking)
   - Document changes
   - Provide code examples  
   - Include rollback procedures

2. **Stakeholder Communication**
   - Notify affected teams
   - Schedule deployment windows
   - Provide support channels

3. **Deploy Changes**
   - Follow deployment procedures
   - Monitor for issues
   - Have rollback plan ready

---

## 🚨 **Emergency Procedures**

### **Immediate Rollback**
```bash
# Restore previous freeze
python scripts/contracts/contracts_freeze.py restore v1.x.x-previous

# Revert implementation changes
git revert <commit-hash>

# Notify stakeholders
```

### **Hot Fix Process**
```bash
# 1. Create emergency branch
git checkout -b hotfix/critical-contract-fix

# 2. Make minimal changes
# 3. Fast-track validation
# 4. Emergency freeze
python scripts/contracts/contracts_freeze.py create v1.x.x-hotfix

# 5. Deploy immediately
```

---

## 📊 **Validation Checklist**

### **Before Implementation**
- [ ] Contract syntax valid
- [ ] Breaking change impact assessed
- [ ] Version strategy confirmed
- [ ] Migration plan ready

### **After Implementation**
- [ ] All tests pass
- [ ] Contract validation clean
- [ ] Documentation updated
- [ ] Examples work correctly

### **Before Deployment**
- [ ] Contract freeze created
- [ ] Change log updated
- [ ] Migration guide ready
- [ ] Rollback plan tested

---

## 🔗 **Related Resources**

- **Contract Tools:** `scripts/contracts/README.md`
- **Versioning Policy:** `contracts/POLICY_VERSIONING.md`
- **Developer Guide:** `contracts/DEVELOPER_WORKFLOW.md`
- **Quick Reference:** `contracts/CONTRACT_CHANGE_QUICK_REF.md`
- **VS Code Tasks:** `.vscode/tasks.json`
- **Standardized Prompts:** `.github/prompts/contract-change.md`

---

## 📝 **Common Scenarios**

### **Adding New API Endpoint**
1. Update `contracts/api/openapi/main.yaml`
2. Add error definitions if needed
3. Update implementation in `api/`
4. Add tests and examples
5. Minor version bump

### **Modifying Event Schema**
1. Check envelope invariants first
2. Update `contracts/events/schemas/*.schema.json`
3. Update examples
4. Check all event producers/consumers
5. Version based on compatibility

### **Storage Schema Evolution**
1. Update `contracts/storage/schemas/*.schema.json`
2. Plan migration strategy
3. Update storage implementation
4. Test backward compatibility
5. Document migration path

---

**🎯 Remember:** Contracts are law. Implementation follows contracts, never the reverse.