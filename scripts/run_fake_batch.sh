#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
"${PYTHON}" -m swetrace.collect.run_batch \
  --tasks benchmarks/fake_tasks.jsonl \
  --agent fake \
  --out runs \
  --summary outputs/reports/summary.csv
