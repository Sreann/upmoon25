# lunar

Unified CLI for this workspace (simulation, operator UIs, ROS helpers).

## Quick start

```bash
cd lunar
uv sync
uv pip install -e .

# Simulation + Foxglove (from repo root)
uv run lunar sim --world ../gz_worlds/arena1.world --port 8765
```

## Operator UIs

| Command | What it runs |
|---------|----------------|
| **`lunar dashboard`** | React **mission-control** (Vite dev server). Default **port 8501**, background by default. |
| **`lunar mission-control`** | Same app; explicit name. |
| **`lunar streamlit-dashboard`** | Legacy **Streamlit** Command Center + camera WebSocket helper (default port 8501 for Streamlit). |
| **`lunar mission-bridge`** | Safe WebSocket bridge for mission-control telemetry/commands. |

## ROS / robot helpers

- **`lunar check`** — Health / environment audit (replaces older `lunar doctor` references).
- **`lunar env`** / **`lunar shell-env`** — Config and exportable env.
- **`lunar topics`** — `ros2 topic list`.
- **`lunar act`** — Shortcuts for actuator / drive topics.
- **`lunar keyboard`** — Terminal teleop (Textual TUI on robot).
- **`lunar autonomy-stack`** — Shadow perception + terrain + flags + autonomy supervisor (no autonomous drive by default).
- **`lunar kill`** — Stop tracked background processes.

## Quality (from **repo root**)

```bash
make test    # lint + offline Python tests + mission-control eslint
make ci      # same + production Vite build
make tune-flags input=field_photos/in output=field_photos/out
```

Arena photos: drop images under `field_photos/in` (gitignored by default), run **`make tune-flags`**, review overlays and `field_photos/out/results.jsonl`.

## Dashboard teleop (Streamlit)

The Streamlit **Command Center** (`lunar streamlit-dashboard`) supports hold-to-drive, conveyor, bucket chain, camera pan/height, and E-stop with browser heartbeat + ROS-side watchdog.
