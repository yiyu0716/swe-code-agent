#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
QUEUE="${SWETRACE_REVIEW_QUEUE:-/data/yiyuldx/swe/outputs/reports/manual_review_queue.jsonl}"
OUT="${SWETRACE_REVIEW_ANNOTATIONS:-/data/yiyuldx/swe/outputs/reports/manual_annotations.jsonl}"

"${PYTHON}" -m swetrace.labeling.annotate_review \
  --queue "${QUEUE}" \
  --out "${OUT}" \
  "$@"
