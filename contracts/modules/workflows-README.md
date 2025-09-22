# workflows/ — Contract Bundle (v1.0.0)

Deterministic orchestration with durable state and idempotent steps; event-first interface.

**Events**
- WORKFLOW_STARTED, UPDATED, COMPLETED, FAILED, RETRIED.

**Storage**
- Append-with-version `workflow_state` rows with current snapshot fields.

**Policy**
- Transitions require AMBER band; emits audit events.
