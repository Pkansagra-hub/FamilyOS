#!/usr/bin/env bash
set -euo pipefail
ROOT="$(dirname "$0")/.."
python3 - <<'PY'
import json,sys,os
try:
  import jsonschema
except ImportError:
  print("jsonschema not installed; skip validation."); sys.exit(0)
base=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
with open(os.path.join(base,"tests","schema-index.json")) as f: idx=json.load(f)
for name,path in idx.items():
  import json
  with open(os.path.join(base,path)) as sf: schema=json.load(sf)
  jsonschema.Draft202012Validator.check_schema(schema)
print("OK: schemas compile.")
PY
