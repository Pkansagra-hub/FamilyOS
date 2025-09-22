Spans:
- services.write.accept: attrs: space_id, payload_hash
- services.index.run: attrs: index_kind
- services.health.emit: attrs: service, status
Parent from envelope.trace when present.
