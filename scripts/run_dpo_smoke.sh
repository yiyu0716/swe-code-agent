#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${SWETRACE_PYTHON:-/home/yiyuldx/birdNet/.venv/bin/python}"
DATASET="${SWETRACE_TRAIN_DATASET:-/data/yiyuldx/swe/outputs/datasets/v0.2}"
MODEL="${SWETRACE_MODEL:-/data/yiyuldx/swe/models/Qwen2.5-Coder-7B-Instruct}"
OUT="${SWETRACE_TRAINING_OUT:-/data/yiyuldx/swe/outputs/training}"
RUN_ID="${SWETRACE_TRAIN_RUN_ID:-dpo-smoke-$(date -u +%Y%m%dT%H%M%SZ)}"
MAX_STEPS="${SWETRACE_MAX_STEPS:-3}"

"${PYTHON}" -m swetrace.training.smoke dpo \
  --dataset "${DATASET}" \
  --model "${MODEL}" \
  --out "${OUT}" \
  --run-id "${RUN_ID}" \
  --max-steps "${MAX_STEPS}"
