#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${SWETRACE_PYTHON:-/home/yiyuldx/birdNet/.venv/bin/python}"
SWEBENCH="${SWETRACE_EVAL_SWEBENCH:-/data/yiyuldx/swe/cache/swebench_lite/data/test-00000-of-00001.parquet}"
TRAINING_DATASET="${SWETRACE_TRAIN_DATASET:-/data/yiyuldx/swe/outputs/datasets/v0.2}"
OUT="${SWETRACE_EVAL_SET_OUT:-/data/yiyuldx/swe/eval_sets/qwen_baseline_v0}"
LIMIT="${SWETRACE_EVAL_SET_LIMIT:-20}"
SEED="${SWETRACE_EVAL_SET_SEED:-20260609}"
VERSION="${SWETRACE_EVAL_SET_VERSION:-qwen-baseline-v0}"

"${PYTHON}" -m swetrace.eval_sets.build_clean_swebench \
  --swebench "${SWEBENCH}" \
  --training-dataset "${TRAINING_DATASET}" \
  --out "${OUT}" \
  --limit "${LIMIT}" \
  --seed "${SEED}" \
  --version "${VERSION}"
