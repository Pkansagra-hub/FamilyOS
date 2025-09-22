AuthZ checks:
- On RANGE_REQUEST consume: verify `band ∈ {GREEN,AMBER}` and space membership.
- On index write: require AMBER band; enforce obligations (audit).
- On response emit: ensure redaction policy applied.
