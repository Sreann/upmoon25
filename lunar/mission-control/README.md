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

**`lunar dashboard`** (from repo root, with ROS running) starts the UI plus `camera_ws` and `mission_bridge`, and proxies WebSockets on the same port as the page — no `.env.local` required. Use **Mock bridge** in the header only for UI rehearsal without ROS.

## Fake data and occupancy grid (no bridge)

```bash
cd lunar/mission-control
pnpm install
pnpm dev:demo
```

From the repo root you can use `make mission-control-demo` (Vite **5173**, `0.0.0.0`, fake snapshot only via `.env.demo`).

- Choose **Terrain lab** in the header scenario dropdown for a **256×256** fake `OccupancyGrid` at **5 cm** resolution (~12.8 m square), with **multi-pixel** canvas scaling so structure stays visible.
- `?mock=1` in the URL disables the mission WebSocket even if `.env.local` targets a bridge (handy on a tunnel where `:8770` is wrong).
- `?scenario=terrain_lab` (or `nominal` / `degraded` / `offline`) sets the initial scenario.

## Copy the dashboard tree for a second checkout

```bash
make mission-control-demo-copy
```

Copies `lunar/mission-control/` to `~/mission-control-demo` (excludes `node_modules`, `dist`, `.vite`). **Not automatic:** run again after you pull changes. Then `cd ~/mission-control-demo && pnpm install && pnpm dev:demo`.

## View on mobile over Tailscale

1. Log the laptop and phone into the **same** Tailscale tailnet.
2. Run `make mission-control-demo` (or `cd lunar/mission-control && pnpm dev:demo`). Vite is configured to listen on **0.0.0.0:5173** in dev.
3. On the laptop run `tailscale ip -4` and on the phone open `http://<that-ip>:5173`.

Optional HTTPS front door (MagicDNS URL printed by Tailscale):

```bash
tailscale serve --bg http://127.0.0.1:5173
```

Use `tailscale serve status` or `tailscale serve reset` to inspect or clear it.

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
- Switchable mock scenarios: nominal, degraded, offline, terrain lab (synthetic occupancy)
- Typed bridge contract under `src/bridge`

## Safety Boundary

This frontend must not become a generic ROS command console. Motion, actuator, restart, and tuning commands should go through a narrow robot-side bridge with allowlisted commands, command freshness checks, and watchdog stop behavior.

## Bridge Work

Read [docs/BRIDGE_CONTRACT.md](docs/BRIDGE_CONTRACT.md) before wiring live ROS data.

The dashboard defaults to **Live bridge** when `VITE_MISSION_WS_URL` resolves (same host, port `8770`). Use **Mock bridge** in the header for UI rehearsal without ROS. `lunar mission-bridge` streams ROS telemetry as `MissionControlSnapshot` and implements safety bar commands, short drive pulses, actuators, zone marking, and short-segment nav arming. Payload macros, bag recording, map save, and PID remain CLI-only (`lunar run`, `lunar keyboard`).

## Team Split

Read [docs/TEAM_LANES.md](docs/TEAM_LANES.md) before assigning work across teammates and agents.
