#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
OUT="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"
"${PYTHON}" -m swetrace.collect.run_task \
  --task examples/fake_task.json \
  --agent fake \
  --out "${OUT}"
