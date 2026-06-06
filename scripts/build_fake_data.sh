#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
RUNS="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"
OUT="${SWETRACE_DATASETS_LEGACY:-/data/yiyuldx/swe/outputs/datasets/legacy_build_from_runs}"
"${PYTHON}" -m swetrace.data_builder.build_from_runs \
  --runs "${RUNS}" \
  --out "${OUT}"
