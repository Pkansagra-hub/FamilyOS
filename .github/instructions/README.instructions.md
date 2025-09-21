---
description: Index of all workspace instructions files.
applyTo: "**/*"
---
# 📚 Instructions Index (.github/instructions)

These instruction files are automatically loaded by **Copilot Chat** (when enabled) and applied based on `applyTo` globs.

- `python.instructions.md` — Python dev standards (ruff/black/mypy/ward).
- `tests.instructions.md` — Test layout, coverage, contract & integration rules.
- `scripts.instructions.md` — Safe/idempotent scripts (bash/python).
- `contracts.instructions.md` — Contracts-first rules (API, events, storage).
- `contract-change-workflow.instructions.md` — Complete contract change process.
- `milestone-epic-issue-workflow.instructions.md` — Structured development workflow.
- `new-service-development.instructions.md` — Service creation following contracts-first methodology.
- `new-module-development.instructions.md` — Adding modules to existing services.
- `testing-requirements.instructions.md` — Testing standards and coverage requirements.
- `documentation-standards.instructions.md` — Documentation standards and templates.
- `api.instructions.md` — API handlers & middleware.
- `events.instructions.md` — Event topics, envelope, handlers.
- `storage.instructions.md` — UnitOfWork, migrations, schema safety.
- `observability.instructions.md` — Metrics/spans/logs standards.
- `security-policy.instructions.md` — PEP, ABAC/RBAC, redaction, MLS/E2EE.
- `docs.instructions.md` — Docs/README/ADR guidelines.
- `github-workflows.instructions.md` — CI/CD safety rails.

> Enable in VS Code: `github.copilot.chat.codeGeneration.useInstructionFiles = true`
> Location: `.github/instructions/*.instructions.md`
