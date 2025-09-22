#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.."; pwd)"
schemas=$(jq -r 'to_entries[] | "\(.key) \(.value)"' "$root/tests/schema-index.json")
python - <<'PY'
import json,sys,os
from jsonschema import validate, Draft7Validator
root=os.path.dirname(os.path.dirname(__file__))
samples={
 "EpisodicEvent": "tests/examples/episodic_event.example.json",
 "EpisodicSegment":"tests/examples/episodic_segment.example.json"
}
idx=json.load(open(os.path.join(root,"tests/schema-index.json")))
for name,rel in idx.items():
    schema=json.load(open(os.path.join(root,rel)))
    Draft7Validator.check_schema(schema)
    if name in samples:
        data=json.load(open(os.path.join(root,samples[name])))
        validate(data, schema)
print("OK")
PY
