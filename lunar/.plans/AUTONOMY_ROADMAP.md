# Lunar Autonomy Roadmap

This is the primary roadmap for taking the current robot from manual/dashboard operation to supervised autonomous excavation. It should be treated as the reference plan during field work, implementation, and testing.

## Progress Ledger

Last updated: 2026-05-12

We can definitively mark progress on the operator dashboard and bridge foundation. We cannot yet mark autonomous navigation, SLAM, terrain avoidance, flag detection, or full dig/dump autonomy as complete because those still require real robot validation and implementation.

### Completed Or Substantially Implemented

- Initial roadmap and field plans written under `lunar/.plans`.
- Dense one-page React/Tailwind mission-control dashboard created under `lunar/mission-control`.
- Streamlit dashboard kept available as fallback through `lunar dashboard` / `make dashboard`.
- New dashboard launch paths added through `lunar mission-control` and `make mission-control`.
- Dashboard feature parity surface implemented with mock/live modes, mission overview, safety bar, cameras, terrain placeholder, zone marking, teleop, mining controls, hardware health, logs, diagnostics, PID panel, audit panel, fallback states, and mobile-friendly layout.
- Typed frontend bridge contract implemented in `lunar/mission-control/src/bridge/types.ts`.
- Live WebSocket client implemented for `MissionControlSnapshot` and command acknowledgements.
- Safe-command ROS bridge started as `lunar mission-bridge` / `make mission-bridge`.
- Mission bridge streams core telemetry snapshot data from ROS where available: camera topic status, depth point count, odom, command velocity echo, battery, CPU/RAM/temp, IR, encoders, and ROS warning/error logs.
- Mission bridge accepts only safety/context commands: ESTOP, pause, manual takeover, drive stop, and zone marking.
- Mission bridge rejects normal drive motion, payload macros, PID tuning, map save, recording, and autonomy resume until watchdog/subsystem contracts are tested.
- Camera frame path added for the new dashboard using the existing camera WebSocket bridge via `VITE_CAMERA_WS_BASE_URL`.
- Field readiness audit handout created.
- Relevant ROS/TanStack/dashboard skills collected under `lunar/skills`.
- Shadow-mode perception/autonomy ROS nodes added:
  - `backend perception_health`
  - `backend local_terrain_grid`
  - `backend flag_detector`
  - `backend autonomy_supervisor`
- `lunar autonomy-stack` / `make autonomy-stack` launch path added for the shadow stack.
- Mission bridge now consumes `/autonomy/state`, `/autonomy/terrain_status`, and `/perception/flag_candidates`.
- Mission bridge now consumes `/autonomy/local_terrain_grid` and forwards compact grid cells to the dashboard snapshot.
- Mission bridge publishes operator zone marks to `/autonomy/zone_mark`.
- Mission-control dashboard now renders live terrain grid cells when available, with mock fallback.
- Local terrain grid now has tunable presets:
  - `coarse`: 15 cm cells
  - `standard`: 10 cm cells
  - `fine`: 5 cm cells
- Offline synthetic tests added for terrain grid classification.
- `lunar autonomy-stack --grid-preset ...` and `make autonomy-stack grid=...` expose terrain resolution tuning.
- Offline unit tests added for:
  - Terrain grid presets and cell classification.
  - HSV red/orange flag detection on synthetic images.
  - Trusted keyboard clamping/direct-serial command behavior.
  - CLI subsystem parsing.
  - Mission bridge snapshot contract and terrain-grid forwarding.
- `make test-offline` added for hardware-free regression checks.

### In Progress

- Live dashboard-to-robot bridge validation.
- Camera stream status and frame display integration.
- Operator zone marking as the first field model.
- Topic health reporting for autonomy-critical signals.
- Safe stop command path through the new dashboard bridge.
- Shadow-mode perception readiness and autonomy supervisor validation.
- Local point-cloud-to-grid validation against real TF and D435 data.
- HSV red/orange flag detector field tuning.

### Not Completed Yet

- Confirming `/camera/depth/points` on the real robot.
- Confirming T265, wheel odometry, TF, and SLAM viability.
- Proving the live top-down terrain grid is spatially correct on hardware.
- Proving red/orange flag detection works in the Exolith lab.
- Implementing navigation toward marked or detected zones.
- Implementing payload/dig/dump macros in the new bridge.
- Implementing the mission state machine as a live autonomy controller.
- Implementing full robot-side motion watchdog for non-stop drive commands.
- Completing a supervised autonomous dig/dump cycle.

### Rough Roadmap Completion

- Mission-control dashboard surface: about 70% complete.
- Frontend/live bridge contract: about 60% complete.
- Safe command bridge foundation: about 35% complete.
- Field readiness documentation: about 80% complete.
- Perception, SLAM, planning, and autonomy execution: about 25% complete.
- End-to-end autonomous excavation: 0% complete until demonstrated on hardware.

## 1. Target End State

The ideal robot is a supervised autonomous excavation system. The operator is not continuously driving. The operator opens the dashboard, verifies system health, confirms or marks field zones, arms autonomy, and supervises repeated dig/dump cycles.

The robot should be able to:

- Understand its own hardware readiness.
- See the terrain around it.
- Identify unsafe terrain such as rocks, potholes, steep surfaces, and unknown regions.
- Maintain a usable estimate of where it is.
- Navigate between start, dig, and dump zones.
- Detect or confirm red/orange dump-zone flags.
- Execute repeatable timed dig and dump macros.
- Stop or request operator help when confidence is low.
- Provide a dashboard explanation of what it is doing and why.

The target architecture is layered, not monolithic:

1. Hardware drivers
2. Teleop and emergency stop
3. Sensor health
4. Perception
5. Local terrain map
6. Localization / SLAM
7. Planning and control
8. Mining macros
9. Mission state machine
10. Dashboard supervision

## 2. Current Starting Point

### Known Working

- The robot can be controlled through `lunar keyboard`.
- The CLI keyboard path publishes the same ROS topics autonomy should use.
- Sabertooth motor controllers are believed to work.
- Emergency stop is trusted.
- RGB camera feeds are working in the dashboard.
- Rear camera and actuator-mounted RGB camera are present.
- Manual digging works.
- Manual dumping works.
- Actuator controls through the CLI keyboard work.
- Operator marking is likely allowed.
- The team is comfortable using the web dashboard as the main operating surface.

### Unknown Or Weak

- Wheel encoder values currently do not make sense.
- `/camera/depth/points` has not been confirmed on the real robot.
- T265 status is unknown.
- Localization status is unknown.
- TF correctness is unknown.
- Point cloud alignment is unknown.
- `global_mapper` real-hardware usefulness is unknown.
- `path_planner` and `motion_controller` hardware usefulness is unknown.
- Nav2 usage status is unclear.
- Exolith lab dimensions and exact task layout are not yet known.
- Autonomy stack is mostly not implemented or not trusted.

### Main Constraints

- Competition performance matters.
- Timeline is short.
- Field environment is initially unknown.
- Terrain includes mixed rocks and potholes.
- Dump zone uses red/orange flags.
- Dig zone is likely defined relative to start/dump or field layout.

## 3. Core Strategy

The central strategy is progressive autonomy.

Do not wait for perfect SLAM, perfect planning, or perfect AI perception. Build a system that can become more autonomous as each layer becomes trustworthy.

The roadmap should always preserve a fallback:

- If SLAM works, use it.
- If SLAM is weak, use dashboard-marked zones plus local obstacle avoidance.
- If flag detection works, use it to confirm dump zone.
- If flag detection fails, allow operator marking.
- If point cloud works, use local traversability.
- If point cloud fails, stop or use manual fallback.
- If wheel odometry improves, fuse it later.

The robot should never blindly continue when the perception or localization layer is unhealthy.

## 4. Near-Term Architecture

### Existing Control Surface

Autonomy should command the same topics that manual controls already use:

- `cmd/velocity` for physical robot drive
- `/cmd/camera_height`
- `/cmd/pan`
- `/cmd/bucket_pos`
- `/cmd/bucket_vel`
- `/cmd/conveyor`

This means the CLI keyboard, dashboard, and autonomy can share the same interface.

### New Autonomy Layers

Add these concepts over time:

- `perception_health`: Reports camera/depth/TF freshness and validity.
- `local_terrain_grid`: Robot-relative top-down grid from depth points.
- `zone_detector`: Detects red/orange flags and candidate dump-zone bearings.
- `zone_manager`: Stores operator-marked or detected start/dig/dump zones.
- `mission_controller`: State machine for dig/dump cycles.
- `navigation_controller`: Drives toward a target while avoiding local hazards.

These do not all need to be separate ROS nodes immediately, but they should be separate concepts.

## 5. Dashboard End State

The dashboard should become mission control.

It should show:

- Robot health
- Emergency stop status
- Active ROS nodes
- Camera feeds
- Red/orange flag detections overlaid on RGB
- Point cloud health
- Top-down local terrain grid
- Global/local map if available
- Robot pose estimate and confidence
- Marked start/dig/dump zones
- Current mission state
- Current target
- Planned or chosen steering direction
- Mining actuator state
- Dig/dump macro state
- Recent logs and reason for stopping

It should allow:

- Start autonomy
- Pause autonomy
- Resume autonomy
- Abort autonomy
- Trigger emergency stop
- Mark start zone
- Mark dig zone
- Mark dump zone
- Clear/re-mark zones
- Run dig macro manually
- Run dump macro manually
- Switch between manual, assisted, and autonomous modes
- Start/stop rosbag recording for field data

Normal operation should not require RViz. However, RViz or Foxglove should remain available for developer debugging of TF, point clouds, and maps.

## 6. Perception Roadmap

### Phase 1: Prove Sensor Streams

Before advanced autonomy, confirm:

- Front RGB feed works.
- Rear RGB feed works.
- Depth point cloud publishes on `/camera/depth/points`.
- Point cloud message rate is usable.
- Point cloud frame is `depth_link_optical`.
- Camera/depth timestamps are fresh.
- TF exists between `depth_link_optical`, `base_link`, `odom`, and `map` where applicable.

Dashboard metrics:

- Last RGB frame age
- Last rear frame age
- Last point cloud age
- Point cloud Hz
- Point count
- Valid point ratio
- Depth min/median/max
- TF OK / not OK

### Phase 2: Top-Down Local Terrain Grid

Build a robot-relative 2D grid from the depth point cloud.

The grid should classify:

- Traversable ground
- Positive obstacles
- Pothole/drop risk
- Unknown cells
- Inflated unsafe region around obstacles

Initial implementation can be simple:

- Downsample point cloud.
- Transform points into `base_link`.
- Bin points into X/Y cells.
- Compute height statistics per cell.
- Mark large height discontinuities as obstacles.
- Mark suspicious low/missing regions as pothole risk.
- Inflate obstacles by robot radius plus margin.

Dashboard view:

- Robot footprint in center
- Forward direction
- Hazard cells
- Unknown cells
- Selected steering direction
- Target bearing if available

### Phase 3: Flag Detection

Start with classical red/orange detection:

- HSV threshold red/orange.
- Filter by area.
- Filter by shape/aspect ratio.
- Estimate image bearing from camera intrinsics.
- Optionally estimate distance from depth if available.
- Publish candidate confidence.

DINO/SAM can be explored as a secondary path, but should not be the only detector at first.

Reason for pushback:

- The target object is color-coded.
- HSV is fast, tunable, and inspectable.
- Field debugging is easier.
- DINO/SAM adds model dependency, latency, compute load, and failure opacity.

Reasonable compromise:

- Build HSV detector first.
- Record field data.
- Test DINO/SAM offline or as a parallel detector.
- Promote model-based detection only if it clearly beats HSV in field conditions.

### Phase 4: Perception Confidence

Every perception output should include confidence.

Examples:

- Flag confidence
- Terrain grid freshness
- Point cloud confidence
- TF confidence
- Localization confidence

Autonomy should use confidence to decide whether to continue, slow, stop, or ask for operator confirmation.

## 7. Localization And SLAM Roadmap

SLAM should be prioritized, but the mission should not depend entirely on solving SLAM immediately.

### Step 1: Audit Existing Pose Sources

Check:

- Is T265 installed?
- Does it publish `/odom`?
- Is `/odom` stable while stationary?
- Does pose drift badly during turns?
- Do wheel encoders publish?
- Can encoder signs and scaling be corrected?
- Does any current odometry match physical motion?

Dashboard metrics:

- Current pose source
- Pose freshness
- Odom velocity
- Drift while stationary
- Encoder values
- Localization confidence

### Step 2: Use Best Available Pose

Possible pose sources in priority order:

1. T265 visual-inertial odometry if stable.
2. Wheel odometry if fixed and validated.
3. Fused T265 + wheel odometry if time allows.
4. Relative dead-reckoned short moves if nothing else is trustworthy.
5. Operator-marked zones plus visual servoing as fallback.

### Step 3: SLAM Candidate Evaluation

Do not choose a SLAM system by preference. Choose by field test.

Evaluate:

- Existing `global_mapper`
- Nav2 costmaps
- RTAB-Map or another RGB-D SLAM approach if feasible
- Simple local mapping without global SLAM

Selection criteria:

- Works with available sensors.
- Runs on available compute.
- Produces stable pose/map in Exolith terrain.
- Is debuggable from dashboard/Foxglove.
- Can be integrated before the deadline.

### Step 4: Dashboard Marking Fallback

Because operator marking is likely allowed, implement it early.

Marking should support:

- Start zone
- Dump zone
- Dig zone
- Optional safe corridor or waypoint

Marked zones let the team test autonomy even before SLAM is perfect. They also give ground truth for validating SLAM later.

## 8. Navigation Roadmap

### Navigation Philosophy

Use short, conservative navigation segments.

Instead of commanding a long path and hoping localization is perfect:

1. Choose a target or bearing.
2. Check local terrain grid.
3. Move a short distance.
4. Stop or slow.
5. Reobserve.
6. Replan or steer.

This fits weak localization, uncertain terrain, and a short timeline.

### Local Obstacle Avoidance

Basic behavior:

- If forward corridor is clear, drive forward.
- If left is safer, bias left.
- If right is safer, bias right.
- If blocked everywhere, stop and rotate/search.
- If terrain confidence is low, slow or stop.
- If target confidence is low, search or ask for operator confirmation.

### Global Planning

If SLAM/global map becomes usable:

- Use marked/detected zones as goals.
- Use global obstacle map for route planning.
- Use local terrain grid as the final safety layer.

Even with global planning, local hazard avoidance must remain active.

## 9. Mining Roadmap

### Initial Mining Control

Use timed macros because no reliable bucket-full sensor exists yet.

Required macros:

- `dig_start`
- `dig_stop`
- `dump_start`
- `dump_stop`
- `stow`
- `abort_payload`

Each macro should command existing actuator topics.

### Dig Cycle

Initial timed dig sequence:

1. Position at dig site.
2. Lower bucket/actuator to configured position.
3. Start bucket chain/conveyor.
4. Drive forward slowly for configured duration or distance.
5. Stop drive.
6. Stop chain/conveyor.
7. Raise/stow bucket.
8. Mark payload as loaded.

### Dump Cycle

Initial timed dump sequence:

1. Position near dump zone.
2. Stop drive.
3. Set bucket/dump actuator.
4. Run conveyor or bucket chain as needed.
5. Wait configured duration.
6. Stop payload actuators.
7. Stow.
8. Mark payload as empty.

### Future Mining Improvements

Possible later upgrades:

- Motor current/load sensing.
- Bucket-full inference.
- Slip detection during digging.
- Adaptive dig duration.
- Terrain selection for better dig spots.

## 10. Mission State Machine

The robot should run a mission state machine, not scattered scripts.

Initial states:

1. `IDLE`
2. `HEALTH_CHECK`
3. `WAIT_FOR_ZONE_MARKS`
4. `DISCOVER_DUMP_ZONE`
5. `NAV_TO_DIG`
6. `DIG`
7. `NAV_TO_DUMP`
8. `DUMP`
9. `RETURN_TO_DIG`
10. `RECOVERY`
11. `PAUSED`
12. `ABORTED`
13. `ESTOP`

Every state should publish:

- State name
- Active target
- Current action
- Confidence
- Stop reason
- Time in state
- Last perception update

Transitions should be explicit.

Examples:

- `HEALTH_CHECK -> WAIT_FOR_ZONE_MARKS` if required sensors are healthy.
- `WAIT_FOR_ZONE_MARKS -> NAV_TO_DIG` if dig/dump zones are known.
- `NAV_TO_DIG -> RECOVERY` if blocked too long.
- `NAV_TO_DIG -> PAUSED` if localization confidence drops.
- `DIG -> NAV_TO_DUMP` when timed dig completes.
- `NAV_TO_DUMP -> DUMP` when within dump tolerance.
- Any state -> `ESTOP` on emergency stop.

## 11. Data And Testing Roadmap

### Rosbag Policy

Record often. The fastest way to improve perception and SLAM is field data.

Minimum topics:

- `/camera/rgb/image_compressed`
- `/camera/rear/image_compressed`
- `/camera/depth/points`
- `/odom`
- `/tf`
- `/tf_static`
- `cmd/velocity`
- `/cmd/*`
- `/sensor/encoder/left`
- `/sensor/encoder/right`
- `/rosout`
- Mission state topic once available

### Test Ladder

1. Bench test without driving.
2. Lifted-wheel drive command test.
3. Slow manual drive in open area.
4. Depth grid validation while stationary.
5. Depth grid validation while driving.
6. Flag detection stationary.
7. Flag detection while driving.
8. Operator-marked waypoint drive.
9. Short autonomous drive segment.
10. Dig macro stationary.
11. Dump macro stationary.
12. Full supervised dig/dump cycle.
13. Repeated cycles.

### Success Criteria

Each feature needs a pass/fail check.

Examples:

- Drive stop command halts robot within expected time.
- Point cloud Hz remains above threshold.
- Top-down obstacle appears in correct direction.
- Flag bearing changes correctly when camera pans.
- Robot can drive to marked point within tolerance.
- Robot stops when terrain grid is stale.
- Dig macro completes without manual intervention.
- Dump macro completes without manual intervention.

## 12. Immediate Priorities

### Priority 1: Confirm Reality

- Confirm `/camera/depth/points` on hardware.
- Confirm T265 or other `/odom` source.
- Confirm TF tree enough for depth-to-base projection.
- Confirm command topic reliability.
- Confirm dig/dump macro topic behavior.

### Priority 2: Dashboard Perception

- Add point cloud health.
- Add top-down local terrain grid.
- Add flag detection overlay or panel.
- Add marked zone UI.

### Priority 3: Assisted Autonomy

- Add mission state display.
- Add macro buttons.
- Add zone marking.
- Add short-segment navigation toward a marked target.
- Add obstacle stop/avoid behavior.

### Priority 4: SLAM Evaluation

- Test existing mapper.
- Test T265 stability.
- Test wheel encoder correction.
- Decide whether to integrate a SLAM package or use simpler local mapping for the competition.

### Priority 5: Full Cycle

- Navigate to dig zone.
- Dig.
- Navigate to dump zone.
- Dump.
- Repeat.
- Recover from blocked path or low-confidence perception.

## 13. What Not To Overbuild Yet

Avoid spending the first critical days on:

- Full 3D point cloud dashboard visualization.
- Complex neural perception before simple color segmentation baseline.
- Perfect global SLAM before local obstacle avoidance works.
- Fully custom planners before short-segment navigation works.
- Fancy UI polish before dashboard confidence and stop reasons exist.

These can come later, but they should not block the first reliable autonomous cycle.

## 14. Decision Points

### If Depth Point Cloud Works

Build top-down local terrain grid immediately.

### If Depth Point Cloud Does Not Work

Prioritize camera driver/hardware fix. Autonomy should remain manual or assisted until depth is available.

### If T265 Works

Use it as the first pose source and validate drift.

### If T265 Does Not Work

Use operator marking, visual servoing to flags, and short local moves while encoder work continues.

### If Wheel Encoders Become Reliable

Add wheel odometry and consider fusion with T265.

### If Flag Detection Is Easy

Use flags for dump-zone confirmation and visual servoing.

### If Flag Detection Is Hard

Use operator marking first and collect data for improved detection.

### If SLAM Works

Use SLAM pose/map for zone-to-zone navigation.

### If SLAM Is Weak

Use marked zones and local terrain avoidance for the competition path.

## 15. Final System Definition

The end-state robot is successful when it can:

1. Boot into a known healthy state.
2. Show all relevant perception and autonomy status on the dashboard.
3. Accept zone marks or discover/confirm zones.
4. Build a usable local traversability map.
5. Navigate safely in short autonomous segments.
6. Avoid rocks and potholes where possible.
7. Execute timed dig and dump macros.
8. Repeat dig/dump cycles.
9. Stop safely when confidence is low.
10. Let the operator understand and override every major decision.

This is the roadmap. When unsure what to build next, prefer the smallest feature that improves one of these capabilities while keeping the robot testable in the field.
