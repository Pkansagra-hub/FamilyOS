#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.."; pwd)"
ajv validate -s "$ROOT/events/catalog.json"
ajv validate -s "$ROOT/storage/schemas/decision_log.schema.json"
ajv validate -s "$ROOT/storage/schemas/risk_assessment.schema.json"
echo "arbitration contracts validated."
