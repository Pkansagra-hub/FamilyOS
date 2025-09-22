# Prospective (P05) Contract (v1)

Implements triggers/reminders under policy. Reuses global events:
- `PROSPECTIVE_SCHEDULE@1.0` (payload schema exists),
- `PROSPECTIVE_REMIND_TICK@1.0` (payload schema exists).

Provides module HTTP for trigger CRUD (OpenAPI below). Everything on-device; AMBER for write ops.

Assumptions: `prospective/README.md` intent is authoritative; code is stubbed; DB schema defined here.
