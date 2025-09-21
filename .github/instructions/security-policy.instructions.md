---
description: PEP, ABAC/RBAC, redaction, MLS/E2EE, and band rules.
applyTo: "policy/**/*,security/**/*,api/**/*.py,events/**/*.py,storage/**/*.py"
---
# 🔐 Security & Policy — PEP/ABAC/MLS

## 1) Enforcement
- All entrypoints pass through **PEP**; enforce **RBAC/ABAC** and **space/band** constraints.
- Apply **redaction** on outputs; validate before returning/emit.

## 2) Crypto & Receipts
- Use required **MLS/E2EE**; sign envelopes/receipts where contracts mandate.
- Rotate keys per policy; never downgrade crypto in prod.

## 3) Privacy
- Minimize data; avoid logging secrets/PII; respect DSAR/PII obligations and tombstone cascades.

## 4) Tests
- Security tests for access decisions; regression tests for redaction/obligations.