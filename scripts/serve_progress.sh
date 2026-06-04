#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${SWETRACE_PYTHON:-${ROOT_DIR}/.venv/bin/python}"
REPORT_DIR="${ROOT_DIR}/reports"
PORTS=(20037 20038 8888)

mkdir -p "${REPORT_DIR}"

if [[ ! -x "${PYTHON}" ]]; then
  echo "Python interpreter is not executable: ${PYTHON}" >&2
  echo "Set SWETRACE_PYTHON=/path/to/python and rerun this script." >&2
  exit 127
fi

for port in "${PORTS[@]}"; do
  pid_file="${REPORT_DIR}/progress-${port}.pid"
  log_file="${REPORT_DIR}/progress-${port}.log"

  if [[ -f "${pid_file}" ]]; then
    old_pid="$(cat "${pid_file}")"
    if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" 2>/dev/null; then
      continue
    fi
    rm -f "${pid_file}"
  fi

  if command -v lsof >/dev/null 2>&1; then
    existing_pid="$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
    if [[ -n "${existing_pid}" ]]; then
      echo "${existing_pid}" > "${pid_file}"
      continue
    fi
  fi

  setsid "${PYTHON}" -m http.server "${port}" --bind 0.0.0.0 -d "${REPORT_DIR}" \
    > "${log_file}" 2>&1 < /dev/null &
  echo "$!" > "${pid_file}"
done

HOST_IP="$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+\.' | grep -vE '^(127|169\.254|172\.17)\.' | head -n 1 || true)"
if [[ -z "${HOST_IP}" ]]; then
  HOST_IP="127.0.0.1"
fi

echo "Progress report servers:"
for port in "${PORTS[@]}"; do
  echo "  http://${HOST_IP}:${port}/"
done
