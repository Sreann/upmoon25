# Field Readiness Audit

Use this checklist before attempting autonomous driving, mapping, or dig/dump cycles. The goal is to replace guesses with facts about what works on the real robot today.

**Stack note:** Intel RealSense T265 is deprecated for this program. Treat `/odom` as coming from your active localization source (for example wheel odometry or SLAM), not from a tracking camera.

## 1. Safety First

- [ ] Emergency stop is accessible.
- [ ] Emergency stop has been tested today.
- [ ] Robot can be safely lifted, blocked, or restrained for drive tests.
- [ ] Operator has a clear manual takeover path.
- [ ] Team agrees who is allowed to command motion.
- [ ] Battery is secured and voltage is acceptable.
- [ ] No loose wiring near wheels, bucket, conveyor, or camera actuator.

Notes:

```text

```

## 2. Startup

- [ ] Robot boots normally.
- [ ] Jetson/network connection works.
- [ ] Dashboard opens.
- [ ] `lunar keyboard` can connect.
- [ ] ROS environment is sourced/running correctly.
- [ ] Correct ROS domain is active.
- [ ] No unexpected duplicate robot nodes are running.

Notes:

```text

```

## 3. Manual Drive

- [ ] Forward command works.
- [ ] Reverse command works.
- [ ] Left turn works.
- [ ] Right turn works.
- [ ] Stop command works immediately.
- [ ] Robot stops if keyboard/dashboard command is released.
- [ ] Robot does not continue moving after dashboard disconnect.
- [ ] Drive speed is controllable enough for slow field testing.

Record:

```text
Drive command topic:
Observed issues:
Maximum safe test speed:
Stop behavior:
```

## 4. Emergency Stop

- [ ] Emergency stop cuts or prevents dangerous motion.
- [ ] Emergency stop works during drive motion.
- [ ] Emergency stop works during bucket/conveyor motion.
- [ ] Recovery/reset procedure is understood.

Record:

```text
E-stop test result:
Recovery procedure:
Concerns:
```

## 5. Cameras

- [ ] Front / actuator-mounted RGB camera feed works.
- [ ] Rear RGB camera feed works.
- [ ] Front and rear RGB streams work.
- [ ] Camera feed latency is acceptable.
- [ ] Camera height control works.
- [ ] Camera pan control works.
- [ ] Red/orange flags are visible in the camera feed under lab lighting.

Record:

```text
Front camera topic:
Rear camera topic:
Tracking camera topic:
Flag visibility notes:
Camera latency notes:
```

## 6. Depth And Point Cloud

- [ ] Depth camera is physically connected.
- [ ] `/camera/depth/points` exists.
- [ ] `/camera/depth/points` publishes at a usable rate.
- [ ] Point cloud data changes when objects move in front of the camera.
- [ ] Point count is nonzero.
- [ ] Point cloud frame is known.
- [ ] Depth data appears usable for rocks/potholes.

Record:

```text
Point cloud topic:
Publish rate:
Frame ID:
Point count:
Valid point ratio, if available:
Observed depth issues:
```

## 7. TF And Frames

- [ ] `base_link` exists.
- [ ] `depth_link_optical` exists.
- [ ] Transform from `depth_link_optical` to `base_link` exists.
- [ ] `odom` exists, if localization is running.
- [ ] `map` exists, if mapping/localization is running.
- [ ] Camera/depth frame orientation looks plausible.

Record:

```text
Available frames:
Missing transforms:
Suspicious transforms:
```

## 8. Odometry And Localization

- [ ] `/odom` exists.
- [ ] `/odom` changes when the robot moves.
- [ ] `/odom` stays mostly stable when the robot is stationary.
- [ ] `/odom` is present and sane for your localization stack.
- [ ] Wheel encoder topics publish.
- [ ] Encoder signs/scales make sense, if available.
- [ ] Localization confidence is good enough for short test moves, or marked as not ready.

Record:

```text
Odom source:
Odom topic:
Stationary drift:
Encoder topics:
Encoder issues:
Localization ready? yes/no:
```

## 9. Sensors

- [ ] IR left publishes.
- [ ] IR right publishes.
- [ ] IR values change when an object is placed nearby.
- [ ] Battery voltage is available, if wired.
- [ ] CPU temperature is visible.
- [ ] Network latency is visible or measurable.

Record:

```text
IR left behavior:
IR right behavior:
Battery reading:
CPU temp:
Network notes:
```

## 10. Mining And Dumping

- [ ] Bucket position control works.
- [ ] Bucket chain forward works.
- [ ] Bucket chain reverse works.
- [ ] Bucket chain stop works.
- [ ] Conveyor on/off works.
- [ ] Manual dig sequence works.
- [ ] Manual dump sequence works.
- [ ] Stow/home position is known.
- [ ] Payload mechanism can be stopped quickly.

Record:

```text
Dig sequence that works:
Dump sequence that works:
Safe bucket positions:
Timing notes:
Problems:
```

## 11. Dashboard

- [ ] Dashboard shows live robot connection.
- [ ] Dashboard shows camera feeds.
- [ ] Dashboard controls drive or confirms drive is controlled elsewhere.
- [ ] Dashboard controls camera pan/height.
- [ ] Dashboard controls bucket/conveyor, if enabled.
- [ ] Dashboard shows recent logs.
- [ ] Dashboard shows hardware status.
- [ ] Dashboard shows recording status.
- [ ] Dashboard stop/abort controls are visible.

Record:

```text
Dashboard URL:
Broken panels:
Missing critical controls:
Latency issues:
```

## 12. Data Recording

- [ ] Rosbag recording can start.
- [ ] Rosbag recording can stop.
- [ ] Recording path has enough disk space.
- [ ] Bag name/session name is set.
- [ ] At least one short test bag has been recorded and verified.

Recommended topics:

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
- `/sensor/encoder/left`
- `/sensor/encoder/right`
- `/rosout`

Record:

```text
Bag filename:
Bag duration:
Disk remaining:
Topics missing:
```

## 13. Mapping And Planning

- [ ] Existing map topic publishes, if available.
- [ ] Map changes when the robot/depth camera sees terrain.
- [ ] Top-down terrain grid exists, if implemented.
- [ ] Planner can accept a target, if available.
- [ ] Robot can drive a short autonomous segment, if allowed.
- [ ] Robot stops when perception/localization is stale.

Record:

```text
Map topic:
Planner target interface:
Autonomous segment tested? yes/no:
Observed planning issues:
```

## 14. Field Marking

- [ ] Start zone location is known or marked.
- [ ] Dig zone location is known or marked.
- [ ] Dump zone location is known or marked.
- [ ] Red/orange dump flags are visible.
- [ ] Any no-go zones are marked.
- [ ] Team knows whether operator marking is allowed by rules.

Record:

```text
Start zone:
Dig zone:
Dump zone:
No-go zones:
Marking rule confirmation:
```

## 15. Go / No-Go Decision

Do not attempt autonomous motion unless these are true:

- [ ] Emergency stop works.
- [ ] Manual stop works.
- [ ] Drive works at slow speed.
- [ ] Camera feed works.
- [ ] Operator can take over.
- [ ] Recording is available.

For obstacle-aware autonomy, also require:

- [ ] Depth point cloud works.
- [ ] TF from depth to robot is available.
- [ ] Local terrain/map view is believable.

For zone-to-zone autonomy, also require one of:

- [ ] Reliable localization/odom.
- [ ] Operator-marked zones with short-segment navigation.
- [ ] Visual flag servoing with local obstacle avoidance.

Final decision:

```text
Manual testing ready? yes/no:
Assisted autonomy ready? yes/no:
Full autonomy ready? yes/no:
Reason:
```

## 16. End-Of-Test Summary

Fill this out before leaving the field.

```text
Date/time:
Location:
Team members:

What worked:

What failed:

Most important next fix:

Data recorded:

Autonomy confidence:

Safety concerns:
```
