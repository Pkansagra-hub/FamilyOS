---
description: Storage, UnitOfWork, migrations, and safety.
applyTo: "storage/**/*.py,migrations/**/*,contracts/storage/**/*"
---
# 💾 Storage — UoW & Migrations

## 1) UnitOfWork
- Atomic commits across stores; publish **receipts**; enforce invariants.
- Use parameterized queries; avoid raw string interpolation.

## 2) Schemas & Models
- Reflect **contracts/storage**; migrations must be **forward- and backward-compatible** where feasible.

## 3) Migrations
- Idempotent, reversible when possible; include data backfill steps.
- Tests for upgrade/downgrade; document operational impact.

## 4) Performance & Safety
- Indices for hot paths; avoid N+1 queries.
- Respect **bands/spaces** when persisting or reading data.