#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/app"
WS_DIR="${ROOT_DIR}/ros2_ws"
SRC_DIR="${WS_DIR}/src"

set +u
source /opt/ros/humble/setup.bash
set -u

if [[ ! -d "${SRC_DIR}" ]]; then
  echo "[ros2-stack] Missing workspace src directory at ${SRC_DIR}."
  exec tail -f /dev/null
fi

if ! find "${SRC_DIR}" -mindepth 2 -maxdepth 4 -name package.xml | read -r; then
  echo "[ros2-stack] No ROS2 packages found under ${SRC_DIR}. Container will stay idle."
  exec tail -f /dev/null
fi

cd "${WS_DIR}"
echo "[ros2-stack] Building workspace..."
colcon build --symlink-install

if [[ -f "${WS_DIR}/install/setup.bash" ]]; then
  # shellcheck disable=SC1091
  set +u
  source "${WS_DIR}/install/setup.bash"
  set -u
fi

echo "[ros2-stack] Workspace ready."
if [[ -n "${ATITD_ROS2_LAUNCH_COMMAND:-}" ]]; then
  echo "[ros2-stack] Running launch command: ${ATITD_ROS2_LAUNCH_COMMAND}"
  exec bash -lc "${ATITD_ROS2_LAUNCH_COMMAND}"
fi

echo "[ros2-stack] No launch command configured. Set ATITD_ROS2_LAUNCH_COMMAND to auto-start nodes."
exec tail -f /dev/null
