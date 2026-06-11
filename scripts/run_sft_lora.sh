#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export USE_TF="${USE_TF:-0}"
export USE_FLAX="${USE_FLAX:-0}"
export TRANSFORMERS_NO_TF="${TRANSFORMERS_NO_TF:-1}"
export TRANSFORMERS_NO_FLAX="${TRANSFORMERS_NO_FLAX:-1}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HF_HOME="${HF_HOME:-/data/yiyuldx/swe/hf_cache}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-/data/yiyuldx/swe/hf_cache/hub}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/data/yiyuldx/swe/hf_cache/transformers}"

PYTHON="${SWETRACE_PYTHON:-/home/yiyuldx/birdNet/.venv/bin/python}"
DATASET="${SWETRACE_SFT_DATASET:-/data/yiyuldx/swe/outputs/datasets/sft_mix_v0.1}"
MODEL="${SWETRACE_MODEL:-/data/yiyuldx/swe/models/Qwen2.5-Coder-7B-Instruct}"
OUT="${SWETRACE_TRAIN_OUT:-/data/yiyuldx/swe/outputs/training}"
RUN_ID="${SWETRACE_TRAIN_RUN_ID:-sft-lora-$(date -u +%Y%m%dT%H%M%SZ)}"
MAX_STEPS="${SWETRACE_MAX_STEPS:-50}"
MAX_TRAIN_SAMPLES="${SWETRACE_MAX_TRAIN_SAMPLES:-}"
MAX_SEQ_LENGTH="${SWETRACE_MAX_SEQ_LENGTH:-1024}"
LEARNING_RATE="${SWETRACE_LEARNING_RATE:-0.0002}"
BATCH_SIZE="${SWETRACE_BATCH_SIZE:-1}"
GRAD_ACCUM="${SWETRACE_GRAD_ACCUM:-8}"
LORA_R="${SWETRACE_LORA_R:-16}"
LORA_ALPHA="${SWETRACE_LORA_ALPHA:-32}"
LORA_DROPOUT="${SWETRACE_LORA_DROPOUT:-0.05}"
DRY_RUN="${SWETRACE_DRY_RUN:-0}"

args=(
  -m swetrace.training.sft_lora
  --dataset "${DATASET}"
  --model "${MODEL}"
  --out "${OUT}"
  --run-id "${RUN_ID}"
  --max-steps "${MAX_STEPS}"
  --max-seq-length "${MAX_SEQ_LENGTH}"
  --learning-rate "${LEARNING_RATE}"
  --per-device-train-batch-size "${BATCH_SIZE}"
  --gradient-accumulation-steps "${GRAD_ACCUM}"
  --lora-r "${LORA_R}"
  --lora-alpha "${LORA_ALPHA}"
  --lora-dropout "${LORA_DROPOUT}"
)

if [[ -n "${MAX_TRAIN_SAMPLES}" ]]; then
  args+=(--max-train-samples "${MAX_TRAIN_SAMPLES}")
fi
if [[ "${DRY_RUN}" == "1" || "${DRY_RUN}" == "true" ]]; then
  args+=(--dry-run)
fi

"${PYTHON}" "${args[@]}"
