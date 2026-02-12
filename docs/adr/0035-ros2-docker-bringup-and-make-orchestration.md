# 0035 ROS2 Docker Bringup and Make Orchestration

## Problem

Operators need a minimal, repeatable way to start the local stack, including an optional ROS2 workspace path, from a small set of commands on Windows-oriented setups. Existing commands covered API/web workflows, but ROS2 startup and one-terminal orchestration were not standardized.

## Non-goals

- Defining runtime behavior for specific ROS2 nodes or launch graphs.
- Replacing existing API/web development targets.
- Requiring tmux for all users.

## Public API

- `Makefile` exposes ROS2 stack targets:
  - `ros2-stack-build`
  - `ros2-stack-up`
  - `ros2-stack-up-detached`
  - `ros2-stack-down`
  - `ros2-stack-logs`
  - `ros2-smoke`
- `Makefile` exposes tmux bringup targets:
  - `bringup-up`
  - `bringup-attach`
  - `bringup-down`
- Docker Compose includes a `ros2-stack` service backed by `Dockerfile.ros2`.
- `ros2_ws/src/bringup/` provides operator scripts for multi-window startup.

## Invariants

- API/web Docker services remain unchanged and independently runnable.
- ROS2 workspace bootstrap is best-effort and idles safely when no ROS2 packages exist.
- pdoc docs publishing remains part of GitHub Pages deployment.

## Test plan

- Validate command surface:
  - `make help`
  - `make docs-pydoc`
- Validate ROS2 container wiring:
  - `make ros2-stack-build`
  - `make ros2-smoke`
- Validate bringup script shell syntax:
  - `bash -n ros2_ws/src/bringup/tmux_up.sh`
  - `bash -n ros2_ws/src/bringup/tmux_down.sh`
