#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-/home/yiyuldx/birdNet/.venv/bin/python}"
RUNS="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"
OUT="${SWETRACE_OFFICIAL_V02_DATASET:-/data/yiyuldx/swe/outputs/datasets/v0.2}"
VERSION="${SWETRACE_OFFICIAL_V02_VERSION:-v0.2-official-$(date -u +%Y%m%d)}"

"${PYTHON}" -m swetrace.data_builder.export_official_v02 \
  --runs "${RUNS}" \
  --out "${OUT}" \
  --version "${VERSION}"
