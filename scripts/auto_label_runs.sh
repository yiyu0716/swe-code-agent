#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
RUNS="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"
"${PYTHON}" -m swetrace.labeling.auto_label_runs --runs "${RUNS}"
