#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
"${PYTHON}" -m swetrace.labeling.auto_label_runs --runs runs
