#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if command -v mini-extra >/dev/null 2>&1; then
  MINI_EXTRA="mini-extra"
elif command -v uvx >/dev/null 2>&1; then
  MINI_EXTRA="uvx --from mini-swe-agent --with socksio mini-extra"
else
  echo "Neither mini-extra nor uvx is available in this environment." >&2
  echo "Install mini-swe-agent or uv, then rerun this script." >&2
  exit 127
fi

INSTANCE_ID="${SWETRACE_MINI_INSTANCE:-django__django-11099}"
MODEL="${SWETRACE_MINI_MODEL:-gpt-4.1-mini}"
SUBSET="${SWETRACE_MINI_SUBSET:-lite}"
SPLIT="${SWETRACE_MINI_SPLIT:-dev}"
TIMEOUT_SECONDS="${SWETRACE_MINI_TIMEOUT_SECONDS:-1800}"
OUT="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"
PIP_INDEX_URL="${SWETRACE_MINI_PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
PIP_TRUSTED_HOST="${SWETRACE_MINI_PIP_TRUSTED_HOST:-pypi.tuna.tsinghua.edu.cn}"
HTTP_PROXY_VALUE="${HTTP_PROXY:-${http_proxy:-}}"
HTTPS_PROXY_VALUE="${HTTPS_PROXY:-${https_proxy:-}}"
SAFE_INSTANCE_ID="${INSTANCE_ID//[^A-Za-z0-9_.-]/-}"
TASK_FILE="${SWETRACE_MINI_TASK_FILE:-}"
ENV_CONFIGS=(
  "-c environment.env.PIP_INDEX_URL=${PIP_INDEX_URL}"
  "-c environment.env.PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}"
)
if [[ -n "${HTTP_PROXY_VALUE}" ]]; then
  ENV_CONFIGS+=(
    "-c environment.env.HTTP_PROXY=${HTTP_PROXY_VALUE}"
    "-c environment.env.http_proxy=${HTTP_PROXY_VALUE}"
  )
fi
if [[ -n "${HTTPS_PROXY_VALUE}" ]]; then
  ENV_CONFIGS+=(
    "-c environment.env.HTTPS_PROXY=${HTTPS_PROXY_VALUE}"
    "-c environment.env.https_proxy=${HTTPS_PROXY_VALUE}"
  )
fi
ENV_CONFIG_STRING="${ENV_CONFIGS[*]}"

if [[ -z "${TASK_FILE}" ]]; then
  TASK_FILE="$(mktemp "${TMPDIR:-/tmp}/swetrace-mini-task-${SAFE_INSTANCE_ID}.XXXXXX.json")"
  REPO="${INSTANCE_ID%%-*}"
  REPO="${REPO//__/\/}"
  cat > "${TASK_FILE}" <<EOF
{
  "task_id": "${INSTANCE_ID}",
  "source": "swebench_lite",
  "repo": "${REPO}",
  "base_commit": "unknown",
  "issue_text": "SWE-bench Lite instance ${INSTANCE_ID}. The real issue text is resolved by mini-SWE-agent from the benchmark instance id.",
  "test_command": "mini-swe-agent managed evaluation",
  "difficulty": "medium",
  "tags": ["swebench-lite", "real-agent-smoke"]
}
EOF
fi

if [[ -n "${SWETRACE_MINI_COMMAND_TEMPLATE:-}" ]]; then
  COMMAND_TEMPLATE="${SWETRACE_MINI_COMMAND_TEMPLATE}"
else
  COMMAND_TEMPLATE="${MINI_EXTRA} swebench-single --instance ${INSTANCE_ID} --subset ${SUBSET} --split ${SPLIT} --model ${MODEL} --output {traj_path} --yolo --exit-immediately -c swebench.yaml ${ENV_CONFIG_STRING}"
fi

PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
"${PYTHON}" -m swetrace.collect.run_task \
  --task "${TASK_FILE}" \
  --agent mini-swe-agent \
  --out "${OUT}" \
  --command-template "${COMMAND_TEMPLATE}" \
  --timeout-seconds "${TIMEOUT_SECONDS}"
