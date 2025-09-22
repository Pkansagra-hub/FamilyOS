#!/usr/bin/env bash
set -euo pipefail
if command -v check-jsonschema >/dev/null 2>&1; then
  check-jsonschema --schemafile storage/schemas/schedule.schema.json storage/schemas/reminder_state.schema.json
else
  echo "Install check-jsonschema to validate." >&2; exit 1
fi
echo "Prospective contract schema validation OK."
