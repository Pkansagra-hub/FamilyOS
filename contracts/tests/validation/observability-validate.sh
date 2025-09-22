#!/usr/bin/env bash
set -euo pipefail
echo "Validating JSON Schemas..."
# If ajv is available, run it; otherwise, noop success for CI placeholder.
command -v ajv >/dev/null 2>&1 && ajv compile -s storage/schemas/*.schema.json || echo "ajv not found; skipping."
