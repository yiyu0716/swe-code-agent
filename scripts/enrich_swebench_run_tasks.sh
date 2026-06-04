#!/usr/bin/env bash
set -euo pipefail

PYTHON="${SWETRACE_PYTHON:-python}"
DATASET="${SWETRACE_SWEBENCH_SUBSET:-/data/yiyuldx/swe/cache/swebench_lite}"
RUNS="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"
SPLIT="${SWETRACE_MINI_SPLIT:-dev}"

"${PYTHON}" -m swetrace.collect.enrich_swebench_run_tasks \
  --dataset "${DATASET}" \
  --runs "${RUNS}" \
  --split "${SPLIT}" \
  "$@"
