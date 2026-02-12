#!/usr/bin/env bash
set -euo pipefail

SESSION_NAME="${ATITD_TMUX_SESSION:-story-gen-stack}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

cd "${ROOT_DIR}"

docker compose stop ros2-stack >/dev/null 2>&1 || true

if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
  tmux kill-session -t "${SESSION_NAME}"
  echo "[bringup] Stopped tmux session '${SESSION_NAME}'."
else
  echo "[bringup] No tmux session named '${SESSION_NAME}' found."
fi
