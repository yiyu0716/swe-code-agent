#!/usr/bin/env bash
set -euo pipefail

PYTHON="${SWETRACE_PYTHON:-python}"
RUNS="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"

"${PYTHON}" -m swetrace.collect.recover_mini_runs --runs "${RUNS}" "$@"
