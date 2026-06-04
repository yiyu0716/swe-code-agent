#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if command -v mini-extra >/dev/null 2>&1; then
  MINI_EXTRA="mini-extra"
elif command -v uvx >/dev/null 2>&1; then
  MINI_EXTRA="uvx --from mini-swe-agent mini-extra"
else
  echo "Neither mini-extra nor uvx is available in this environment." >&2
  echo "Install mini-swe-agent or uv, then rerun this script." >&2
  exit 127
fi

INSTANCE_ID="${SWETRACE_MINI_INSTANCE:-django__django-11099}"
MODEL="${SWETRACE_MINI_MODEL:-gpt-4.1-mini}"
TASK_FILE="${SWETRACE_MINI_TASK_FILE:-examples/swebench_lite_task.json}"
COMMAND_TEMPLATE="${SWETRACE_MINI_COMMAND_TEMPLATE:-${MINI_EXTRA} swebench-single --instance ${INSTANCE_ID} --model ${MODEL} --output {traj_path} --exit-immediately}"

/root/swe/.venv/bin/python -m swetrace.collect.run_task \
  --task "${TASK_FILE}" \
  --agent mini-swe-agent \
  --out runs \
  --command-template "${COMMAND_TEMPLATE}"
