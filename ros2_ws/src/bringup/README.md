# bringup

Convenience scripts for one-terminal stack startup with `tmux`.

## Scripts

- `ros2_ws/src/bringup/tmux_up.sh`: starts a tmux session with windows for:
  - ROS2 stack in Docker (`docker compose up ros2-stack`)
  - API server (`uv run story-api`)
  - dashboard dev process (`npm run --prefix web dev`)
  - ROS2 Docker logs
- `ros2_ws/src/bringup/tmux_down.sh`: stops the tmux session and stops `ros2-stack` container.

## Usage

```bash
make bringup-up
```

Stop everything:

```bash
make bringup-down
```

Attach to an existing session:

```bash
make bringup-attach
```

Set a custom session name:

```bash
TMUX_SESSION=my-stack make bringup-up
```
