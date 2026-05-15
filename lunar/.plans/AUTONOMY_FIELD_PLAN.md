# Lunar Autonomy Field Plan

This document captures the current situation and a practical autonomy plan for the Exolith field task.

## Progress Update

Last updated: 2026-05-13

**Canonical stack decisions, Nav2 definition, and the full cross-team focus checklist live in `AUTONOMY_ROADMAP.md`** (*Authoritative planning decisions* and *Focus areas checklist*). This field plan stays tactical; do not fork competing stack guidance here.

We have made concrete progress on the field-operations layer: the team now has a planned mission-control surface, a working dashboard app scaffold, live bridge contracts, fallback states, and a first safe-command bridge path. This does not mean autonomy is complete. It means the robot now has a clearer operator/control architecture to support autonomy work.

Completed or substantially implemented:

- Mission-control app scaffold and dense dashboard surface.
- Mock telemetry and degraded/offline fallback states.
- Safe dashboard command acknowledgements.
- Live bridge skeleton for ROS telemetry.
- Safe stop/manual takeover/zone-mark command path.
- Camera WebSocket integration path.
- Field readiness audit document.
- Roadmap and team work split documents.
- Shadow-mode perception health node.
- Shadow-mode local terrain grid node.
- HSV red/orange flag detector baseline.
- Shadow-mode autonomy supervisor.
- Single launcher for those nodes through `lunar autonomy-stack`.
- Global occupancy **software** alignment (`occupancy_grid_codec`, mapper/costmap/planner message layout); hardware still unproven.
- **Navigation controller v1** in repo: local-grid corridor follower, `/autonomy/navigation_twist` + status topics; supervisor `READY` + optional twist forwarding (see `AUTONOMY_ROADMAP` ledger).

Still field-critical and unproven:

- Depth point cloud on real hardware.
- TF correctness.
- Localization/SLAM source.
- Point-cloud terrain grid correctness.
- Flag detection reliability in field lighting.
- Autonomous navigation.
- Dig/dump macros through the new bridge.
- Full supervised dig/dump cycle.

## Goal

Build toward competition-grade autonomy for a lunar excavation robot operating in an unknown Exolith lab terrain. The robot starts in a start zone, must navigate to a dig area, perform timed dig cycles, navigate to a dump zone marked by red/orange flags, dump, and repeat while avoiding rocks and potholes where possible.

The near-term goal is not full autonomy from the first test. The goal is to build a reliable ladder:

1. Manual operation through the same ROS topics autonomy will use.
2. Dashboard observability for perception, localization, and actuation.
3. Assisted autonomy with operator-supervised zone discovery.
4. Repeatable autonomous dig and dump cycles.
5. More independent discovery and recovery behavior as reliability improves.

## Current Status From Team Discussion

### Working Or Believed Working

- Robot can be controlled through the `lunar keyboard` CLI.
- Sabertooth motor controllers are present and believed to work.
- Emergency stop path is trusted.
- RGB camera feeds used by the dashboard are working.
- Rear RGB camera and actuator-mounted RGB camera are present.
- Manual digging works.
- Manual dumping works.
- CLI keyboard controls for actuators work.
- Mining is likely time-based rather than bucket-fill-sensor-based.
- Red/orange flags mark relevant zones.

### Unknown Or Unproven

- Whether `/cmd/velocity` is fully reliable under all field conditions.
- Whether wheel encoder values are usable; current values do not make sense.
- Whether the D435 depth camera publishes `/camera/depth/points` on hardware.
- Whether the T265 is installed, publishing, or useful.
- Whether localization is currently available.
- Whether TF between camera, robot, odom, and map frames is correct.
- Whether point clouds align correctly with the robot.
- Whether `global_mapper` has ever produced a useful map from real hardware.
- Whether `path_planner` and `motion_controller` work beyond simulation (**lab/sim path**; not the competition critical path until local-first navigation is proven—see roadmap).
- **Nav2 is not in scope this cycle** (standard ROS 2 nav stack; deferred per `AUTONOMY_ROADMAP.md`). The committed runtime path is **custom nodes on existing drive/actuator topics**.
- Field dimensions and exact zone layout are not known yet.
- Whether competition rules allow operator initialization, teleop marking, AprilTags, or other fiducials needs confirmation.

### Main Risk Areas

- Mapping
- Localization
- Planning
- Terrain interpretation from depth
- Competition timeline: now to Wednesday

## Keyboard Vs Joystick

The current `lunar keyboard` path is acceptable for bring-up because it publishes the same ROS topics the autonomous stack should use:

- `cmd/velocity` for drive
- `/cmd/camera_height`
- `/cmd/pan`
- `/cmd/bucket_pos`
- `/cmd/bucket_vel`
- `/cmd/conveyor`

The newer keyboard TUI also has stop/watchdog behavior for drive and transient actuators. This makes it useful for repeatable testing and for validating the command interface.

Joystick is still better for fast human teleoperation because analog control is smoother and easier under stress. But for autonomy development, keyboard/dashboard controls are not a dead end. They exercise the same topic-level control surface that a mission controller should use.

Recommendation:

- Keep `lunar keyboard` as the primary bring-up and debug interface.
- Use joystick only if the team needs smoother human driving during field testing.
- Do not build autonomy around joystick-specific behavior.

## Architecture Direction

The robot should not try to solve everything with one large AI model. The safer architecture is layered:

1. Low-level control: existing motor and actuator topics.
2. Perception health: camera stream, depth stream, point count, TF validity.
3. Local terrain grid: top-down obstacle and pothole estimate from depth.
4. Zone detection: red/orange flag detection from RGB.
5. Localization: best available pose estimate, initially simple and conservative.
6. Planner: avoid known local hazards and move toward target zones.
7. Mission state machine: search, navigate, dig, return, dump, repeat, abort.

The dashboard should expose each layer so failures are visible.

### Authoritative alignment (do not contradict)

Match `AUTONOMY_ROADMAP.md` **Authoritative planning decisions**:

- **Ship** local terrain grid + short segments + supervisor gates before betting on global SLAM or long paths.
- **`autonomy_supervisor`**: readiness and `/autonomy/state`; add **`navigation_controller`** behavior and mission FSM as explicit next layers.
- **Nav2**: out of scope until after a supervised autonomous dig/dump works without it and time is allocated for integration.

## Perception Plan

### Depth / Terrain

First prove whether `/camera/depth/points` exists on the real robot. If it does, use it to create a top-down local terrain panel in the dashboard.

The panel should show:

- Point cloud message age
- Point cloud Hz
- Valid point ratio
- Nearest obstacle distance
- TF status from `depth_link_optical` to `base_link`
- A robot-relative 2D grid showing rocks and potholes

Do not prioritize a 3D viewer. A local top-down grid is better for driving and autonomy.

The terrain logic should classify:

- Positive obstacles: rocks, walls, field edges, piles
- Negative obstacles: potholes or drop-offs
- Unknown cells: no reliable depth
- Traversable cells: recently observed safe ground

For Wednesday, this can be simple:

- Downsample the point cloud.
- Transform into robot/base frame.
- Build a local X/Y grid.
- Mark cells with high height discontinuity as obstacles.
- Mark cells with missing/depressed depth patterns as pothole risk.
- Inflate hazards around the robot footprint.

### RGB / Flags

Start with classical color segmentation before DINOv3 or SAM-style models.

Reason:

- The target is red/orange flags, which is a color-based object.
- Classical HSV thresholding is faster, easier to debug, and runs locally.
- It is easier to tune at the field with dashboard sliders or config values.
- The timeline is short.

Suggested ladder:

1. HSV threshold red/orange regions.
2. Filter by size, shape, and vertical flag-like geometry.
3. Estimate bearing from image center and camera intrinsics.
4. Use depth or approximate distance if available.
5. Publish detected flag candidates as dashboard overlays and ROS messages.

Use DINO/SAM only if:

- Color segmentation fails under field lighting.
- There is enough compute and time.
- A fallback classical detector remains available.

Best practice is not "AI first." It is measurable perception first, with a model only where it clearly beats simple methods.

## Localization Plan

This is the hardest part if wheel encoders and T265 are unreliable.

Near-term recommendation:

- Avoid assuming full global localization.
- Build a local autonomy mode around relative movement, visible flags, and conservative obstacle avoidance.
- Use dashboard/operator initialization if rules allow it.

Possible localization options, from most practical to most ambitious:

1. Operator marks start/dump/dig zones from dashboard after visual confirmation.
2. Robot searches for flags, estimates bearing, and drives toward them using visual servoing plus local obstacle avoidance.
3. Use T265 `/odom` if it is available and stable.
4. Fix wheel encoders and fuse them later.
5. Full SLAM is likely too risky for this timeline unless already working.

For Wednesday, assume localization is weak. Design behavior that survives weak localization:

- Keep routes simple.
- Drive in short segments.
- Reobserve flags frequently.
- Use local obstacle grid for immediate safety.
- Stop and ask for operator confirmation if confidence drops.

## Navigation Strategy

The immediate practical approach is behavior-based navigation, not full global planning.

### To Dump Zone

1. Search visually for red/orange flags.
2. Pick the strongest valid flag/zone candidate.
3. Drive toward the bearing in short segments.
4. Use local top-down depth grid to avoid hazards.
5. Recompute target bearing continuously.
6. Stop in a standoff position near the dump zone.
7. Execute dump macro.

### To Dig Zone

If the dig zone is defined relative to start/dump:

1. Use known/initialized relationship if available.
2. Otherwise use a simple search pattern from start zone.
3. Avoid hazards using the local terrain grid.
4. Execute timed dig macro at a safe patch.

### Hazard Avoidance

Use local obstacle avoidance before global planning:

- If path ahead is clear, continue.
- If blocked left/right asymmetrically, steer toward the clearer side.
- If blocked everywhere, stop and rotate/search.
- If pothole risk is high, slow down or stop.

This should be exposed on the dashboard as a top-down local grid with a chosen steering direction.

## Mission State Machine

The autonomy should be a state machine with explicit abort paths:

1. `IDLE`
2. `CHECK_HEALTH`
3. `DISCOVER_DUMP`
4. `NAV_TO_DIG`
5. `DIG`
6. `NAV_TO_DUMP`
7. `DUMP`
8. `RETURN_OR_REPEAT`
9. `RECOVERY`
10. `ESTOP_OR_ABORT`

Each state should publish:

- Current state
- Target
- Confidence
- Reason for stopping
- Last successful perception update

This lets the dashboard explain what autonomy is doing.

## Dashboard Priorities

For the current architecture, the dashboard should become the autonomy bring-up surface.

Highest priority additions:

1. Point cloud health panel.
2. Top-down local obstacle/pothole grid.
3. Flag detection overlay on RGB camera feed.
4. Mission state display.
5. Buttons for high-level macros: start dig, stop dig, dump, abort autonomy.
6. Recording controls for field data.

Do not make RViz mandatory for the operator. It is reasonable to use the web dashboard as the primary interface. However, completely refusing RViz during development is risky. RViz is still the quickest way to debug TF and point cloud alignment if the dashboard has not yet reproduced those tools.

Recommendation:

- Operator workflow: web dashboard.
- Developer emergency debug: RViz/Foxglove allowed when TF or point cloud alignment is suspicious.

## Wednesday-Oriented Plan

### Day 1: Prove Hardware Signals

- Confirm drive commands stop reliably.
- Confirm depth point cloud exists or document that it does not.
- Confirm RGB flag visibility in dashboard.
- Confirm actuator commands for dig/dump.
- Record rosbag data while manually driving in representative terrain.

### Day 2: Build Assisted Autonomy

- Add top-down local terrain grid.
- Add red/orange flag detector.
- Add simple mission state machine skeleton.
- Add timed dig and dump macros.
- Add operator-supervised "mark dump" and "mark dig" options if rules allow.

### Day 3: Integrate And Test

- Run repeated dig/dump cycles with the operator ready to abort.
- Tune thresholds for Exolith lighting and terrain.
- Prefer reliability over elegance.
- Keep fallback mode: dashboard/keyboard teleop plus macro buttons.

## Practical Competition Strategy

The reliable path is not full unknown-world autonomy immediately. The reliable path is progressive autonomy:

- Let the robot discover or confirm the dump zone using flag detection.
- Let the dashboard show perception confidence.
- Use local hazard avoidance from depth.
- Use simple state-machine autonomy for repeatable dig/dump behavior.
- Keep operator fallback available.

If localization remains weak, make the robot visually servo to flags and drive in short, conservative moves. If point cloud is unreliable, fall back to slow driving plus RGB/operator confirmation. If flag detection is unreliable, allow dashboard-assisted zone marking.

## Open Questions To Resolve At The Lab

- What exact rules govern operator initialization and teleop intervention?
- Are AprilTags or extra fiducials allowed?
- What are the approximate field dimensions?
- Where are start, dump, and dig regions relative to each other?
- Is the T265 installed and publishing `/odom`?
- Does `/camera/depth/points` publish on the real robot?
- Are camera transforms correct enough for top-down projection?
- How bad are lighting changes on red/orange flag detection?
- Do rocks and potholes create reliable height signatures in the depth cloud?
