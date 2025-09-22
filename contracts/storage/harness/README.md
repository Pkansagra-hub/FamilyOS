# Storage contracts validation harness

Validate `contracts/storage/examples/` against JSON Schemas in `contracts/storage/schemas/`.

## Run
```bash
bash contracts/storage/harness/validate.sh contracts/storage/examples
```
- Uses **ajv-cli** if installed; else a **jq** smoke check.
- Edit `schema-index.json` if your schema filenames differ.
