#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
/root/swe/.venv/bin/python -m swetrace.labeling.auto_label_runs --runs runs
