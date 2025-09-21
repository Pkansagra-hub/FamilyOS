---
description: Milestone-Epic-Issue development workflow for structured feature delivery.
applyTo: "**/*"
---
# 🎯 Milestone-Epic-Issue Development Workflow

## Overview
MemoryOS follows a structured development approach using milestone-driven branching with epic and issue organization for predictable feature delivery.

---

## 🌳 Branch Hierarchy

### **Branch Types:**
```
main (protected)
├── develop (active development, dev environment)
    ├── milestone/M1-foundation
    │   ├── epic/M1.1-event-bus-infrastructure
    │   │   ├── issue/1.1.1-event-envelope-design
    │   │   ├── issue/1.1.2-basic-publisher-interface
    │   │   └── issue/1.1.3-jsonl-persistence-layer
    │   ├── epic/M1.2-storage-foundation
    │   └── epic/M1.3-basic-api-layer
    ├── milestone/M2-cognitive-core
    └── milestone/M3-intelligence-layer
```

### **Naming Conventions:**
- **Milestones:** `milestone/M{number}-{name}`
- **Epics:** `epic/M{milestone}.{epic}-{name}`
- **Issues:** `issue/{epic-id}.{issue-id}-{name}`
- **Hotfixes:** `hotfix/{description}`

---

## 🔄 Development Workflow

### **1. Planning Phase**
```bash
# Start from develop
git checkout develop && git pull

# Create or checkout milestone branch
git checkout milestone/M1-foundation || git checkout -b milestone/M1-foundation

# Create epic branch if needed
git checkout epic/M1.1-event-bus || git checkout -b epic/M1.1-event-bus
```

### **2. Issue Implementation**
```bash
# Create issue branch from epic
git checkout -b issue/1.1.1-event-envelope-design

# Follow contracts-first methodology
1. Update contracts/** first
2. Run: contracts:validate
3. Write failing tests
4. Implement with feature flags and observability
5. Validate: ci:fast
```

### **3. Integration Flow**
```bash
# Issue → Epic (individual feature completion)
git checkout epic/M1.1-event-bus
git merge issue/1.1.1-event-envelope-design

# Epic → Milestone (epic completion with verification)
git checkout milestone/M1-foundation
git merge epic/M1.1-event-bus

# Milestone → Develop (milestone completion with full testing)
git checkout develop
git merge milestone/M1-foundation

# Develop → Main (production release with approval)
# Via protected PR process
```

---

## 📋 Work Planning

### **Milestone Planning:**
- **Duration:** 12-16 weeks per milestone
- **Scope:** Major system capability (Foundation, Cognitive Core, Intelligence Layer)
- **Deliverables:** Complete feature set with production readiness
- **Acceptance:** Full test suite, documentation, performance validation

### **Epic Planning:**
- **Duration:** 3-4 weeks per epic
- **Scope:** Related set of issues delivering cohesive functionality
- **Deliverables:** Working feature components with integration
- **Acceptance:** Integration tests pass, contract compliance achieved

### **Issue Planning:**
- **Duration:** 1-5 days per issue
- **Scope:** Single feature, bug fix, or improvement
- **Deliverables:** Working code with tests and observability
- **Acceptance:** Unit tests pass, contracts validated, code reviewed

---

## 🚀 PR Strategy

### **PR Templates by Level:**
- **Issue → Epic:** Focus on feature completion and integration
- **Epic → Milestone:** Emphasize epic verification and milestone progress
- **Milestone → Develop:** Complete milestone validation and readiness
- **Develop → Main:** Production deployment and release preparation

### **Review Requirements:**
- **Issue PRs:** Peer review, automated CI/CD
- **Epic PRs:** Technical lead review, integration validation
- **Milestone PRs:** Architecture review, full system testing
- **Production PRs:** Stakeholder approval, security validation

---

## 🔒 Quality Gates

### **Progressive Validation:**
```yaml
Issue Level:
  - Contract syntax validation
  - Unit tests (≥70% coverage)
  - Code quality (ruff, mypy, black)
  - Security scanning

Epic Level:
  - Integration test suite
  - Contract validation
  - Performance baseline
  - Cross-feature compatibility

Milestone Level:
  - Complete test suite
  - End-to-end testing
  - Performance validation
  - Security audit

Production Level:
  - Production readiness
  - Deployment validation
  - Monitoring setup
  - Documentation complete
```

---

## 🛠️ Tooling Support

### **VS Code Tasks:**
- `workflow:milestone-plan` → Plan milestone structure
- `workflow:epic-create` → Create epic branch and setup
- `workflow:issue-start` → Start issue development
- `branch:milestone-status` → Check milestone progress
- `branch:epic-merge` → Merge issue to epic
- `branch:milestone-merge` → Merge epic to milestone

### **Git Hooks:**
- Pre-commit: Contract validation, code quality
- Pre-push: Test suite validation
- Post-merge: Integration verification

---

## 📊 Progress Tracking

### **Milestone Metrics:**
- Epic completion percentage
- Issue velocity and burn-down
- Test coverage progression
- Contract compliance status

### **Quality Metrics:**
- Code quality scores
- Test suite health
- Performance benchmarks
- Security scan results

### **Delivery Metrics:**
- Feature delivery timeline
- Scope creep tracking
- Resource utilization
- Milestone predictability

---

## 🚨 Emergency Procedures

### **Hotfix Process:**
```bash
# Create hotfix from main
git checkout main && git pull
git checkout -b hotfix/critical-security-fix

# Implement minimal fix
# Skip epic/milestone process for critical issues
# Direct PR to main with expedited review

# After deployment, back-merge to develop
git checkout develop
git merge hotfix/critical-security-fix
```

### **Rollback Procedures:**
- **Issue Rollback:** Revert issue merge from epic
- **Epic Rollback:** Reset milestone to pre-epic state
- **Milestone Rollback:** Reset develop to stable state
- **Production Rollback:** Emergency revert with immediate deployment

---

## 🎯 Success Criteria

### **Workflow Effectiveness:**
- Predictable milestone delivery
- Minimal integration conflicts
- Clear feature progress tracking
- Efficient code review process

### **Quality Outcomes:**
- High test coverage maintenance
- Consistent code quality
- Stable contract evolution
- Performance target achievement

### **Team Productivity:**
- Reduced context switching
- Clear ownership boundaries
- Efficient collaboration patterns
- Minimal blocking dependencies
