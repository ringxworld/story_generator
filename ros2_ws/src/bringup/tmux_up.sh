#!/usr/bin/env bash
set -euo pipefail

SESSION_NAME="${ATITD_TMUX_SESSION:-story-gen-stack}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WEB_DIR="${ROOT_DIR}/web"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required for bringup. Install tmux (WSL/Git Bash) and retry."
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for bringup."
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required for bringup."
  exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required for bringup."
  exit 1
fi

cd "${ROOT_DIR}"

if [[ "${ATITD_SKIP_WEB_INSTALL:-0}" != "1" ]]; then
  echo "[bringup] Installing web dependencies..."
  npm --prefix "${WEB_DIR}" install
fi

if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
  echo "[bringup] Session '${SESSION_NAME}' already exists. Attaching..."
  tmux attach -t "${SESSION_NAME}"
  exit 0
fi

echo "[bringup] Starting tmux session '${SESSION_NAME}'..."

# Window 1: ROS2 stack in Docker
tmux new-session -d -s "${SESSION_NAME}" -n ros2 "cd '${ROOT_DIR}' && docker compose up ros2-stack"

# Window 2: API server
tmux new-window -t "${SESSION_NAME}" -n api "cd '${ROOT_DIR}' && uv run story-api"

# Window 3: dashboard
tmux new-window -t "${SESSION_NAME}" -n web "cd '${ROOT_DIR}' && npm run --prefix web dev"

# Window 4: quick logs
tmux new-window -t "${SESSION_NAME}" -n logs "cd '${ROOT_DIR}' && docker compose logs -f ros2-stack"

tmux set-option -t "${SESSION_NAME}" -g mouse on
tmux select-window -t "${SESSION_NAME}:ros2"

echo "[bringup] Session ready."
tmux attach -t "${SESSION_NAME}"
