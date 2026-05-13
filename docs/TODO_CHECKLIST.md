# Action checklist — upmoon25

Use `- [ ]` / `- [x]` in your editor to tick items. Order is roughly **do first at top**.

---

## Blocking — before trusting demos or competition runs

- [ ] **Miner CLI**: Make `miner start` work OR document only `miner run`; align `main_controller` help text with `mining_controller.onCmd`.
- [ ] **ROS_DOMAIN_ID**: Pick one value (e.g. team standard **8888** or **25**) and set it on **Jetson, RC laptop, autonomy laptop, Docker, and `lunar` `.lunar/config.json`** — all must match.
- [ ] **Drive command arbitration**: Decide who may publish motion (`joystick_driver`, `mining_controller`, `motion_controller`) — add mode switch, topic remaps, or mux — so commands don’t silently fight.
- [ ] **README secrets**: Remove passwords and sensitive IPs from `README.md`; share credentials via a private channel; rotate anything already exposed.
- [ ] **Field log motion**: Run `motion_controller` on the real robot with bag/log compare to sim; note failures before relying on autonomy.

---

## Mining controller (`mining_controller.py`)

- [ ] Fix **`RAISE_BUCKET`** timing logic (dead/unreachable branches); match code to intended bucket-raise sequence.
- [ ] Replace **`abort`** behavior: stop actuators and **stay alive** for new commands instead of `rclpy.shutdown()` / killing the node.
- [ ] Document **`recinit` vs `recdump`** accurately in CLI help (init distance vs dump distance).
- [ ] Reduce reliance on **tag-only pose** during cycles — add encoder/time bounds or recovery if tag is lost.
- [ ] Expand **IR** use if required for align/collect (or document that IR is only used at lower→dig).
- [ ] Move magic numbers (**speeds, timers, IR threshold**) to **ROS parameters** or YAML for tuning without edits.
- [ ] Clean **logging** (avoid spam every timer tick); fix **`Marker.ns`** and other RViz clutter.
- [ ] Add **unit tests** for state transitions (mock clock, IR, pose).
- [ ] (Optional redesign) Implement desired cycle: **bucket calibrate (e.g. pos 20) → IR align → forward D → back D → conveyor → repeat with counter/timer**.

---

## Autonomy stack (non-mining)

- [ ] **`localizer`**: Either prove it with metrics or remove/hide from operator docs until then (currently discouraged in code).
- [ ] **`path_planner`**: Address TODOs — goal orientation, duplicated logic, configurability.
- [ ] **`global_mapper`**: Profile CPU load; consider CUDA TODO if maps lag.
- [ ] **`global_costmapper`**: Shared parameter file / single source of tuning values with planner.
- [ ] Confirm **`/cmd/velocity`** publishers match **`drive_motors`** subscriptions under your launch namespaces.

---

## Frontend / hardware

- [ ] **`arduino_driver`**: Verify command ranges/rates vs firmware for pan, bucket, camera height, conveyor.
- [ ] **`drive_motors`**: Test USB re-enumeration / port changes on Jetson.
- [ ] **Firmware**: Ensure deployed Arduino binary matches `firmware/arduino/` sources (no stray old HEX).

---

## Simulation & interfaces

- [ ] **`servo_plugin.cc`**: Profile if Gazebo drops ticks (performance TODO).
- [ ] **`gz_worlds`**: After URDF/world changes, verify spawn pose and TF still connect **`map` → `odom` → `base_link`**.

---

## Tooling (`lunar`) — from journal roadmap

- [ ] Host **`./lunar` wrapper** that forwards into Docker without manual `docker exec`.
- [ ] Replace root scripts when ready: **`BUILD.bash` → `lunar build`**, **`RUN_ROBOT.bash` → `lunar run robot`**, **`MAX_RUN.sh` → `lunar run autonomy`** (or chosen profile names).
- [ ] **`lunar firmware compile/flash`** via `arduino-cli` (optional but reduces “black box” flashes).
- [ ] **`lunar test --unit`**: wire `colcon test`.
- [ ] **`lunar test --sim`**: headless smoke test (move / subscribe sanity).
- [ ] **`lunar data record`** / **save-map** helpers (rosbags, map snapshots).
- [ ] **`lunar layout export`** for Foxglove layouts.

---

## Dashboard (optional enhancements)

- [ ] Live camera in dashboard (if still blind per `DASHBOARD_OPPORTUNITIES.md`).
- [ ] Map overlay / occupancy preview (if mapping runs during ops).
- [ ] High-level buttons: dig sequence / estop / record bag (per opportunities doc).

---

## Documentation

- [ ] One **runbook**: exact commands for Jetson vs RC vs autonomy for competition day.
- [ ] Document **`miner`** sequence end-to-end (`mark`, `recinit`, `recdump`, `run`, `abort`).
- [ ] Note **`motion_controller`** “sim-first” caveat in operator-facing docs.

---

## Safety process (team policy)

- [ ] Written rule: **who has authority** to enable autonomy vs teleop vs mining.
- [ ] **E-stop** and wireless drop tested with software running.
- [ ] **Watchdog** or heartbeat policy for web/dashboard teleop if used.

---

*Derived from `docs/RIGOROUS_AUDIT.md`, mining discussion, and `lunar/JOURNAL.md`.*
