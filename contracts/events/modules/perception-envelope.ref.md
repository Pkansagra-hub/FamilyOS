# Envelope Binding — Perception

Required envelope fields: `schema_version`, `id`, `ts`, `topic=SENSORY_FRAME`, `band`, `actor`, `device`, `space_id`, `policy_version`, `abac`, `rbac`, `qos`, `signature`.

Bands:
- **GREEN**: low-risk sensors
- **AMBER**: mic/camera unless device_trust=high
- **RED**: blocked by default for raw frames
Obligations on AMBER/RED: redact PII, audit log, local-only processing.
