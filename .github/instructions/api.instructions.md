---
description: API layer rules (routes, schemas, middleware).
applyTo: "api/**/*.py"
---
# 🌐 API Plane — Handlers & Middleware

## 1) Start at Contracts
- Update **OpenAPI** first under `contracts/api/` and add examples.

## 2) Handler Checklist
- Define **request/response** models; validate inputs early.
- Enforce **PEP** (RBAC/ABAC, bands, space) at the start of the handler.
- **Observability**: create span; emit metrics and structured logs.
- Map exceptions to consistent error models and status codes.
- **Idempotency** for writes; include correlation/request ids in responses when applicable.

## 3) Middleware
- Ensure auth/context propagation; attach correlation ids.
- Body size/time limits; uniform error serialization.

## 4) Tests
- Integration tests through the real ASGI app; use example payloads from `contracts/`.