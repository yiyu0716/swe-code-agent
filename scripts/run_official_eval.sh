#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${SWETRACE_PYTHON:-/home/yiyuldx/birdNet/.venv/bin/python}"
OFFICIAL_ROOT="${SWETRACE_OFFICIAL_EVAL_ROOT:-/data/yiyuldx/swe/official_eval}"
DATASET_JSON="${SWETRACE_OFFICIAL_DATASET_JSON:-/data/yiyuldx/swe/cache/swebench_lite/swebench_lite_dev_test.json}"
PREDICTIONS="${SWETRACE_OFFICIAL_PREDICTIONS:?Set SWETRACE_OFFICIAL_PREDICTIONS to a predictions JSONL shard.}"
RUN_ID="${SWETRACE_OFFICIAL_RUN_ID:-swetrace_official_$(date -u +%Y%m%dT%H%M%SZ)}"
INSTANCE_TAG="${SWETRACE_OFFICIAL_INSTANCE_TAG:-pip-proxy}"
MAX_WORKERS="${SWETRACE_OFFICIAL_MAX_WORKERS:-1}"
TIMEOUT="${SWETRACE_OFFICIAL_TIMEOUT_SECONDS:-1800}"
INSTANCE_IDS="${SWETRACE_OFFICIAL_INSTANCE_IDS:-}"

mkdir -p "${OFFICIAL_ROOT}" /data/yiyuldx/swe/hf_cache /data/yiyuldx/swe/hf_datasets /data/yiyuldx/swe/tmp

args=(
  -d "${DATASET_JSON}"
  -s test
  -p "${PREDICTIONS}"
  --max_workers "${MAX_WORKERS}"
  --timeout "${TIMEOUT}"
  --cache_level instance
  --clean False
  -id "${RUN_ID}"
  --instance_image_tag "${INSTANCE_TAG}"
  --report_dir "${OFFICIAL_ROOT}/reports/${RUN_ID}"
)

if [[ -n "${INSTANCE_IDS}" ]]; then
  # shellcheck disable=SC2206
  ids=(${INSTANCE_IDS})
  args=(-i "${ids[@]}" "${args[@]}")
fi

cd "${OFFICIAL_ROOT}"
HF_HOME=/data/yiyuldx/swe/hf_cache \
HF_DATASETS_CACHE=/data/yiyuldx/swe/hf_datasets \
TMPDIR=/data/yiyuldx/swe/tmp \
"${PYTHON}" -m swebench.harness.run_evaluation "${args[@]}"
