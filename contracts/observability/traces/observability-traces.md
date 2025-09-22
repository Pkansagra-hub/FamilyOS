Spans:
- obs.scrape: attributes { endpoint, success, status_code }
- obs.log.write: { level, masked:boolean }
- obs.span.export: { count }
Parent/child: API request span → module spans chain via context propagation (trace_id).
