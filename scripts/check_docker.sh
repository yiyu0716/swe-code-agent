#!/usr/bin/env bash
set -euo pipefail

echo "Docker preflight"

if command -v docker >/dev/null 2>&1; then
  echo "docker binary: $(command -v docker)"
else
  echo "docker binary: missing"
  exit 10
fi

if [[ -S /var/run/docker.sock ]]; then
  echo "docker socket: present"
  ls -l /var/run/docker.sock
else
  echo "docker socket: missing"
  exit 11
fi

if docker version >/tmp/swetrace-docker-version.log 2>&1; then
  echo "docker daemon: reachable"
  cat /tmp/swetrace-docker-version.log
else
  echo "docker daemon: unreachable"
  cat /tmp/swetrace-docker-version.log
  exit 12
fi

IMAGE="${SWETRACE_DOCKER_TEST_IMAGE:-hello-world}"
echo "test image: ${IMAGE}"
docker run --rm "${IMAGE}" >/tmp/swetrace-docker-run.log 2>&1
cat /tmp/swetrace-docker-run.log
echo "docker preflight: ok"
