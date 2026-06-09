#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${SWETRACE_PYTHON:-/home/yiyuldx/birdNet/.venv/bin/python}"
PUBLIC_DATASET="${SWETRACE_PUBLIC_SFT_DATASET:-/data/yiyuldx/swe/outputs/datasets/public_sft_v0.1}"
LOCAL_DATASET="${SWETRACE_LOCAL_DATASET:-/data/yiyuldx/swe/outputs/datasets/v0.2}"
OUT="${SWETRACE_SFT_MIX_OUT:-/data/yiyuldx/swe/outputs/datasets/sft_mix_v0.1}"
VERSION="${SWETRACE_SFT_MIX_VERSION:-sft-mix-v0.1}"

"${PYTHON}" -m swetrace.data_builder.build_training_mix \
  --public-dataset "${PUBLIC_DATASET}" \
  --local-dataset "${LOCAL_DATASET}" \
  --out "${OUT}" \
  --version "${VERSION}"
