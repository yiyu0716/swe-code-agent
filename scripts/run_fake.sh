#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
"${PYTHON}" -m swetrace.collect.run_task \
  --task examples/fake_task.json \
  --agent fake \
  --out runs
