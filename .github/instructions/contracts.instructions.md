---
description: Contracts-first workflow for APIs, events, and storage.
applyTo: "contracts/**/*"
---
# 📜 Contracts — API · Events · Storage

## 0) Prime Directive
- **Any I/O change starts here** and must pass **contract CI** before implementation.
- **Use automation tools**: `contracts/automation/contract_suite.py`, `validation_helper.py`, `interactive_contract_builder.py`

## 1) Versioning & Policy
- **SemVer** for breaking changes; include **migration plan** and adapters.
- Keep **envelope invariants** frozen: `band`, `obligations`, `policy_version`, `id/ts/topic`, `actor/device/space_id`, `qos`, `hashes`, `signature`.
- **Validation command**: `python scripts/contracts/check_envelope_invariants.py`

## 2) Contract Artifacts (Exact Paths)
- **API**: `contracts/api/openapi/modules/[service]-openapi.yaml` (routes, shapes, errors)
- **Events**: `contracts/events/modules/[service]-catalog.json` + topic schemas in `contracts/events/schemas/`
- **Storage**: `contracts/storage/schemas/[service]-*.schema.json` (entities, relationships, indices)
- **Examples**: `contracts/examples/[service]/` (request/response samples for validation)
- **Pipelines**: `contracts/pipelines/P[XX]-[name].yaml` (P01-P20 cognitive processing pipelines)

## 3) Quality Gates (Automated Validation)
- **Schema Validation**: `python contracts/automation/validation_helper.py --file [contract-file]`
- **Contract Suite**: `python contracts/automation/contract_suite.py validate --all`
- **Storage Validation**: `python scripts/contracts/storage_validate.py`
- **Syntax Check**: `python scripts/contracts/contract_helper.py validate`
- **Coverage**: `additionalProperties: false` where feasible; all enums documented with examples

## 4) Contract Generation Tools
- **Interactive Builder**: `python contracts/automation/interactive_contract_builder.py`
- **Template Generation**: `python contracts/automation/contract_suite.py generate --service [name] --type [api|events|storage]`
- **Brain-Inspired Templates**: Available for hippocampus, cortex, cerebellum, amygdala, thalamus, brainstem
- **Pipeline Generation**: `python contracts/automation/pipeline_enhancer.py --brain-region [region]`

## 5) CI Expectations
- **Pre-commit**: Schema lint/validate + example validation
- **Contract Changes**: Run `python contracts/automation/validation_helper.py` before commit
- **Freeze Creation**: `python contracts/automation/contract_suite.py freeze --version [x.y.z]`
- **Diff Analysis**: Automatic semver impact labeling (patch/minor/major)
- **Documentation**: Auto-generate API docs from OpenAPI specs

## 6) Contract Workflow Commands
```bash
# Start new contract development
python contracts/automation/interactive_contract_builder.py

# Validate existing contracts
python contracts/automation/validation_helper.py --all
python scripts/contracts/storage_validate.py

# Generate brain-inspired contracts
python contracts/automation/contract_suite.py generate --brain-region hippocampus --type storage

# Create production freeze
python contracts/automation/contract_suite.py freeze --version 1.0.0

# Full validation suite
python scripts/contracts/storage_validate.py && \
python scripts/contracts/contract_helper.py validate && \
python scripts/contracts/check_envelope_invariants.py
```

## 7) Breaking Change Process
1. **Analysis**: Use `python contracts/automation/validation_helper.py --breaking-change-analysis [file]`
2. **Migration Plan**: Document in `contracts/_migration/[version]/migration-plan.md`
3. **Adapters**: Create in `contracts/_migration/[version]/adapters/`
4. **Validation**: Test with existing examples in `contracts/examples/`
5. **Freeze**: Create new major version freeze before implementation
