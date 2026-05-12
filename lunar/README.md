# lunar

Unified cli for this project.

## Quick start

```bash
uv venv
uv pip install -e .

# run sim + web bridge
lunar sim --world ../gz_worlds/arena1.world --port 8765
```

## Commands

- `lunar sim` - start Gazebo sim + Foxglove bridge
- `lunar doctor` - quick environment checks
- `lunar env` - show effective config + ROS env
- `lunar topics` - run `ros2 topic list`
- `lunar act` - send focused robot actuator commands without full `ros2 topic pub` syntax
- `lunar kill` - stop processes started by `lunar sim`
- `lunar config` - show or set config values

## Dashboard Teleop

The Streamlit dashboard `Command Center` now exposes robot teleop controls for:

- drive velocity with press-and-hold buttons
- conveyor toggle
- bucket chain forward and reverse with press-and-hold buttons
- bucket position
- camera height
- camera pan with press-and-hold buttons
- emergency stop

Drive, pan, and bucket-chain hold controls use a browser heartbeat plus a ROS-side watchdog so commands stop if the page loses focus or the connection drops.
