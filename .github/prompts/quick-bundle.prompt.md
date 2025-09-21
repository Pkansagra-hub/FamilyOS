````prompt
# ⚡ Contract Quick Bundle & Validation Prompts

Use these prompts for fast contract bundling, validation, and troubleshooting workflows.

---

## 🔄 **Quick Bundle & Validate**

```
I need to quickly lint, bundle, and validate OpenAPI contracts:

**Current Context:**
- **Contract Files:** [Which contracts need bundling]
- **Recent Changes:** [What was modified recently]
- **Expected Issues:** [Any known problems to watch for]
- **Urgency Level:** [Quick fix/Thorough validation/Release preparation]

**Quick Bundle Workflow:**
1. Lint the main OpenAPI specification
2. Bundle all referenced files into single specification
3. Run contract validation suite
4. Identify and resolve common issues

**Execution Steps:**
1. Run: `npx @redocly/cli@latest lint contracts/api/openapi/main.yaml`
2. Run: `npx @redocly/cli@latest bundle contracts/api/openapi/main.yaml -o contracts/api/openapi.v1.yaml`
3. Run VS Code task: `contracts:validate` (fallback: `python scripts/contracts/storage_validate.py`)
4. If errors detected, apply appropriate fixes

**Common Issue Resolution:**
- **Missing 4xx responses or security:** Chain to "Add 4xx & Security" prompt
- **JSON Schema dialect issues:** Chain to "OAS 3.1 Alignment" prompt
- **Validation errors:** Check contract syntax and references
- **Bundle failures:** Verify file paths and $ref resolution

**Acceptance Criteria:**
- [ ] Lint passes with 0 errors
- [ ] Bundle generation succeeds
- [ ] Contract validation exits with code 0
- [ ] No breaking changes introduced
- [ ] All $ref references resolve correctly

**Success Indicators:**
- Lint: 0 errors
- Bundle: Successful generation
- Validate: exit 0
- No regression in existing functionality

Please help me execute the quick bundle workflow and resolve any issues found.
```

---

## 🔧 **Bundle Troubleshooting**

```
I'm encountering issues with contract bundling or validation:

**Error Details:**
- **Command That Failed:** [Lint/Bundle/Validate command]
- **Error Messages:** [Specific error output]
- **File Paths:** [Which contract files are involved]
- **Recent Changes:** [What was modified before the error]

**Error Categories:**
- **Lint Errors:** Syntax, formatting, or schema violations
- **Bundle Errors:** File references, circular dependencies, or path issues
- **Validation Errors:** Contract compliance or structural problems
- **Schema Errors:** Type definitions or validation rule conflicts

**Diagnostic Information:**
- **Contract Structure:** [Main files and dependencies]
- **Reference Chain:** [$ref paths and dependencies]
- **Schema Version:** [OpenAPI version being used]
- **Tool Versions:** [Redocly CLI and validation tool versions]

Please help me diagnose and fix the contract bundling issues.
```

---

## 🚀 **Release Preparation Bundle**

```
I need to prepare contracts for release with thorough validation:

**Release Context:**
- **Release Version:** [Version number and type]
- **Changes Made:** [Summary of contract changes]
- **Breaking Changes:** [Any breaking changes and migration plan]
- **Deployment Timeline:** [When this needs to be ready]

**Comprehensive Validation:**
- Full contract suite validation
- Backward compatibility checking
- Example validation
- Security posture verification
- Performance impact assessment

**Release Checklist:**
- [ ] All contracts lint without errors
- [ ] Bundle generation successful
- [ ] Full validation suite passes
- [ ] Backward compatibility verified
- [ ] Examples validate against schemas
- [ ] Security requirements met
- [ ] Documentation updated
- [ ] Migration plan documented (if breaking changes)

Please help me prepare the contracts for production release.
```
````
