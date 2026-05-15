# Operator Handoff

The dashboard defaults to **Live bridge** when port `8770` is reachable on the same host. Use **Mock bridge** in the header for UI rehearsal without ROS.

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

Live mode auto-resolves to `ws://<host>:8770/mission/ws` unless `VITE_MISSION_WS_DISABLE=1` or `?mock=1`. Override with `VITE_MISSION_WS_URL` if needed.

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
