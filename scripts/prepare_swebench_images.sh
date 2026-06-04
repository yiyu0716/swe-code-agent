#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
TASKS="${SWETRACE_TASKS:-/data/yiyuldx/swe/outputs/tasks/swebench_lite_dev.jsonl}"
OUT="${SWETRACE_IMAGE_MANIFEST:-/data/yiyuldx/swe/outputs/reports/swebench_images.jsonl}"
TIMEOUT="${SWETRACE_DOCKER_PULL_TIMEOUT_SECONDS:-900}"

args=(--tasks "${TASKS}" --out "${OUT}" --timeout-seconds "${TIMEOUT}")
if [[ "${SWETRACE_DRY_RUN:-0}" == "1" ]]; then
  args+=(--dry-run)
fi

"${PYTHON}" -m swetrace.collect.prepare_swebench_images "${args[@]}"
