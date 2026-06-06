#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
HOST="${SWETRACE_REVIEW_HOST:-127.0.0.1}"
PORT="${SWETRACE_REVIEW_PORT:-20039}"
RUNS="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"
QUEUE="${SWETRACE_REVIEW_QUEUE:-/data/yiyuldx/swe/outputs/reports/manual_review_queue.jsonl}"
ANNOTATIONS="${SWETRACE_REVIEW_ANNOTATIONS:-/data/yiyuldx/swe/outputs/reports/manual_annotations.jsonl}"
DPO_DATASET="${SWETRACE_DPO_DATASET:-/data/yiyuldx/swe/outputs/datasets/v0.2}"

"${PYTHON}" -m swetrace.labeling.review_server \
  --host "${HOST}" \
  --port "${PORT}" \
  --reports "/home/yiyuldx/swe/reports" \
  --runs "${RUNS}" \
  --queue "${QUEUE}" \
  --annotations "${ANNOTATIONS}" \
  --dpo-dataset "${DPO_DATASET}"
