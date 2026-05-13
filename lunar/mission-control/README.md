# Lunar Mission Control

Dense one-page operator dashboard for the lunar excavation robot.

This is the replacement target for the Streamlit dashboard. The first pass is intentionally UI-first with mock telemetry so the team can agree on the operating surface before wiring the live ROS bridge.

## Commands

```bash
pnpm install
pnpm dev
pnpm build
pnpm lint
```

**Robot (Linux, no pnpm):** build on a dev machine (`pnpm build`), sync the repo with `make deploy` (it **does not** rsync `node_modules/`). On the robot, `lunar dashboard` serves `dist/` with Python when `pnpm` is missing.

From the repo root:

```bash
lunar mission-control
make mission-control
make mission-bridge
```

To connect the frontend to the live bridge, copy `.env.example` to `.env.local` and set:

```bash
VITE_MISSION_WS_URL=ws://ROBOT_OR_LAPTOP_IP:8770/mission/ws
VITE_CAMERA_WS_BASE_URL=ws://ROBOT_OR_LAPTOP_IP:8767
```

`VITE_MISSION_WS_URL` drives the typed mission snapshot and safe command acknowledgements. `VITE_CAMERA_WS_BASE_URL` reuses the existing camera frame WebSocket at `/camera/ws/rgb` and `/camera/ws/rear`.

## Current Scope

- Sticky safety / mission bar
- Mission state overview
- Camera panels
- Top-down local terrain placeholder
- Zone marking
- Manual teleop controls
- Mining macro controls
- Hardware health table
- Data/log controls
- Autonomy timeline
- Localization/SLAM status
- Advanced controls
- Switchable mock scenarios: nominal, degraded, offline
- Typed bridge contract under `src/bridge`

## Safety Boundary

This frontend must not become a generic ROS command console. Motion, actuator, restart, and tuning commands should go through a narrow robot-side bridge with allowlisted commands, command freshness checks, and watchdog stop behavior.

## Bridge Work

Read [docs/BRIDGE_CONTRACT.md](docs/BRIDGE_CONTRACT.md) before wiring live ROS data.

The frontend currently uses `MockRobotBridge` so UI work can continue without a robot. `lunar mission-bridge` is the first live bridge path: it streams ROS telemetry as the same `MissionControlSnapshot` shape and only accepts ESTOP, pause, manual takeover, drive stop, and zone marking. Forward/reverse/turn drive, payload, PID, map save, and autonomy resume remain rejected until the robot-side watchdog layer exists.

## Team Split

Read [docs/TEAM_LANES.md](docs/TEAM_LANES.md) before assigning work across teammates and agents.
