This module **must** use `contracts/events/envelope.schema.json` fields:
- Required: event_id, event_ts, actor, user_id, device_id, space_id, caps, band, policy_version, qos.
- Dedupe: `dedupe_key` computed from catalog entry.
- Bands: RED masks event payload to metadata only; BLACK denies emission.
