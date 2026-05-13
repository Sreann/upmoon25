# Operator Handoff

This app is currently safe to open because it uses mock data by default.

## Run

From the repo root:

```bash
make mission-control
```

Or:

```bash
cd lunar/mission-control
pnpm dev --host 0.0.0.0
```

Open the printed URL from a laptop or phone on the same network.

## Demo Modes

Use the top bar selector:

- `Nominal`: shows what a healthy robot session should look like.
- `Degraded`: shows partial data and field-audit warnings.
- `Offline`: shows disconnected behavior and disabled controls.

The UI should remain readable and safe in all three modes.

## Live Bridge Mode

Live mode is disabled unless `VITE_MISSION_WS_URL` is set.

Example:

```bash
VITE_MISSION_WS_URL=ws://robot.local:8787/mission/ws pnpm dev --host 0.0.0.0
```

Until the robot-side bridge exists, stay in mock mode.

## Safety Expectation

- ESTOP must remain visible.
- Missing/stale data must be obvious.
- Motion controls must be disabled when the bridge is offline.
- Any future live motion command must be enforced by a robot-side watchdog.

## What Is Still Mocked

- All telemetry
- All camera feeds
- Topic health
- Hardware status
- Zone marks
- Command acknowledgements
- Terrain grid
- Logs

The current app is the operating surface and integration contract, not a live robot dashboard yet.
