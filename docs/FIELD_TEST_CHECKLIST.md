# Field / bench integration checklist — sensors & actuators

Use this **on the robot + laptop/Jetson** while watching **topics, RViz/Foxglove, logs, and physical motion**. Check boxes when **both** software output **and** hardware behavior match expectations.

**Safety before every session**

- [ ] Robot **blocked / wheels clear** or on stands as appropriate for the test.
- [ ] **E-stop** location known; spotter if driving on ground.
- [ ] **`ROS_DOMAIN_ID`** matches on **this machine and Jetson** (`echo $ROS_DOMAIN_ID`).
- [ ] Workspace built and sourced: `source install/setup.bash` (after `colcon build`).

---

## A — Bring-up (no motion)

- [ ] **`ros2 daemon stop`** then **`ros2 daemon start`** (fresh discovery).
- [ ] **`ros2 node list`** shows expected nodes after your launch (e.g. `ros2 launch frontend comp_launch.py` or `jet_launch.py`).
- [ ] **`ros2 topic list`** includes the topics you plan to test below (names may be prefixed if you use namespaces).

---

## B — Odometry & tracking camera (T265)

**Launch:** `t265_driver` must be running.

| Step | Action | Pass criteria |
|------|--------|----------------|
| B1 | `ros2 topic hz /odom` | Stable rate (typical ~30 Hz class; note actual printout). |
| B2 | `ros2 topic echo /odom --once` | `twist` field updates when you **physically** micro-move robot or wheels free-spin safely. |
| B3 | Optional image | `ros2 topic hz /camera/tracking/image_compressed` | Non-zero rate if topic enabled. |

- [ ] B1  
- [ ] B2  
- [ ] B3  

---

## C — Front RGB (D435 front pipe via `rgb_driver`)

**Parameters:** Check launch uses `publish_raw` / `publish_compressed` you expect.

| Step | Action | Pass criteria |
|------|--------|----------------|
| C1 | `ros2 topic hz /camera/rgb/image_raw` OR `/camera/rgb/image_compressed` | Non-zero Hz when publishing enabled. |
| C2 | RViz: **Image** display on chosen topic | Live picture moves when you wave hand in front of camera. |
| C3 | `ros2 topic echo /camera/rgb/camera_info --once` | Reasonable `width`/`height` (e.g. 640×480 per `hardware.toml`). |

- [ ] C1  
- [ ] C2  
- [ ] C3  

---

## D — Depth + rear RGB (`depth_driver`)

**Note:** Point cloud may only publish when `demand_publish` / `/cmd/pointcloud` policy matches your launch params.

| Step | Action | Pass criteria |
|------|--------|----------------|
| D1 | `ros2 topic hz /camera/depth/points` | If launch expects continuous cloud: non-zero Hz. If demand-only: publish **`std_msgs/Int8` `data: 1`** to **`/cmd/pointcloud`** then Hz spikes. |
| D2 | `ros2 topic hz /camera/rear/image_raw` or `.../image_compressed` | Non-zero when rear camera connected and driver OK. |
| D3 | RViz: **PointCloud2** on `/camera/depth/points` | Points resemble scene when cloud publishes. |

- [ ] D1  
- [ ] D2  
- [ ] D3  

---

## E — IR sensors & encoders (Arduino bridge)

**Launch:** `arduino_driver`.

| Step | Action | Pass criteria |
|------|--------|----------------|
| E1 | `ros2 topic hz /sensor/ir` | Updates when sensor sees changing distance (hand in/out). |
| E2 | If wired | `ros2 topic hz /sensor/ir/left` and `/sensor/ir/right` | Same idea per channel. |
| E3 | Drive wheels gently **with wheels unloaded or blocked** | `ros2 topic echo /sensor/encoder/left --once` (repeat) values trend when mandated by firmware. |

- [ ] E1  
- [ ] E2  
- [ ] E3  

---

## F — Bucket alarm GPIO (`bucket_alarm` node)

**Note:** Not included in `comp_launch.py` / `jet_launch.py` by default — start manually if you use it:  
`ros2 run frontend bucket_alarm`

| Step | Action | Pass criteria |
|------|--------|----------------|
| F1 | `ros2 topic hz /sensor/bucket_alarm` | ~10 Hz from timer in driver. |
| F2 | **Mechanically** trigger alarm condition per wiring (stall/limit) | Topic switches **0 ↔ 1** consistent with driver logic (`bucket_alarm.py`). |

- [ ] F1  
- [ ] F2  

---

## G — Pan feedback (`/camera/rgb/pan`)

**Launch:** `arduino_driver`.

| Step | Action | Pass criteria |
|------|--------|----------------|
| G1 | `ros2 topic echo /camera/rgb/pan --once` | Numeric feedback present. |
| G2 | Publish small pan command (see **K**) | Feedback value trends toward commanded behavior (direction per mechanical setup). |

- [ ] G1  
- [ ] G2  

---

## H — Joint states / TF

| Step | Action | Pass criteria |
|------|--------|----------------|
| H1 | `ros2 topic hz /joint_states` | Non-zero when Arduino publishes joints. |
| H2 | `ros2 run tf2_ros tf2_echo map base_link` (or `odom` → `base_link`) | Transform exists **after** static/map publishers running (may fail until TF tree complete). |

- [ ] H1  
- [ ] H2  

---

## I — AprilTag pipeline (`tag_detector`)

**Launch:** Often `tag_detector` + RGB feeding it (compressed vs raw per params).

| Step | Action | Pass criteria |
|------|--------|----------------|
| I1 | With tag in view | `ros2 topic hz /camera/rgb/tag_pose` or detector output your launch uses | Non-zero when tag visible. |
| I2 | Move tag out of frame | Rate drops or messages stop (confirms coupling to vision). |

- [ ] I1  
- [ ] I2  

---

## J — Drive train (`drive_motors` + Sabertooth)

**Convention:** `cmd/velocity` **`Twist`**: `linear.x` and `angular.z` are **roughly −100…100** throttle units (see `drive_motors.py`). Commands **decay to zero** after **timeout** (~0.75 s) if not refreshed — normal.

**Preparation:** wheels safe (stands / clearance); **small** magnitudes first.

| Step | Action | Pass criteria |
|------|--------|----------------|
| J1 | `ros2 topic pub --once cmd/velocity geometry_msgs/msg/Twist "{linear: {x: 5.0}, angular: {z: 0.0}}"` | Wheels briefly drive **forward** then ramp down after timeout. |
| J2 | Repeat with **negative** `linear.x` | **Reverse** behavior. |
| J3 | `linear.x: 0`, small **`angular.z`** (+ then −) | **Pivot** correct direction for your `DIR` constant / wiring. |
| J4 | Confirm watchdog | Stop publishing; wheels relax to stop within timeout. |

- [ ] J1  
- [ ] J2  
- [ ] J3  
- [ ] J4  

---

## K — Arduino-actuated commands (pan, camera height, bucket position)

**Topics:** `cmd/pan`, `cmd/camera_height`, `cmd/bucket_pos` — **`std_msgs/Int16`**.

**Use conservative values first**; confirm PWM limits with ME/electrical.

| Step | Action | Pass criteria |
|------|--------|----------------|
| K1 | `ros2 topic pub --once cmd/pan std_msgs/msg/Int16 "{data: 90}"` | Servo/camera head moves; `/camera/rgb/pan` updates over time. |
| K2 | `ros2 topic pub --once cmd/camera_height std_msgs/msg/Int16 "{data: 50}"` | Mechanism moves (direction/safe range per team calibration). |
| K3 | `ros2 topic pub --once cmd/bucket_pos std_msgs/msg/Int16 "{data: 30}"` | Bucket linear position responds per linkage. |

- [ ] K1  
- [ ] K2  
- [ ] K3  

---

## L — Bucket chain motor (`bucket_spin` → Modbus)

**Topic:** `cmd/bucket_vel` **`Int16`** (RPM-style command per node doc).

| Step | Action | Pass criteria |
|------|--------|----------------|
| L1 | `ros2 topic pub --rate 10 cmd/bucket_vel std_msgs/msg/Int16 "{data: 10}"` | Chain rotates slowly **correct sign**; node logs no repeated Modbus errors. |
| L2 | `ros2 topic pub --once cmd/bucket_vel std_msgs/msg/Int16 "{data: 0}"` | Motion stops (may ramp — watch briefly). |

- [ ] L1  
- [ ] L2  

---

## M — Conveyor (`conveyor` node — Jetson GPIO)

**Note:** Not in default `comp_launch.py`; run **`ros2 run frontend conveyor`** when hardware present.

**Topic:** `cmd/conveyor` **`Int16`**: **`1` = ON**, **`0` = OFF** per `conveyor.py`.

| Step | Action | Pass criteria |
|------|--------|----------------|
| M1 | `ros2 topic pub --once cmd/conveyor std_msgs/msg/Int16 "{data: 1}"` | Conveyor runs / relay engages **audibly or visually**. |
| M2 | `ros2 topic pub --once cmd/conveyor std_msgs/msg/Int16 "{data: 0}"` | Conveyor stops. |

- [ ] M1  
- [ ] M2  

---

## N — Teleop integration (joystick or keyboard)

**Purpose:** Confirms same topics as manual pubs reach hardware under normal pilot stack.

| Step | Action | Pass criteria |
|------|--------|----------------|
| N1 | Launch **`joystick_driver`** (RC laptop) or **`keyboard_driver`** | Each binding moves drive / conveyor / bucket / pan / height as designed. |
| N2 | While holding drive | **`ros2 topic hz cmd/velocity`** reflects pilot rate. |

- [ ] N1  
- [ ] N2  

---

## O — Mining controller (integration smoke)

**Only after J–M proven.** Mining publishes **`cmd/velocity`**, **`cmd/conveyor`**, **`cmd/bucket_vel`**, **`cmd/bucket_pos`**.

| Step | Action | Pass criteria |
|------|--------|----------------|
| O1 | With miner idle | Send **`miner abort`** or equivalent `/cmd/miner` frame if testing miner CLI — robot stays still. |
| O2 | **Dry run:** trace logs when issuing **`miner run`** after **`recinit`/`recdump`** setup per team procedure | States advance **without** unexpected motion if you purposefully **disable drive** (not standard — optional harness); otherwise **full caution**. |

- [ ] O1  
- [ ] O2  

*(Detailed miner sequencing belongs in a competition runbook; CLI uses **`run`**, not **`start`, unless fixed.)*

---

## P — Session close-out

- [ ] Publish **zero** drive: `Twist` zeros on `cmd/velocity`.
- [ ] **`cmd/bucket_vel`** → `0`, **`cmd/conveyor`** → `0`, bucket position to safe pose per team.
- [ ] Stop launch files cleanly (**Ctrl-C**); confirm **`ros2 node list`** empties for your stack.
- [ ] Note serial ports (`ls /dev/ttyACM* /dev/ttyUSB*`) if anything flaky — compare to `hardware.toml`.

---

## Quick topic reference (common names)

| Purpose | Topic(s) |
|---------|-----------|
| Odometry | `/odom` |
| Front camera | `/camera/rgb/image_raw`, `/camera/rgb/image_compressed`, `/camera/rgb/camera_info` |
| Depth cloud | `/camera/depth/points`; trigger `/cmd/pointcloud` if demand mode |
| Rear camera | `/camera/rear/image_raw`, `/camera/rear/image_compressed` |
| T265 image | `/camera/tracking/image_compressed` |
| IR | `/sensor/ir`, `/sensor/ir/left`, `/sensor/ir/right` |
| Encoders | `/sensor/encoder/left`, `/sensor/encoder/right` |
| Bucket alarm | `/sensor/bucket_alarm` |
| Pan feedback | `/camera/rgb/pan` |
| Drive command | `cmd/velocity` (`geometry_msgs/Twist`) |
| Conveyor | `cmd/conveyor` (`Int16` 0/1) |
| Bucket chain | `cmd/bucket_vel` (`Int16`) |
| Bucket position | `cmd/bucket_pos` (`Int16`) |
| Pan / cam height cmds | `cmd/pan`, `cmd/camera_height` |

---

*Adjust Hz expectations and safe command ranges to match your season tuning. If a step doesn’t apply (sensor absent), mark **N/A** and record why.*
