Scenarios:
- Validate episodic_event/segment/link JSON against schemas.
- Idempotent append: same envelope.event_id -> single persisted event.
- WAL replay safety: order preserved by ts within space.
- Redaction obligations for RED/BLACK bands in export path.
