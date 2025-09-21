# 🧭 Copilot Rules of Engagement — **Family AI with Memory-Centric Architecture**

**Core Vision:** Memory Module as the backbone of Family AI - enabling emotional intelligence, contextual awareness, and family coordination through user-controlled devices with E2EE sync.

**Architecture Foundation:**
- 🧠 **Memory Module:** Device-local storage with family sync (E2EE + CRDT)
- 🤖 **3 API Planes:** Agent (LLM), Tool (Connectors), Control (Admin)
- 👥 **Family Intelligence:** Memory sync creates contextual family awareness
- 🔐 **User-Controlled:** Simple permissions, user commands for sensitive actions

We will follow GitHub branching and PR rules as specified in section 8 below and no md files or code files will be added to root. All documentation will be added to project_planning or docs folder as specified in section 7 below.

---

# 🚨 **ABSOLUTE ZERO TOLERANCE PRODUCTION POLICY** 🚨

## **NO SIMULATIONS IN PRODUCTION - PERIOD!**

### **⚠️ CRITICAL PRODUCTION RULES - VIOLATION = IMMEDIATE REJECTION ⚠️**

**THIS IS A PRODUCTION ENVIRONMENT - NOT A PLAYGROUND**

1. **ZERO SIMULATION CODE ALLOWED:**
   - **NO `asyncio.sleep()` EVER** - Use event-driven patterns or `pass` with TODO
   - **NO `time.sleep()` EVER** - Use threading events or proper synchronization
   - **NO mock/fake/simulate delays** - Real components only
   - **NO artificial timing** - Measure real performance only
   - **NO playground behavior** - Production patterns mandatory

2. **REPLACEMENT PATTERN FOR SIMULATIONS:**
   ```python
   # ❌ FORBIDDEN - NEVER DO THIS
   await asyncio.sleep(0.1)  # simulate work
   time.sleep(delay)  # artificial delay

   # ✅ REQUIRED - ALWAYS DO THIS
   # TODO: Implement proper [feature] without simulation
   pass
   ```

3. **TESTING RESTRICTIONS:**
   - **NO SIMPLE/TRIVIAL TESTS** - Only comprehensive integration tests
   - **NO MOCK THEATER** - Use real components with WARD framework
   - **NO PLACEHOLDER TESTS** - Every test must validate real functionality

4. **PRODUCTION ENFORCEMENT:**
   - Any simulation code = **IMMEDIATE PR REJECTION**
   - Any sleep calls in production code = **IMMEDIATE PR REJECTION**
   - Any mock delays = **IMMEDIATE PR REJECTION**
   - Any playground patterns = **IMMEDIATE PR REJECTION**

**REAL PRODUCTION SYSTEMS HAVE REAL COMPONENTS AND REAL VALUES ONLY**

---

## 0) Prime Directive — **CONTRACTS FIRST** (No exceptions)
- Any I/O change (**API, events, storage, pipelines**) **starts in `contracts/**`** and passes **contract CI** *before* coding.
- Follow **SemVer** for contracts. Breaking changes ⇒ **MAJOR** bump with a **written migration plan** and adapters.
- **Frozen envelope invariants** (never break): `band`, `obligations`, `policy_version`, `id/ts/topic`, `actor/device/space_id`, `qos`, `hashes`, `signature`. See `contracts/POLICY_VERSIONING.md`.
- Required artifacts to update first:
  - `contracts/api/openapi.v1.yaml` (routes, shapes, errors)
  - `contracts/events/envelope.schema.json` and `contracts/events/*` (topics & payloads)
  - `contracts/storage/*` (schemas, receipts, unit-of-work invariants)
- **Daily commands:** `contracts/CONTRACT_CHANGE_QUICK_REF.md`
- **Complete process:** `contracts/CONTRACT_CHANGE_PROCESS.md`
- **Directory overview:** `contracts/README.md`
- **Implementation status:** `contracts/CONTRACT_IMPLEMENTATION_COMPLETE.md`

---

## 1) Read-this-first (30‑minute ramp) — **Memory-Centric Family AI**
- **Memory Architecture:** [`architecture_diagrams/`](../architecture_diagrams/) - Memory-centric Family AI diagrams
  - `architecture_diagrams/project_architecture_part1.mmd` - Memory backbone & API planes
  - `architecture_diagrams/project_architecture_part2.mmd` - Memory-driven cognitive core
  - `architecture_diagrams/project_architecture_part3.mmd` - Memory-powered intelligence systems
  - `architecture_diagrams/project_architecture_part4.mmd` - Memory infrastructure & sync
- **Family AI Vision:** [`README.md`](../README.md) - Complete Family AI vision with memory as backbone
- **Contracts:** [`contracts/contract_checklist.md`](../contracts/contract_checklist.md) - Memory-centric contract architecture
- **Memory Module:** Device-local storage with family sync via E2EE + CRDT
- **3 API Planes:** Agent (LLM memory ops), Tool (app connectors), Control (family admin)
- **User Permissions:** Simple user-controlled access with explicit commands for sensitive actions

---

## 2) Working Model (B → C → A)
**Build** the core behind a guard → **Connect** to the system → **Advance** with polish & edges.
- Read envelope schema, OpenAPI, storage contracts **before** touching code.
- Prefer additive, backwards‑compatible changes. New capabilities ship **off by default** when in doubt.

---

## 3) Security & Privacy (non‑negotiable)
- Every request hits the **Policy Enforcement Point (PEP)**; enforce **RBAC/ABAC** and **space/band** rules.
- **Redaction** must be validated on all outputs (use `policy/redactor.py`).
- **MLS/E2EE receipts & signatures** required where specified by contracts; never downgrade crypto in prod.
- **Never log PII**. Route sensitive fields through redactors; audit via `observability/audit.py` only.
- Respect **bands**: GREEN/AMBER/RED/BLACK control capability, logging, and data movement.

---

## 4) Observability or it didn't happen
Instrument anything you build:
- **Metrics:** Prometheus names **start with `familyos_…`**; use `observability/metrics.py` helpers and SLO buckets.
- **Traces/Spans:** Use `observability/trace.py` → `start_span(f"{area}.{component}.{method}")`.
- **Logs:** JSON structured via `observability/logging.py`, include correlation/context ids.
- **HTTP/ASGI middleware:** ensure `api/middleware.py` wraps new routes.
- PRs **without** metrics + spans + structured logs **will be rejected**.

---

## 5) SLOs (ship fast, stay fast)
- Meet stated **p95** budgets per device class; budget breaches must have a back‑out plan.
- **Guard risky changes** behind config/policy and document rollback.

---

## 6) Tests — *Minimum viable confidence*
Use **WARD** with real components (no "mock theater" for core).
- **Unit:** ≥70% of touched logic (type‑hinted; `mypy --strict` must pass).
- **Integration:** every I/O path changed (API ↔ events ↔ storage).
- **Contract:** any `contracts/**` delta (schemas, examples, adapters).
- **Performance:** required for any hot path touched.
- Test doubles are allowed **only** for external dependencies (network, FS).

---

## 7) Repo Hygiene
- New tests → `tests/` (mirror module layout).
- New scripts → `scripts/` (idempotent; no secrets).
- Docs belong in module READMEs / `docs/`. **No stray Markdown** in random dirs.
- Small PRs (≈ <300 LOC). Use Conventional Commits (`feat:`, `fix:`, `chore:`…).
- Python **3.11**, **Poetry** for deps; style via **ruff** (line length 100), **black** (default), **mypy --strict**.

---

## 8) Branching & Releases (Milestone-Epic-Issue Strategy)
**Structured development following milestone-driven GitFlow with contract-first methodology**

### **Branch Hierarchy:**
- **main** (protected) → production deploys only
- **develop** → active development branch (dev environment)
- **milestone/M{number}-{name}** → milestone integration branches
- **epic/M{milestone}.{epic}-{name}** → epic consolidation branches
- **issue/{epic-id}.{issue-id}-{name}** → individual issue implementation

### **Branch Flow:**
- **Work Level:** Individual issues/sub-issues in `issue/` branches
- **Epic Level:** Merge completed `issue/` branches to `epic/` branch
- **Milestone Level:** Merge completed `epic/` branches to `milestone/` branch
- **Integration:** Merge verified `milestone/` branch to `develop`
- **Production:** Merge `develop` to `main` (protected, requires approval)

### **Naming Conventions:**
```bash
# Milestone branches
milestone/M1-foundation
milestone/M2-cognitive-core
milestone/M3-intelligence-layer

# Epic branches (within milestone)
epic/M1.1-event-bus-infrastructure
epic/M1.2-storage-foundation
epic/M1.3-basic-api-layer

# Issue branches (within epic)
issue/1.1.1-event-envelope-design
issue/1.1.2-basic-publisher-interface
issue/1.2.1-unit-of-work-pattern
```

### **Development Workflow:**
1. **Issue Work:** Create `issue/` branch from appropriate `epic/` branch
2. **Contract First:** Update contracts before implementation
3. **Implementation:** Code behind feature flags with observability
4. **Testing:** Unit + integration + contract tests
5. **Epic Merge:** PR from `issue/` → `epic/` branch
6. **Milestone Merge:** PR from `epic/` → `milestone/` branch
7. **Development Integration:** PR from `milestone/` → `develop`
8. **Production Release:** PR from `develop/` → `main`

### **PR Targeting Rules:**
- `issue/*` → `epic/*` (individual feature completion)
- `epic/*` → `milestone/*` (epic completion with verification)
- `milestone/*` → `develop` (milestone completion with full testing)
- `develop` → `main` (production release with approval)
- `hotfix/*` → `main` (emergency fixes, then back-merge to develop)

### **CI/CD Enforcement:**
- Enforce branch naming conventions in CI
- Different validation levels for different branch types
- Contract validation required for all merges
- Full test suite for milestone and develop merges
- Release tagging for develop → main merges

---

## 9) PR Template (fill it, no blanks)
**What & Why:** scope + contract delta
**Flag/Config:** new or existing toggle & default
**Security:** PEP/ABAC/MLS/E2EE impact
**Observability:** metrics + spans added (names)
**Tests:** unit / integration / contract / perf paths
**SLOs:** target p95 + evidence (before/after)
**Docs:** updated READMEs / ADR as needed

---

## 10) Don'ts (without approval)
- Add new deps, change contracts, bypass PEP, rely on cloud, or blow SLOs.
- Create files outside owned areas, add placeholders, or leave "temporary" hacks.
- Log secrets/PII or disable redaction in prod.
- **NEVER ADD SIMULATION CODE** - Use real components and TODO comments only.
- **NEVER CREATE SIMPLE/TRIVIAL TESTS** - Only comprehensive integration tests allowed.

---

## 11) Development Workflows & Automation
**Standardized workflows** ensure consistency and reduce errors across all development activities.

### **Workflow Instructions** (`.github/instructions/`)
- **Contract Changes:** Follow `.github/instructions/contract-change-workflow.instructions.md` for all contract modifications
- **Milestone Workflow:** Use `.github/instructions/milestone-epic-issue-workflow.instructions.md` for structured development
- **New Services:** Use `.github/instructions/new-service-development.instructions.md` for service creation
- **New Modules:** Follow `.github/instructions/new-module-development.instructions.md` for module development
- **Testing:** Reference `.github/instructions/testing-requirements.instructions.md` for comprehensive testing standards
- **Documentation:** Use `.github/instructions/documentation-standards.instructions.md` for all documentation

### **Standardized Prompts** (`.github/prompts/`)
- **Contract Change:** Use `.github/prompts/contract-change.prompt.md` for contract analysis prompts
- **Milestone Planning:** Use `.github/prompts/milestone-epic-issue-planning.prompt.md` for project planning
- **New Service:** Use `.github/prompts/new-service.prompt.md` for service planning prompts
- **New Module:** Use `.github/prompts/new-module.prompt.md` for module design prompts
- **Bug Fix:** Use `.github/prompts/bug-fix.prompt.md` for debugging and analysis prompts
- **Feature Addition:** Use `.github/prompts/feature-addition.prompt.md` for feature planning prompts

### **VS Code Task Automation** (`.vscode/tasks.json`)
**Milestone-Epic-Issue Workflow:**
- `workflow:milestone-plan` → Plan milestone structure and epic breakdown
- `workflow:epic-create` → Create epic branch and setup
- `workflow:issue-start` → Start issue development with contracts-first
- `branch:milestone-status` → Check progress across all branches
- `branch:epic-merge` → Merge issue to epic branch
- `branch:milestone-merge` → Merge epic to milestone branch

**Contract Tasks:**
- `contracts:validate` → Validate storage contracts
- `contracts:validate-syntax` → Check contract syntax
- `contracts:check-invariants` → Verify envelope invariants
- `contracts:full-validation` → Complete contract validation suite

**Service Development:**
- `service:scaffold-new` → Create new service structure
- `service:create-contracts` → Initialize service contracts

**Quality Assurance:**
- `ci:fast` → Quick CI checks (lint, type, test)
- `ci:full-validation` → Complete validation pipeline

**Access Tasks:**
- `Ctrl+Shift+P` → "Tasks: Run Task" → select any workflow
- `tools:open-prompts` → Open prompts folder
- `tools:open-instructions` → Open instructions folder
- `tools:open-contracts` → Open contracts folder

---

## 12) Daily Loop (Milestone-Driven Development)
`pull develop → checkout milestone branch → create epic branch (if needed) → create issue branch → run workflow task → use standardized prompts → update contracts first → write failing tests → implement behind feature flag → add metrics/spans/logs → run contract & test validation → small PR to epic → epic completion PR to milestone → milestone verification PR to develop`

### **Detailed Daily Workflow:**
1. **Start Work:** `git checkout milestone/M{X}-{name} && git pull`
2. **Epic Branch:** `git checkout epic/M{X}.{Y}-{name}` (create if needed)
3. **Issue Branch:** `git checkout -b issue/{epic-id}.{issue-id}-{description}`
4. **Contracts First:** Update `contracts/**` and validate before coding
5. **Implementation:** Code with feature flags, observability, and tests
6. **Validation:** Run `contracts:validate` + `ci:fast` + full test suite
7. **Epic PR:** Small focused PR from `issue/` → `epic/`
8. **Milestone Integration:** After epic completion, PR `epic/` → `milestone/`
9. **Development Integration:** After milestone verification, PR `milestone/` → `develop`

---

## 13) Module map (for Copilot & navigation)
- **API plane:** `api/` (routers, schemas, middleware, auth/rbac)
- **Events:** `events/` (bus, types, validation, handlers, middleware)
- **Policy:** `policy/` (abac/rbac, consent, redactor, space policy)
- **Storage:** `storage/` (stores, `unit_of_work.py`, sqlite utilities, vector/fts)
- **Cognition:** `core/`, `arbitration/`, `hippocampus/`, `retrieval/`, `prospective/`, `learning/`
- **Observability:** `observability/` (logging/metrics/trace/audit/context/middleware)
- **Security:** `security/` (keys, ratchet, mls groups, encryptor)
- **Supervisor/Services:** `supervisor/`, `services/`
- **Workflows & Sync:** `workflows/`, `sync/`

**When adding a route:** update OpenAPI → add router/handler → schemas → policy checks → obs → tests.
**When adding an event/topic:** update contracts → `events/types.py` → validators → handlers → obs → tests.
**When touching storage:** update `contracts/storage/*` → `unit_of_work` invariants → receipts → migration plan → tests.

---

## 14) GitHub & VS Code integration (how this file is used)
- Store this file at **`.github/copilot-instructions.md`** (note the hyphen).
- VS Code: enable the setting **`github.copilot.chat.codeGeneration.useInstructionFiles`** to apply it to all chats.
- You can also add topic‑specific instruction files (`.github/instructions/*.instructions.md`) with `applyTo` globs for language‑ or task‑specific rules as needed.

---

## 15) Mindset
**Contracts are law.** Clarity over cleverness. **Production over perfectionism theater.**
If scope is ambiguous, propose the smallest contract‑first change and document trade‑offs.
**Ask if unsure.** When in doubt, ping a team lead or architect for guidance.
**We're building a long‑lived system.** Favor maintainability, operability, and simplicity.
**We are using WARD.** Write tests first, make them pass, then refactor. Example to run it: `python -m ward test --path tests/storage/test_progress_tracker.py`
