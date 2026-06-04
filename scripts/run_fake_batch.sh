#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
OUT="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"
SUMMARY="${SWETRACE_SUMMARY:-/data/yiyuldx/swe/outputs/reports/summary.csv}"
"${PYTHON}" -m swetrace.collect.run_batch \
  --tasks benchmarks/fake_tasks.jsonl \
  --agent fake \
  --out "${OUT}" \
  --summary "${SUMMARY}"
