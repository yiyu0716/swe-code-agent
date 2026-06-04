#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
DATASET="${SWETRACE_SWEBENCH_SUBSET:-/data/yiyuldx/swe/cache/swebench_lite}"
SPLIT="${SWETRACE_SWEBENCH_SPLIT:-dev}"
OUT="${SWETRACE_TASKS_OUT:-/data/yiyuldx/swe/outputs/tasks/swebench_lite_dev.jsonl}"
LIMIT="${SWETRACE_TASK_LIMIT:-10}"

args=(
  --dataset "${DATASET}"
  --split "${SPLIT}"
  --out "${OUT}"
  --limit "${LIMIT}"
)
if [[ -n "${SWETRACE_TASK_REPO:-}" ]]; then
  args+=(--repo "${SWETRACE_TASK_REPO}")
fi
if [[ -n "${SWETRACE_SKIP_EXISTING_RUNS:-}" ]]; then
  args+=(--skip-existing "${SWETRACE_SKIP_EXISTING_RUNS}")
fi

"${PYTHON}" -m swetrace.collect.select_swebench_tasks "${args[@]}"
