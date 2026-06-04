#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

BASE_URL="${SWETRACE_HF_MIRROR:-https://hf-mirror.com}"
DATASET_ID="${SWETRACE_SWEBENCH_DATASET:-princeton-nlp/SWE-bench_Lite}"
OUT_DIR="${SWETRACE_SWEBENCH_CACHE:-/data/yiyuldx/swe/cache/swebench_lite}"

mkdir -p "${OUT_DIR}/data"

download_file() {
  local split_file="$1"
  local url="${BASE_URL}/datasets/${DATASET_ID}/resolve/main/data/${split_file}"
  local out="${OUT_DIR}/data/${split_file}"
  echo "Downloading ${url}"
  curl -L --fail --retry 3 --connect-timeout 15 --max-time 180 -o "${out}" "${url}"
  ls -lh "${out}"
}

download_file "dev-00000-of-00001.parquet"
download_file "test-00000-of-00001.parquet"

echo "SWE-bench Lite cached at ${OUT_DIR}"
