---
description: GitHub Actions CI/CD safety rails with milestone-epic-issue branching strategy.
applyTo: ".github/workflows/**/*.yml,.github/workflows/**/*.yaml"
---
# 🏗️ CI/CD — GitHub Actions

## 1) Security
- Use `actions/checkout@v4`. Pin action SHAs or trusted tags.
- Minimal `permissions:`; prefer OIDC for cloud auth. No long-lived secrets.

## 2) Milestone-Epic-Issue Workflow Jobs
### **Branch-Specific Validation:**
- **Issue branches:** Quick validation (lint, type check, unit tests, contract syntax)
- **Epic branches:** Enhanced validation (integration tests, contract validation, coverage)
- **Milestone branches:** Full validation (complete test suite, performance tests, security scans)
- **Develop branch:** Production readiness (full CI/CD pipeline, deployment tests)
- **Main branch:** Production deployment (release validation, tagged deployments)

### **Job Matrix:**
- Matrix with **Python 3.11**. Cache Poetry.
- **Issue → Epic:** ruff → mypy → ward (unit) → contracts:validate-syntax
- **Epic → Milestone:** Full suite + integration tests + contract validation
- **Milestone → Develop:** Complete pipeline + performance tests
- **Develop → Main:** Production readiness + security validation

## 3) Branch Targeting & Naming Enforcement
### **Branch Naming Patterns:**
```yaml
milestone/M[0-9]+-[a-z0-9-]+
epic/M[0-9]+\.[0-9]+-[a-z0-9-]+
issue/[0-9]+\.[0-9]+\.[0-9]+-[a-z0-9-]+
hotfix/[a-z0-9-]+
```

### **PR Target Validation:**
- `issue/*` → `epic/*` (must target correct epic)
- `epic/*` → `milestone/*` (must target correct milestone)
- `milestone/*` → `develop` (milestone completion)
- `develop` → `main` (production release)
- `hotfix/*` → `main` (emergency fixes only)

## 4) Contract-First Enforcement
### **Contract Validation Gates:**
- **All branches:** Contract syntax validation
- **Epic merges:** Full contract validation + compatibility checks
- **Milestone merges:** Contract freeze compliance + migration validation
- **Develop merges:** Production contract readiness

### **Contract Change Detection:**
- Detect changes in `contracts/**`
- Require contract validation before code changes
- Enforce SemVer for breaking changes
- Validate contract freeze process

## 5) Quality Gates
### **Progressive Validation:**
- **Issue level:** Fast feedback (< 5 minutes)
- **Epic level:** Comprehensive testing (< 15 minutes)
- **Milestone level:** Full validation (< 30 minutes)
- **Production level:** Complete pipeline (< 60 minutes)

### **Failure Handling:**
- Fail fast on lint/type/security errors
- Coverage thresholds enforced for changed code
- Contract validation failures block all merges
- Performance regression detection

## 6) Artifacts & Reporting
### **Branch-Specific Artifacts:**
- **Issue branches:** Test reports, basic coverage
- **Epic branches:** Integration test reports, contract validation results
- **Milestone branches:** Complete test suite results, performance benchmarks
- **Develop/Main:** Deployment artifacts, security scan results

### **Milestone Progress Tracking:**
- Epic completion status
- Issue integration status
- Contract validation compliance
- Test coverage progression

## 7) Deployment Strategy
### **Environment Mapping:**
- **Develop branch:** Continuous deployment to dev environment
- **Milestone branches:** Optional staging deployment for verification
- **Main branch:** Production deployment with approval gates

### **Release Process:**
1. Milestone completion triggers staging deployment
2. Manual verification in staging environment
3. Approved milestone merge to develop
4. Develop → main with production deployment
5. Automatic tagging and release notes

## 8) Emergency Procedures
### **Hotfix Workflow:**
- `hotfix/*` branches target `main` directly
- Fast-track CI with essential validations only
- Automatic back-merge to `develop` after deployment
- Immediate notification to development teams

### **Rollback Procedures:**
- Quick revert mechanisms for failed deployments
- Automatic rollback triggers for critical metrics
- Branch restoration for failed milestone integrations
