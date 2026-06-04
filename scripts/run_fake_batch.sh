#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
/root/swe/.venv/bin/python -m swetrace.collect.run_batch \
  --tasks benchmarks/fake_tasks.jsonl \
  --agent fake \
  --out runs \
  --summary outputs/reports/summary.csv
