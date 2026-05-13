# Next Tasks

This is the immediate implementation queue for pushing the mission-control app toward the robot end state.

## 1. Live Bridge Skeleton

- Done: create a robot-side bridge process with `lunar mission-bridge`.
- Done: serve `/healthz`.
- Done: serve `/mission/ws`.
- Done: send `MissionControlSnapshot` from live ROS topic callbacks where available.
- Next: validate the bridge on the robot and confirm topic names against real hardware.

## 2. Topic Health

Implement health for:

- Done: `/camera/rgb/image_compressed`
- Done: `/camera/rear/image_compressed`
- Done: `/camera/depth/points`
- Done: `/odom`
- Stubbed: `/tf`
- Done: `cmd/velocity`

For each topic:

- status
- age
- rate
- note
- safety-critical flag

## 3. Camera Streams

- Reuse or port the existing Streamlit camera websocket logic.
- Front stream first.
- Rear stream second.
- Tracking stream last.
- Keep no-stream and stale-stream states visible.

## 4. Command API

Implement only safe commands first:

- `estop`
- `manual_takeover`
- `drive stop`
- `recording start/stop`
- `mark_zone`

Current live bridge behavior: accept ESTOP, pause, manual takeover, drive stop, and zone marking. Reject normal drive motion, payload, PID, map save, recording, and autonomy resume until the robot-side watchdog and subsystem contracts are tested.

Delay:

- non-stop drive motion
- payload macros
- PID tuning
- node restarts

## 5. Local Terrain Grid

- Confirm `/camera/depth/points`.
- Done: add `backend local_terrain_grid` shadow node.
- Done: publish `/autonomy/local_terrain_grid` and `/autonomy/terrain_status`.
- Done: bridge `/autonomy/local_terrain_grid` into `MissionControlSnapshot.terrainGrid`.
- Done: dashboard renders live terrain grid cells when available, with mock fallback.
- Done: add terrain grid presets: `coarse` = 15 cm, `standard` = 10 cm, `fine` = 5 cm.
- Done: add offline synthetic tests for terrain grid classification.
- Done: expose preset launch through `lunar autonomy-stack --grid-preset ...` and `make autonomy-stack grid=...`.
- Done: add offline tests for flag detection, trusted keyboard clamping/direct-serial behavior, CLI subsystem parsing, and mission bridge snapshot contract.
- Done: add `make test-offline` for hardware-free regression checks.
- Next: validate TF from depth frame to `base_link` on real robot.
- Keep full point cloud out of the browser.

## 6. Shadow Autonomy Stack

- Done: add `backend perception_health`.
- Done: add `backend flag_detector`.
- Done: add `backend autonomy_supervisor` with autonomous motion disabled.
- Done: add `lunar autonomy-stack`.
- Next: tune flag thresholds in the lab.
- Next: make supervisor readiness visible in the dashboard's mission state.

## 7. Field Audit Integration

- Add a dashboard panel that mirrors `FIELD_READINESS_AUDIT.md`.
- Let the operator mark checks as pass/fail.
- Export session summary later.

## 8. Mobile Pass

- Validate on phone.
- Keep ESTOP visible.
- Make camera/teleop sections usable without horizontal scrolling.
- Tables can scroll horizontally lower on the page.

## Done Criteria For First Robot-Useful Version

- App opens from phone.
- Bridge connection state is accurate.
- Front/rear camera state is accurate.
- Stop/ESTOP controls are visible.
- Topic health is live.
- Recording can start/stop.
- Zone marks can be captured.
- No live motion command exists without robot-side watchdog.
