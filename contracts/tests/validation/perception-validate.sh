#!/usr/bin/env bash
set -euo pipefail
# Prefer Python check-jsonschema; fallback to ajv if available.

if command -v check-jsonschema >/dev/null 2>&1; then
  check-jsonschema --schemafile storage/schemas/sensory_frame.schema.json storage/schemas/frame_record.schema.json
else
  if command -v ajv >/dev/null 2>&1; then
    ajv compile -s storage/schemas/sensory_frame.schema.json
    ajv compile -s storage/schemas/frame_record.schema.json
  else
    echo "Install check-jsonschema (pip) or ajv (npm) to validate." >&2
    exit 1
  fi
fi

echo "Perception contract schema validation OK."
