#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
RUNS="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"
OUT="${SWETRACE_DATASETS:-/data/yiyuldx/swe/outputs/datasets}"
"${PYTHON}" -m swetrace.data_builder.build_from_runs \
  --runs "${RUNS}" \
  --out "${OUT}"
