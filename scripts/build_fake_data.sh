#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
/root/swe/.venv/bin/python -m swetrace.data_builder.build_from_runs \
  --runs runs \
  --out outputs/datasets
