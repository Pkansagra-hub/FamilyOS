#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.."; pwd)"
ajv validate -s "$ROOT/events/catalog.json"
ajv validate -s "$ROOT/storage/schemas/retrieval_trace.schema.json"
ajv validate -s "$ROOT/storage/schemas/retrieval_cache_entry.schema.json"
echo "retrieval contracts validated."
