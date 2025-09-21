---
description: Safe, idempotent scripts policy.
applyTo: "scripts/**/*.sh,scripts/**/*.py"
---
# ⚙️ Scripts — Safety & Idempotency

## 1) General
- Scripts must be **idempotent** and **side-effect explicit**.
- No secrets in source. Read creds from env/secret manager. Never `echo` secrets.

## 2) Shell (`*.sh`)
- Start with: `#!/usr/bin/env bash` and `set -Eeuo pipefail`.
- Use `IFS=$'\n\t'`; quote all expansions; check exit codes.
- Provide `--dry-run`; default to **safe** behavior.

## 3) Python Scripts (`*.py`)
- Entry point guard: `if __name__ == "__main__":` with `argparse`.
- Use project logger (structured JSON). No prints.
- Type hints, small functions, unit tests when non-trivial.

## 4) Environments
- Target **staging** by default. Require an explicit flag to hit **production**.
- Respect proxies, timeouts, and retries with backoff.

## 5) Don’t
- Don’t modify schema/contracts; that belongs in `contracts/**` with CI.
- Don’t write outside repo boundaries or temp dirs without flags.