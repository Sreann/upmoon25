# Mission Control App Plan

This document describes the desired operator-facing mission control dashboard. It is intentionally product- and workflow-focused, not a technical implementation spec.

The app should be a dense, single-page control surface for operating and supervising the lunar excavation robot. It should replace the normal need for Streamlit/RViz during field operation while still allowing developer debug tools when needed.

## Progress Ledger

Last updated: 2026-05-12

### Completed Or Substantially Implemented

- React/Tailwind mission-control app exists under `lunar/mission-control`.
- Uses pnpm and builds with Vite.
- Dense one-page operator console implemented.
- Sticky safety/mission bar implemented.
- Mock/live bridge selector implemented.
- Nominal/degraded/offline fallback scenarios implemented.
- Mission state overview implemented.
- Live camera cards implemented with explicit no-stream, connecting, stale, and missing states.
- Optional camera WebSocket frame display implemented through `VITE_CAMERA_WS_BASE_URL`.
- Local terrain/navigation section implemented as a placeholder surface.
- Zone marking controls implemented and wired into command acknowledgements.
- Manual teleop controls implemented at the UI/command layer.
- Mining cycle controls implemented at the UI/command layer.
- Hardware/topic health sections implemented.
- Data/log controls implemented at the UI layer.
- Autonomy timeline, localization/SLAM status, PID, analytics, field audit, and raw config panels implemented.
- Live `MissionControlSnapshot` WebSocket client implemented.
- `lunar mission-control` and `make mission-control` launch paths added.

### In Progress

- Live robot telemetry integration through `lunar mission-bridge`.
- Safe command acknowledgements for ESTOP, pause, manual takeover, drive stop, and zone marking.
- Camera frame integration with the existing camera WebSocket service.

### Still Missing

- Real terrain grid data from point clouds.
- Real flag detection overlays.
- Real autonomy state machine messages.
- Real recording start/stop bridge command.
- Real map save/load behavior.
- Real payload command execution from the new bridge.
- Full responsive field testing on phone/tablet/laptop with the robot.

## 1. Product Goal

Build a one-page mission control dashboard that gives an operator everything needed to:

- Verify the robot is safe and ready.
- See what the robot sees.
- Understand what autonomy believes.
- Mark or confirm field zones.
- Control the robot manually when needed.
- Start, pause, resume, or abort autonomous excavation.
- Monitor dig/dump cycles.
- Diagnose failures quickly.
- Collect field data for later improvement.

The dashboard should feel like an operator console, not a marketing site and not a notebook. It should be dense, readable, fast, and practical under field pressure.

## 2. Design Principles

### Dense Over Decorative

The first screen should show real robot information immediately. Avoid hero sections, empty space, oversized headings, and explanatory filler.

### One Page

The app should be one vertically scrollable page. It may have a sticky top command bar and internal section navigation, but operators should not need to switch routes to understand the mission.

### Status Before Controls

Critical health and safety status should be visible before the operator sends commands.

### Explain The Robot

The dashboard should always answer:

- What mode is the robot in?
- What is it trying to do?
- What does it see?
- What does it believe is safe?
- What target is it pursuing?
- Why did it stop?

### Operator Authority

The operator must always be able to pause, abort, stop motion, and take manual control.

### Confidence Is A First-Class Signal

Autonomy should not just say "driving" or "mapping." It should expose confidence and freshness:

- Sensor confidence
- Localization confidence
- Terrain confidence
- Flag detection confidence
- Mission confidence

## 3. Overall Page Layout

The page should be organized from most urgent to most detailed.

Recommended vertical order:

1. Sticky Safety / Mission Bar
2. Mission State Overview
3. Live Cameras
4. Local Terrain And Navigation
5. Zone Marking And Field Model
6. Manual Teleop And Actuator Controls
7. Mining Cycle Controls
8. Autonomy Timeline / State Machine
9. Sensor And Hardware Health
10. Data Recording And Logs
11. Developer Diagnostics

The top of the page must be usable on a laptop during field operation without scrolling.

## 4. Sticky Safety / Mission Bar

This bar should remain visible at the top while scrolling.

Required elements:

- Connection status
- Robot armed/disarmed state
- Emergency stop status
- Current mode: Manual, Assisted, Auto, Paused, Recovery, Estop
- Current mission state
- Active target
- Big `ESTOP` control
- `Pause`
- `Resume`
- `Abort Autonomy`
- `Manual Takeover`
- Battery/status summary if available
- Last robot heartbeat age

This bar is the operator's anchor. It should be compact but impossible to miss.

## 5. Mission State Overview

This is the high-level summary panel.

Show:

- Current mission mode
- Current mission state
- Time in current state
- Current action
- Active goal
- Current stop reason, if stopped
- Current confidence score
- Last autonomy decision
- Next planned transition
- Loaded/empty payload state
- Current cycle count

Example states:

- `IDLE`
- `HEALTH_CHECK`
- `WAIT_FOR_ZONE_MARKS`
- `DISCOVER_DUMP_ZONE`
- `NAV_TO_DIG`
- `DIG`
- `NAV_TO_DUMP`
- `DUMP`
- `RETURN_TO_DIG`
- `RECOVERY`
- `PAUSED`
- `ABORTED`
- `ESTOP`

The operator should be able to understand the robot's intent in under five seconds.

## 6. Live Cameras

Camera feeds are central.

Required feeds:

- Front / actuator-mounted RGB camera
- Rear RGB camera
- Tracking camera if available

Each feed should show:

- Stream status
- Last frame age
- FPS
- Resolution
- Active overlays

Useful overlays:

- Red/orange flag detections
- Detection confidence
- Camera centerline
- Target bearing
- Safe/unsafe direction hints
- Autonomy-selected target

Camera controls:

- Camera pan
- Camera height
- Center camera
- Preset positions:
  - Forward
  - Ground
  - Dump zone search
  - Rear check

The camera section should help both manual driving and autonomy supervision.

## 7. Local Terrain And Navigation

This is the top-down autonomy view.

Show a robot-relative local map:

- Robot footprint
- Forward direction
- Traversable cells
- Rocks / positive obstacles
- Potholes / drop risk
- Unknown cells
- Inflated hazard zones
- Current target bearing
- Chosen steering direction
- Recent path trace

Key metrics:

- Point cloud status
- Point cloud Hz
- Valid point ratio
- Nearest obstacle distance
- Nearest pothole/drop risk
- Terrain map age
- TF status for depth projection

Controls:

- Clear local map
- Freeze/unfreeze view
- Toggle overlays
- Adjust caution level if supported

The operator should be able to see why the robot is choosing or rejecting a path.

## 8. Zone Marking And Field Model

Because operator marking is likely allowed, this is a core feature.

Show:

- Start zone
- Dig zone
- Dump zone
- Optional waypoint(s)
- Optional unsafe/no-go regions
- Optional safe corridor

Zone status:

- Unknown
- Operator marked
- Robot detected
- Confirmed
- Stale

Controls:

- Mark current robot position as start
- Mark current robot position as dig zone
- Mark current robot position as dump zone
- Mark from camera target
- Confirm detected dump flags
- Clear zone
- Re-mark zone
- Save/load field setup

The field model should be honest about uncertainty. A manually marked zone should not be confused with an autonomously detected one.

## 9. Manual Teleop And Actuator Controls

Manual control remains essential.

Drive controls:

- Forward
- Reverse
- Turn left
- Turn right
- Stop
- Speed limit
- Turn rate limit
- Hold-to-drive behavior

Drive status:

- Last command
- Command age
- Drive watchdog status
- Active control source: dashboard, keyboard, autonomy, joystick

Waypoint controls:

- Manual X/Y goal entry
- Send `Go To` target
- Show whether the goal was accepted
- Show active goal on the map
- Show latest goal command age

Actuator controls:

- Camera height
- Camera pan
- Bucket position
- Bucket chain forward/reverse/stop
- Conveyor on/off
- Stow all

Important behavior:

- Manual controls should make it clear when autonomy is disabled, paused, or overridden.
- Hold-to-drive controls should be preferred for movement.
- Stop commands should be easy to send.

## 10. Mining Cycle Controls

Mining needs its own operating panel.

Show:

- Payload state: empty, digging, loaded, dumping, unknown
- Bucket position
- Bucket chain state
- Conveyor state
- Dig timer
- Dump timer
- Current macro
- Macro progress

Controls:

- Start dig macro
- Stop dig macro
- Home/stow macro
- Start dump macro
- Stop dump macro
- Stow bucket
- Abort payload operation
- Set dig duration
- Set dump duration
- Set bucket depth preset

Future useful signals:

- Motor load
- Estimated bucket fill
- Slip during dig
- Dig success/failure classification

## 11. Autonomy Timeline / State Machine

The dashboard should show the autonomy state machine as a live timeline.

Show:

- Current state highlighted
- Recently completed states
- Failed transitions
- Recovery attempts
- Time spent in each state
- Reason for transition

Examples:

- `NAV_TO_DIG -> DIG`: reached dig tolerance
- `NAV_TO_DUMP -> RECOVERY`: local terrain blocked
- `RECOVERY -> PAUSED`: localization confidence low

This helps the operator debug autonomy without reading logs first.

## 12. Sensor And Hardware Health

This section should make hardware problems obvious.

Sensors:

- Front RGB camera
- Rear RGB camera
- Depth camera
- T265 / tracking camera
- Wheel encoders
- IR sensors
- Arduino
- Sabertooth controllers
- Battery
- Network

For each:

- Online/offline
- Last update age
- Message rate
- Current value or summary
- Warning/error state

System:

- CPU
- RAM
- Disk
- Temperature
- Network latency
- ROS domain
- Running profile
- Active nodes

The health section should tell the operator whether autonomy is allowed to run.

The current Streamlit dashboard has a useful hardware-inventory pattern that should be preserved:

- Read the hardware registry.
- Show each device category.
- Show configured model and purpose.
- Show detected status.
- Show detail such as serial number, port, or missing driver.
- Show raw hardware configuration for debugging.

Useful hardware checks to keep:

- RealSense driver import health
- T265 detection
- Front D435 detection
- Rear D435 detection
- Arduino detection
- Sabertooth left/right serial paths
- Mining spin controller path
- Jetson/off-Jetson awareness

The dashboard should distinguish:

- Device connected
- Device missing
- Driver missing
- Off-Jetson expected missing
- GPIO-capable but not physically verified

## 13. Localization And SLAM Panel

This can be its own subsection within health/navigation.

Show:

- Active pose source
- Pose freshness
- Current X/Y/yaw if available
- Localization confidence
- Drift/stationary warning
- T265 status
- Wheel encoder status
- SLAM/map status
- TF tree status summary

Controls:

- Reset odom if allowed
- Reinitialize localization
- Set current pose manually if supported
- Toggle pose source if supported

This section is critical because mapping/localization/planning are currently the biggest unknowns.

## 14. Data Recording And Logs

Field data is essential.

Controls:

- Start recording
- Stop recording
- Record preset:
  - Cameras only
  - Autonomy debug
  - Full field test
- Add event marker
- Save current field setup
- Save current map
- Enter bag/session name
- Enter map name

Show:

- Recording status
- Recording duration
- Bag name
- Disk remaining
- Recent event markers

Logs:

- Recent warnings/errors
- Filter by subsystem
- Show latest stop reason
- Show latest autonomy decision
- Copy/export session summary

Map/data operations from the Streamlit dashboard that should survive:

- Trigger map saving.
- Show whether recorder is idle or active.
- Show active bag filename.
- Make recording state visible outside the data section when recording is active.

The operator should be able to mark "interesting failure happened now" without SSH.

## 15. Developer Diagnostics

This should be lower on the page. It is useful but not primary.

Show:

- ROS topic rates
- Node status
- Process status
- Bridge status
- WebSocket status
- Last messages for key topics
- Raw mission state JSON
- Raw perception health JSON
- Raw hardware configuration
- Raw selected topic payloads for debugging

Controls:

- Restart dashboard bridge
- Restart camera bridge
- Restart selected non-critical node, if supported
- Restart mapper, if supported
- Restart motion controller, if supported
- Open Foxglove link

Dangerous controls should be separated and clearly labeled.

The current Streamlit dashboard includes quick restart controls for mapper, controller, and dashboard bridge. Keep the idea, but make it safer:

- Require confirmation for restart actions.
- Show what process/node will be affected.
- Show restart result.
- Avoid broad or destructive process kills from the browser.

## 16. Tuning And Calibration

The current Streamlit dashboard includes PID tuning controls. The mission-control app should keep a dedicated tuning/calibration section, lower on the page or behind an "advanced" disclosure.

Include:

- Drive PID gain display
- Kp/Ki/Kd controls if the robot supports live tuning
- Apply gains
- Show last applied values
- Show whether tuning command was acknowledged
- Record tuning changes in the event log

Future tuning controls:

- Flag color threshold tuning
- Terrain grid caution level
- Obstacle inflation radius
- Dig duration
- Dump duration
- Teleop speed limits

Tuning should not be visually mixed with primary safety controls. It is powerful, but not part of normal driving.

## 17. Analytics And Trends

The current Streamlit dashboard includes useful "pulse" panels. These should be kept because they help diagnose field failures.

Show trend plots for:

- CPU load
- CPU temperature
- Battery voltage
- Network latency
- Robot velocity
- Commanded/baseline velocity

Keep an odometry divergence concept:

- Compare pose/velocity source against commanded velocity or baseline.
- Show disagreement warnings.
- Use this to detect slip, bad odometry, or localization drift.

Keep an IR proximity view:

- Left/right IR values
- Simple radar or directional display
- Warning state when values cross configured thresholds

These analytics do not need to be at the top of the page, but they should be available during field testing.

## 18. Demo And Offline Mode

The current Streamlit app has a synthetic demo state when live data is unavailable. The new app should keep a deliberate version of this.

Useful behavior:

- Show the app without the robot connected.
- Simulate camera/telemetry/map data.
- Allow UI development away from the lab.
- Clearly label demo data as demo data.

Demo mode must never be confused with a connected robot.

## 19. Operator Workflows

### Startup Workflow

1. Open dashboard.
2. Confirm robot connection.
3. Confirm emergency stop state.
4. Confirm cameras.
5. Confirm drive readiness.
6. Confirm depth/terrain if available.
7. Mark or confirm start/dig/dump zones.
8. Start recording.
9. Arm autonomy or begin manual operation.

### Manual Dig/Dump Workflow

1. Drive to dig location.
2. Run dig macro.
3. Drive to dump location.
4. Run dump macro.
5. Repeat or hand off to autonomy.

### Assisted Autonomy Workflow

1. Operator marks zones.
2. Robot navigates in short segments.
3. Operator watches terrain and mission state.
4. Robot stops if confidence is low.
5. Operator confirms/re-marks/resumes.

### Full Autonomy Workflow

1. Robot health check passes.
2. Robot confirms or discovers zones.
3. Robot navigates to dig.
4. Robot digs.
5. Robot navigates to dump.
6. Robot dumps.
7. Robot repeats until stopped.

### Recovery Workflow

1. Robot stops and reports reason.
2. Dashboard shows failed sensor/blocked terrain/localization issue.
3. Operator chooses:
   - resume
   - retry
   - re-mark
   - manual takeover
   - abort

## 20. Visual Style Direction

The app should feel like a field robotics operations console:

- Dense
- Dark or neutral high-contrast mode
- Compact panels
- Clear borders and status colors
- Small, readable typography
- Minimal decoration
- No marketing hero
- No large empty cards
- No playful UI

Status colors:

- Green: healthy / active / confirmed
- Yellow: warning / stale / low confidence
- Red: unsafe / stopped / error
- Gray: unavailable / unknown
- Blue: operator-selected / manual mark

## 21. First Version Scope

The first version should not attempt everything.

Minimum useful dashboard:

- Sticky safety bar
- Mission state summary
- Front and rear camera feeds
- Manual drive controls
- Core actuator controls
- Zone marking panel
- Point cloud health
- Top-down terrain placeholder or first version
- Mining macro buttons
- Logs and stop reason
- Recording start/stop
- Map save
- Basic hardware inventory
- Basic system monitor
- Basic node/bridge status

This is enough to start replacing Streamlit without building a giant product.

## 22. Later Enhancements

Future additions:

- Better top-down terrain rendering
- Flag detection overlays
- SLAM map display
- Mission timeline
- Recording presets
- Field setup save/load
- More detailed hardware doctor
- Autonomy replay from bags
- Tuning panels for perception thresholds
- Model-based flag detector comparison
- Safer node lifecycle controls
- Richer hardware registry editor
- Operator event annotations

## 23. Streamlit Feature Preservation Checklist

When replacing the Streamlit dashboard, make sure these existing useful features are either preserved or intentionally dropped:

- Front camera feed
- Rear camera feed
- T265/tracking camera feed
- Camera WebSocket feed behavior
- Command metrics: linear velocity, position, battery, latency
- OS monitor: CPU, RAM, CPU temperature
- Live sensors: IR left/right, encoder left/right
- Occupancy/map display
- Drive hold controls
- Throttle control
- Bucket chain hold controls
- Chain speed control
- Conveyor toggle
- Bucket position control
- Camera pan control
- Camera height control
- X/Y goal entry
- Go-to command
- Home macro
- Dig macro
- Emergency stop button
- PID tuning controls
- System vital trends
- Odometry/baseline divergence plot
- IR proximity radar
- Hardware inventory from `hardware.toml`
- Detailed raw hardware config view
- Restart mapper/control/bridge actions
- Start/stop rosbag recording
- Bag naming
- Save map
- Map naming
- Recorder active/idle status
- Recent system logs
- Demo/offline telemetry mode

Some of these need safer redesign before becoming part of the new app, especially node restart controls and any command that affects robot motion.

## 24. Non-Negotiables

- Emergency stop must always be visible.
- Stop/abort must never depend only on frontend state.
- Robot-side watchdogs must enforce command timeouts.
- The browser should not be trusted as the only safety layer.
- The UI must show stale data as stale.
- The UI must distinguish unknown from healthy.
- The app must remain usable under poor network conditions.
- The operator must always know who has control: manual, autonomy, keyboard, joystick, or dashboard.

## 25. Success Definition

The app succeeds when an operator can run a field session from one page:

- Verify hardware.
- Watch cameras.
- See terrain risk.
- Mark zones.
- Drive manually.
- Run dig/dump macros.
- Start and supervise autonomy.
- Understand why the robot stopped.
- Take over immediately.
- Record useful data.

The app should reduce field confusion. It should make the robot's state and intent obvious.
