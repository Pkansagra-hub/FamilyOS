#!/usr/bin/env bash
# Storage contracts validation harness
# Uses ajv-cli (draft 2020-12) if present; else jq smoke checks.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCHEMAS="${SCHEMA_DIR:-$ROOT/contracts/storage/schemas}"
EXAMPLES="${1:-$ROOT/contracts/storage/examples}"
INDEX="${INDEX_JSON:-$ROOT/contracts/storage/harness/schema-index.json}"

if [[ ! -d "$SCHEMAS" || ! -d "$EXAMPLES" || ! -f "$INDEX" ]]; then
  echo "Missing schemas/examples/index" >&2; exit 2
fi

if command -v ajv >/dev/null 2>&1; then
  echo "→ ajv validate (draft 2020-12)"
  rc=0
  while IFS= read -r line; do
    ex="${line%% *}"; sch="${line##* }"
    ex_path="$EXAMPLES/$ex"; sch_path="$SCHEMAS/$sch"
    if [[ -f "$ex_path" && -f "$sch_path" ]]; then
      echo "  - $ex ⇢ $sch"
      ajv validate -s "$sch_path" -d "$ex_path" --spec=draft2020 || rc=$?
    else
      echo "  ! skip (missing): $ex_path or $sch_path"
    fi
  done < <(jq -r '.mappings[] | "\(.example) \(.schema)"' "$INDEX")
  exit $rc
fi

if command -v jq >/dev/null 2>&1; then
  echo "→ jq smoke checks"
  rc=0
  while IFS= read -r req; do
    file="$(echo "$req" | jq -r '.example')"
    ex_path="$EXAMPLES/$file"
    keys="$(echo "$req" | jq -c '.keys')"
    jq -e --argjson keys "$keys" '
      . as $d | ($keys | all($d|has(.)))' "$ex_path" >/dev/null || rc=$?
  done < <(jq -c '.smoke.required_sets[]' "$INDEX")
  exit $rc
fi

echo "Install ajv-cli (npm i -g ajv-cli) or jq" >&2; exit 2
