#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required."
  exit 1
fi

cd "${ROOT_DIR}"

echo "[ros2-smoke] building ros2-stack image..."
docker compose build ros2-stack

echo "[ros2-smoke] starting ros2-stack..."
docker compose up -d ros2-stack

echo "[ros2-smoke] validating container startup..."
sleep 3
docker compose ps ros2-stack
docker compose logs --tail=40 ros2-stack

container_id="$(docker compose ps -q ros2-stack)"
if [[ -z "${container_id}" ]]; then
  echo "[ros2-smoke] ros2-stack container not found."
  exit 1
fi

status="$(docker inspect -f '{{.State.Status}}' "${container_id}")"
if [[ "${status}" != "running" ]]; then
  echo "[ros2-smoke] ros2-stack is not running (status=${status})."
  exit 1
fi

echo "[ros2-smoke] complete."
