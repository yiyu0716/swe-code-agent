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
SAFE_INSTANCE_ID="${INSTANCE_ID//[^A-Za-z0-9_.-]/-}"
TASK_FILE="${SWETRACE_MINI_TASK_FILE:-}"

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
  COMMAND_TEMPLATE="${MINI_EXTRA} swebench-single --instance ${INSTANCE_ID} --subset ${SUBSET} --split ${SPLIT} --model ${MODEL} --output {traj_path} --yolo --exit-immediately"
fi

PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
"${PYTHON}" -m swetrace.collect.run_task \
  --task "${TASK_FILE}" \
  --agent mini-swe-agent \
  --out runs \
  --command-template "${COMMAND_TEMPLATE}" \
  --timeout-seconds "${TIMEOUT_SECONDS}"
