#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
/root/swe/.venv/bin/python -m swetrace.collect.run_task \
  --task examples/fake_task.json \
  --agent fake \
  --out runs
