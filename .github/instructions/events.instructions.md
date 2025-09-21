---
description: Events bus, topics, validators, and handlers.
applyTo: "events/**/*,contracts/events/**/*"
---
# 📨 Events — Topics & Handlers

## 1) New Topic Flow
- Add/modify **schema** in `contracts/events/*` first (update examples).
- Keep envelope invariants intact; bump policy/versions if needed.

## 2) Emitting
- Construct envelope with `policy_version`, `band`, `actor/device/space_id`, `qos`.
- Sign/encrypt if required by policy; redact before emit; emit metrics.

## 3) Handling
- Validate against contract; **idempotent** processing; avoid side effects before validation.
- Use UnitOfWork for storage writes; publish receipts; instrument spans/metrics.

## 4) Tests
- Contract tests validate examples; integration tests round-trip emit→handle→store.