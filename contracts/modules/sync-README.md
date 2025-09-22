# Sync (P07) Contract (v1)

CRDT-based, offline-first P2P replication with MLS/E2EE hooks. HTTP provides push/pull surfaces. Storage covers peers, vector clock, op log.

Reuse: `contracts/storage/crdt.schema.json` for CRDT `data` envelope. All network exchanges audited via events.
