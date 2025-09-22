Checks executed:
- API layer: `X-Actor`, `X-Device`, `X-Contract-Version` validated (global).
- Before enqueue RECALL_REQUESTED: ABAC (actor.caps includes RECALL; space binding).
- Before emitting RECALL_RESULT: band obligations applied to snippets.
