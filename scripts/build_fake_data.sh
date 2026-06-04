#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
"${PYTHON}" -m swetrace.data_builder.build_from_runs \
  --runs runs \
  --out outputs/datasets
