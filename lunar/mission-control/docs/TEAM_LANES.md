# Team Lanes

Use this to split mission-control work across humans and their agents.

## Lane 1: Frontend Shell

Owns:

- One-page dashboard layout
- Responsive/mobile behavior
- Empty/stale/error states
- Visual components
- Operator workflows

Allowed files:

- `src/App.tsx`
- future `src/components/*`
- `src/index.css`

Acceptance:

- `pnpm build` passes.
- Offline/degraded/nominal scenarios remain usable.
- ESTOP remains visible.

## Lane 2: Bridge Contract

Owns:

- Type definitions
- Snapshot schema
- Command schema
- WebSocket client/server protocol docs

Allowed files:

- `src/bridge/*`
- `docs/BRIDGE_CONTRACT.md`

Acceptance:

- Frontend can run against mock bridge.
- Live bridge can implement same types.
- No arbitrary ROS command console is exposed.

## Lane 3: Camera Streams

Owns:

- Front/rear/tracking stream display
- Reconnect states
- FPS/age indicators
- No-stream states

Acceptance:

- Missing camera is obvious.
- Stale camera is obvious.
- Camera stream work does not block other telemetry.

## Lane 4: Terrain Grid

Owns:

- Local grid data shape
- Top-down grid rendering
- Hazard legend
- Terrain freshness

Acceptance:

- Grid can render without full point cloud.
- Unknown, obstacle, pothole, traversable, and robot footprint states are distinct.

## Lane 5: ROS Bridge

Owns:

- ROS subscriptions
- Snapshot generation
- Command allowlist
- Hold-to-drive watchdogs
- Recording/map operations

Acceptance:

- Robot-side bridge rejects unsafe commands.
- Browser disconnect stops active motion.
- Topic health includes age/rate/status.

## Lane 6: Field Ops

Owns:

- Field readiness audit
- Rosbag recording
- Test notes
- Screenshot/video proof

Acceptance:

- Every claim is backed by data.
- Bags include camera/depth/odom/tf/commands/logs where available.

## Integration Rule

Small PRs only. Each PR should say:

- What lane it belongs to.
- What files changed.
- How it was tested.
- What is still mocked.
- Whether it can affect robot motion.
