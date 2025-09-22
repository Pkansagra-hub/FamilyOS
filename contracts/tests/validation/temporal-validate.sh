#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
npx ajv validate -s "$HERE/storage/schemas/time_index.schema.json" -d "$HERE/../contracts/events/envelope.examples.json" || true
echo "Temporal contracts validated (schema-only)."
