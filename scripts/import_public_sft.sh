#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${SWETRACE_PYTHON:-/home/yiyuldx/birdNet/.venv/bin/python}"
RAW="${SWETRACE_PUBLIC_SFT_RAW:-/data/yiyuldx/swe/public_datasets/raw/R2EGym-SFT-Trajectories/data/train-00000-of-00001.parquet}"
OUT="${SWETRACE_PUBLIC_SFT_OUT:-/data/yiyuldx/swe/outputs/datasets/public_sft_v0.1}"
EVAL_SET="${SWETRACE_EVAL_SET:-/data/yiyuldx/swe/eval_sets/qwen_baseline_v0}"
LOCAL_DATASET="${SWETRACE_LOCAL_DATASET:-/data/yiyuldx/swe/outputs/datasets/v0.2}"
SOURCE_NAME="${SWETRACE_PUBLIC_SFT_SOURCE:-R2E-Gym/R2EGym-SFT-Trajectories}"
VERSION="${SWETRACE_PUBLIC_SFT_VERSION:-public-sft-v0.1}"

ARGS=(
  --raw "${RAW}"
  --out "${OUT}"
  --eval-set "${EVAL_SET}"
  --local-dataset "${LOCAL_DATASET}"
  --source-name "${SOURCE_NAME}"
  --version "${VERSION}"
)

if [[ -n "${SWETRACE_PUBLIC_SFT_LIMIT:-}" ]]; then
  ARGS+=(--limit "${SWETRACE_PUBLIC_SFT_LIMIT}")
fi

"${PYTHON}" -m swetrace.data_builder.import_public_sft "${ARGS[@]}"
