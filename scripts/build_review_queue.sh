#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
"${PYTHON}" -m swetrace.labeling.review_queue \
  --runs "${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}" \
  --out "${SWETRACE_REVIEW_QUEUE:-/data/yiyuldx/swe/outputs/reports/manual_review_queue.jsonl}"
