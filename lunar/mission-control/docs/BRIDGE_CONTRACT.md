# Mission Control Bridge Contract

This document defines the boundary between the mission-control frontend and the robot-side ROS bridge.

The frontend must not publish arbitrary ROS messages. It should receive a compact mission snapshot and send a small set of allowlisted commands.

## Goals

- Keep robot safety logic out of the browser.
- Let frontend and ROS work proceed in parallel.
- Make stale/missing data explicit.
- Give every operator command an acknowledgement.
- Prevent generic ROS command access from the dashboard.

## Transport

Recommended first transport:

- WebSocket for telemetry snapshots and command acknowledgements.
- HTTP only for simple health checks or static metadata.

Suggested endpoints:

```text
GET  /healthz
GET  /metadata
WS   /mission/ws
```

The bridge should run near the robot/ROS graph and enforce safety rules server-side.

Current implementation:

```bash
lunar mission-bridge --foreground
```

This starts the first safe-command bridge at `ws://0.0.0.0:8770/mission/ws`. It streams the snapshot contract and accepts only ESTOP, pause, manual takeover, drive stop, and zone marking. It rejects normal drive motion, payload, PID, map save, and autonomy resume until the command watchdog layer exists.

## Snapshot Message

The bridge should periodically send a `MissionControlSnapshot` matching `src/bridge/types.ts`.

Minimum useful frequency:

- Mission/health snapshot: 5-10 Hz
- Camera frames: separate camera WebSocket or MJPEG stream
- Terrain grid: 5-10 Hz

The snapshot should include:

- Mission state
- Command metrics
- Topic health
- Camera stream status
- Hardware status
- Zone marks
- Recent logs
- Localization/SLAM status

Every live signal should include either:

- last update age
- message rate
- status
- confidence

Unknown must not be represented as healthy.

## Command Message

Frontend commands should match `RobotCommand` in `src/bridge/types.ts`.

Allowed command families:

- `estop`
- `pause_autonomy`
- `resume_autonomy`
- `manual_takeover`
- `drive`
- `payload`
- `mark_zone`
- `recording`
- `save_map`

The bridge should reject unknown commands.

## Command Acknowledgement

Every command gets a result:

```json
{
  "accepted": true,
  "message": "Drive command accepted for hold heartbeat",
  "commandId": "uuid"
}
```

Rejections should be explicit:

```json
{
  "accepted": false,
  "message": "Rejected: /odom is stale and autonomy is not allowed"
}
```

## Safety Requirements

The bridge must enforce:

- ESTOP always accepted.
- Motion commands are disabled when bridge state is unsafe.
- Drive commands require a hold heartbeat.
- Drive commands time out robot-side.
- Speed limits are clamped robot-side.
- Autonomy cannot start with stale safety-critical topics.
- Payload commands are rejected if hardware health is bad.
- Restart/tuning commands require confirmation.
- Browser disconnect stops active hold commands.

The browser can make requests, but the bridge decides whether a command is safe.

## Camera Streams

Do not send raw ROS image messages through the general mission snapshot.

Use separate streams:

```text
WS /camera/ws/front
WS /camera/ws/rear
WS /camera/ws/tracking
```

or:

```text
GET /camera/front/stream.mjpg
GET /camera/rear/stream.mjpg
```

The mission snapshot should only include camera stream status:

- live
- connecting
- stale
- missing
- unknown

## Terrain Grid

The bridge should not send full point clouds to the frontend for normal operation.

Preferred payload:

- small local grid
- cell status values
- resolution
- robot footprint
- target bearing
- selected steering direction
- timestamp/age

The full point cloud can remain a Foxglove/RViz debug tool.

## Topic Health

At minimum, expose health for:

- `/camera/rgb/image_compressed`
- `/camera/rear/image_compressed`
- `/camera/depth/points`
- `/odom`
- `/tf`
- `/tf_static`
- `cmd/velocity`
- `/cmd/camera_height`
- `/cmd/pan`
- `/cmd/bucket_pos`
- `/cmd/bucket_vel`
- `/cmd/conveyor`
- `/rosout`

Safety-critical topics should be flagged.

## First Implementation Scope

The first robot bridge should implement:

1. Snapshot heartbeat. Done in mission bridge.
2. Topic health. Done for core camera/depth/odom/cmd topics.
3. Camera stream status. Done as status only; frame streaming remains separate.
4. Recent logs. Done from `/rosout` warnings/errors.
5. ESTOP/manual stop command path. Done for ESTOP, pause, manual takeover, and drive stop.
6. Zone marking. Done as operator marks at current odom estimate.
7. Hold-to-drive command path with timeout.
8. Recording start/stop.

Defer:

- Full autonomy commands.
- SLAM map editing.
- PID tuning.
- Node restarts.

## Frontend Development Mode

The frontend includes `MockRobotBridge` with scenarios:

- `nominal`
- `degraded`
- `offline`
- `terrain_lab` (large synthetic local terrain cells for UI validation)

Use these scenarios to develop fallback states before the live bridge exists.
