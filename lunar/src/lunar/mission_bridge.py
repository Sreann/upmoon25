from __future__ import annotations

import asyncio
import json
import math
import queue
import re
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict

import psutil
import tornado.ioloop
import tornado.web
import tornado.websocket

MISSION_BRIDGE_PORT = 8770
SNAPSHOT_HZ = 4.0
STALE_TOPIC_SEC = 1.0
MISSING_TOPIC_SEC = 3.0

CAMERA_TOPICS = {
    "front": "/camera/rgb/image_compressed",
    "rear": "/camera/rear/image_compressed",
}
SAFETY_TOPICS = {
    "/camera/depth/points",
    "/odom",
    "/tf",
    "cmd/velocity",
}

_clients_lock = threading.Lock()
_clients = set()
_io_loop = None
_command_queue: "queue.Queue[QueuedCommand]" = queue.Queue()


@dataclass
class TopicSample:
    topic: str
    note: str
    safety_critical: bool = False
    last_seen: float | None = None
    count: int = 0
    last_count: int = 0
    rate_hz: float = 0.0
    width: int | None = None
    height: int | None = None


@dataclass
class MissionBridgeState:
    started_at: float = field(default_factory=time.time)
    last_rate_tick: float = field(default_factory=time.time)
    odom_x: float = 0.0
    odom_y: float = 0.0
    odom_yaw_rad: float = 0.0
    odom_pose_frame_id: str = "odom"
    linear_vel: float = 0.0
    angular_vel: float = 0.0
    baseline_vel: float = 0.0
    battery_voltage: float = 0.0
    cpu_usage: float = 0.0
    cpu_temp: float = 0.0
    ram_usage: float = 0.0
    ir_left: int | None = None
    ir_right: int | None = None
    encoder_left: int | None = None
    encoder_right: int | None = None
    point_cloud_points: int = 0
    armed: bool = False
    estop: bool = False
    mode: str = "Manual"
    mission_state: str = "PERCEPTION_FAULT"
    payload_state: str = "unknown"
    stop_reason: str = "Waiting for live localization and depth topics."
    last_decision: str = "Telemetry snapshot generated."
    next_transition: str = "Confirm odom, depth, camera, and zone marking before autonomy."
    terrain_status: Dict[str, Any] | None = None
    terrain_grid: Dict[str, Any] | None = None
    flag_candidates: Dict[str, Any] | None = None
    autonomy_state: Dict[str, Any] | None = None
    nav_mission_state: Dict[str, Any] | None = None
    dig_sequence_state: Dict[str, Any] | None = None
    navigation_active: bool = False
    navigation_status: Dict[str, Any] | None = None
    navigation_status_seen: float | None = None
    pan_angle: int = 90
    camera_height: int = 0
    bucket_pos: int = 0
    bucket_vel: int = 0
    conveyor: int = 0
    recent_logs: Deque[Dict[str, str]] = field(default_factory=lambda: deque(maxlen=30))
    trends: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=24))
    topics: Dict[str, TopicSample] = field(default_factory=dict)
    zones: Dict[str, Dict[str, str]] = field(
        default_factory=lambda: {
            "start": {"label": "Start Zone", "status": "unknown", "detail": "not marked in bridge yet"},
            "dig": {"label": "Dig Zone", "status": "unknown", "detail": "requires field discovery or operator mark"},
            "dump": {"label": "Dump Zone", "status": "unknown", "detail": "red/orange flag detector pending"},
            "no_go": {"label": "No-Go Zones", "status": "unknown", "detail": "rocks/potholes need costmap source"},
        }
    )

    def ensure_topic(self, topic: str, note: str, safety_critical: bool = False) -> TopicSample:
        if topic not in self.topics:
            self.topics[topic] = TopicSample(topic=topic, note=note, safety_critical=safety_critical)
        return self.topics[topic]

    def touch_topic(self, topic: str, *, width: int | None = None, height: int | None = None) -> None:
        sample = self.ensure_topic(topic, "observed", topic in SAFETY_TOPICS)
        sample.last_seen = time.time()
        sample.count += 1
        sample.width = width
        sample.height = height


_state = MissionBridgeState()


@dataclass
class QueuedCommand:
    request_id: str | None
    command: Dict[str, Any]
    reply: Callable[[Dict[str, Any]], None]


class MissionControlWebSocket(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        with _clients_lock:
            _clients.add(self)
        self.write_message(json.dumps({"kind": "snapshot", "snapshot": build_snapshot()}))

    def on_close(self):
        with _clients_lock:
            _clients.discard(self)

    def on_message(self, message):
        request_id = None
        try:
            payload = json.loads(message)
            request_id = payload.get("requestId")
            command = payload.get("command", {})
        except Exception:
            result = {
                "accepted": False,
                "message": "Invalid command JSON.",
                "commandId": request_id,
            }
            self.write_message(json.dumps({"kind": "command_result", "requestId": request_id, "result": result}))
            return

        def reply(result: Dict[str, Any]) -> None:
            if _io_loop is None:
                return
            _io_loop.add_callback(
                self.write_message,
                json.dumps({"kind": "command_result", "requestId": request_id, "result": result}),
            )

        _command_queue.put(QueuedCommand(request_id=request_id, command=command, reply=reply))


class HealthHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Cache-Control", "no-store")

    def get(self):
        self.write({"ok": True, "clients": len(_clients), "snapshot_hz": SNAPSHOT_HZ})


def _status_for_topic(sample: TopicSample) -> tuple[str, str, str]:
    if sample.last_seen is None:
        return "missing", "--", "--"

    age_sec = max(0.0, time.time() - sample.last_seen)
    if age_sec > MISSING_TOPIC_SEC:
        status = "missing"
    elif age_sec > STALE_TOPIC_SEC:
        status = "stale"
    else:
        status = "live"

    if age_sec < 1.0:
        age = f"{int(age_sec * 1000)} ms"
    else:
        age = f"{age_sec:.1f} s"
    rate = f"{sample.rate_hz:.1f} Hz" if sample.rate_hz > 0 else "--"
    return status, age, rate


def _get_cpu_temp() -> float:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r", encoding="utf-8") as f:
            return float(f.read().strip()) / 1000.0
    except Exception:
        return 0.0


def _metric_status_bad_when_zero(value: float) -> str:
    return "bad" if value <= 0 else "ok"


def _nav_mission_for_dashboard(raw: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not raw:
        return None
    return {
        "phase": raw.get("phase"),
        "controllerMode": raw.get("controller_mode"),
        "detail": raw.get("detail"),
        "digAutonomyEnabled": bool(raw.get("dig_autonomy_enabled", False)),
        "navCorridorEnabled": bool(raw.get("nav_controller_corridor_enabled", False)),
        "digDistanceM": raw.get("dig_distance_m"),
        "unknownFraction": raw.get("unknown_fraction"),
    }


def _navigation_steering_for_dashboard() -> Dict[str, Any] | None:
    raw = _state.navigation_status
    if not raw:
        return None
    age_ms = None
    if _state.navigation_status_seen is not None:
        age_ms = int(max(0.0, time.time() - _state.navigation_status_seen) * 1000)
    reason = str(raw.get("plan_reason") or raw.get("gated_reason") or "")
    return {
        "linearX": float(raw.get("linear_x", 0.0)),
        "angularZ": float(raw.get("angular_z", 0.0)),
        "reason": reason,
        "ageMs": age_ms,
    }


def _dig_sequence_for_dashboard(raw: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not raw:
        return None
    return {
        "phase": raw.get("phase"),
        "waitForNavDigArm": bool(raw.get("wait_for_nav_dig_arm", False)),
        "digArm": bool(raw.get("dig_arm", False)),
        "irValue": raw.get("ir_value"),
        "irTarget": raw.get("ir_target"),
        "encoderValue": raw.get("encoder_value"),
        "encoderTarget": raw.get("encoder_target"),
        "encoderTopic": raw.get("encoder_topic"),
        "cycleCounter": raw.get("cycle_counter"),
        "maxCyclesLe": raw.get("max_cycles_le"),
        "bucketPosCommanded": raw.get("bucket_pos_commanded"),
        "keepBucketChainUntilDone": bool(raw.get("keep_bucket_chain_until_done", False)),
        "phaseElapsedSec": raw.get("phase_elapsed_sec"),
        "conveyorRemainingSec": raw.get("conveyor_remaining_sec"),
        "useLocalTerrainGrid": bool(raw.get("use_local_terrain_grid", False)),
        "terrainHadGrid": bool(raw.get("terrain_had_grid", False)),
        "terrainFresh": bool(raw.get("terrain_fresh", False)),
        "terrainForwardOk": bool(raw.get("terrain_forward_ok", True)),
        "terrainReverseOk": bool(raw.get("terrain_reverse_ok", True)),
        "terrainGateForward": raw.get("terrain_gate_forward"),
        "terrainGateReverse": raw.get("terrain_gate_reverse"),
    }


def build_snapshot() -> Dict[str, Any]:
    now = time.time()
    connected = any(sample.last_seen is not None and now - sample.last_seen <= MISSING_TOPIC_SEC for sample in _state.topics.values())
    odom_sample = _state.ensure_topic("/odom", "localization source", True)
    depth_sample = _state.ensure_topic("/camera/depth/points", "depth grid source", True)
    odom_status, odom_age, _ = _status_for_topic(odom_sample)
    depth_status, _, _ = _status_for_topic(depth_sample)

    topics = []
    for topic, note, safety in [
        ("/camera/rgb/image_compressed", "front RGB", False),
        ("/camera/rear/image_compressed", "rear RGB", False),
        ("/camera/depth/points", "depth grid source", True),
        ("/odom", "localization source", True),
        ("/tf", "frame transforms", True),
        ("cmd/velocity", "command echo/watchdog source", True),
    ]:
        sample = _state.ensure_topic(topic, note, safety)
        status, age, rate = _status_for_topic(sample)
        topics.append(
            {
                "topic": topic,
                "status": status,
                "age": age,
                "rate": rate,
                "note": sample.note,
                "safetyCritical": sample.safety_critical,
            }
        )

    cameras = []
    for camera_id, topic in CAMERA_TOPICS.items():
        sample = _state.ensure_topic(topic, f"{camera_id} camera", False)
        status, _, _ = _status_for_topic(sample)
        cameras.append(
            {
                "id": camera_id,
                "name": {"front": "Front D435 RGB", "rear": "Rear D435 RGB"}[camera_id],
                "topic": topic,
                "status": status,
                "fps": f"{sample.rate_hz:.0f}" if sample.rate_hz > 0 else "--",
                "resolution": f"{sample.width}x{sample.height}" if sample.width and sample.height else "--",
            }
        )

    if _state.estop:
        _state.mode = "Estop"
        _state.mission_state = "ESTOP"
        _state.stop_reason = "Operator ESTOP command is active."
    elif _state.autonomy_state:
        _state.mode = str(_state.autonomy_state.get("mode", _state.mode))
        _state.mission_state = str(_state.autonomy_state.get("state", _state.mission_state))
        _state.armed = bool(_state.autonomy_state.get("armed", _state.armed))
        _state.stop_reason = str(_state.autonomy_state.get("stop_reason", _state.stop_reason))
        _state.last_decision = str(_state.autonomy_state.get("last_decision", _state.last_decision))
        _state.next_transition = str(_state.autonomy_state.get("next_transition", _state.next_transition))
        _state.payload_state = str(_state.autonomy_state.get("payload", _state.payload_state))
    elif (
        connected
        and odom_status == "live"
        and depth_status == "live"
        and _state.mission_state == "PERCEPTION_FAULT"
    ):
        _state.mission_state = "AWAIT_MARK_DIG"
        _state.stop_reason = "Safe command bridge connected. Autonomy supervisor JSON not enabled; awaiting dig zone mark."

    trends = list(_state.trends)[-16:] or [
        {
            "label": "now",
            "cpu": _state.cpu_usage,
            "temp": _state.cpu_temp,
            "battery": _state.battery_voltage,
            "odomVelocity": _state.linear_vel,
            "commandVelocity": _state.baseline_vel,
        }
    ]

    logs = list(_state.recent_logs) or [
        {"ts": "now", "level": "warn", "message": "[mission_bridge] Safe-command bridge waiting for ROS telemetry."}
    ]
    terrain = _state.terrain_status or {}
    terrain_grid = _state.terrain_grid
    terrain_grid_status, terrain_grid_age_ms = _stream_status_from_age(
        None if terrain_grid is None else float(terrain_grid.get("last_seen", 0.0))
    )
    flags = (_state.flag_candidates or {}).get("candidates", [])
    best_flag = flags[0] if flags else None
    confidence = float((_state.autonomy_state or {}).get("confidence", 0.35 if connected else 0.0))

    return {
        "mission": {
            "connected": connected,
            "armed": _state.armed,
            "estop": _state.estop,
            "mode": _state.mode,
            "state": _state.mission_state,
            "navigationActive": _state.navigation_active,
            "navigationSteering": _navigation_steering_for_dashboard(),
            "target": "field readiness",
            "heartbeatMs": 0 if connected else None,
            "confidence": confidence,
            "cycle": 0,
            "payload": _state.payload_state,
            "stopReason": _state.stop_reason,
            "lastDecision": _state.last_decision,
            "nextTransition": _state.next_transition,
            "navMission": _nav_mission_for_dashboard(_state.nav_mission_state),
            "digSequence": _dig_sequence_for_dashboard(_state.dig_sequence_state),
        },
        "metrics": [
            {"label": "Linear Vel", "value": f"{_state.linear_vel:.2f} m/s", "detail": "/odom", "status": "ok" if odom_status == "live" else "bad"},
            {"label": "Command Vel", "value": f"{_state.baseline_vel:.2f} m/s", "detail": "cmd/velocity", "status": "idle"},
            {"label": "Battery", "value": f"{_state.battery_voltage:.1f} V" if _state.battery_voltage else "--", "detail": "/sensor/battery", "status": _metric_status_bad_when_zero(_state.battery_voltage)},
            {"label": "CPU", "value": f"{_state.cpu_usage:.0f}%", "detail": f"{_state.cpu_temp:.0f} C", "status": "warn" if _state.cpu_usage > 85 else "ok"},
            {"label": "RAM", "value": f"{_state.ram_usage:.0f}%", "detail": "Jetson host", "status": "warn" if _state.ram_usage > 85 else "ok"},
            {"label": "Point Cloud", "value": f"{_state.point_cloud_points:,}" if _state.point_cloud_points else "--", "detail": "/camera/depth/points", "status": "ok" if depth_status == "live" else "bad"},
            {"label": "Terrain Grid", "value": "ok" if terrain.get("ok") else "--", "detail": f"{terrain.get('obstacle_cells', 0)} obstacles, {terrain.get('caution_cells', 0)} caution", "status": "ok" if terrain.get("ok") else "bad"},
            {"label": "Best Flag", "value": f"{best_flag.get('bearing_deg')} deg" if best_flag else "--", "detail": f"conf {best_flag.get('confidence')}" if best_flag else "no candidate", "status": "ok" if best_flag else "idle"},
        ],
        "topics": topics,
        "cameras": cameras,
        "hardware": [
            {"category": "Compute", "name": "CPU", "status": f"{_state.cpu_usage:.0f}%", "detail": f"{_state.cpu_temp:.0f} C", "severity": "warn" if _state.cpu_usage > 85 else "ok"},
            {"category": "Power", "name": "Battery", "status": f"{_state.battery_voltage:.1f} V" if _state.battery_voltage else "UNKNOWN", "detail": "/sensor/battery", "severity": _metric_status_bad_when_zero(_state.battery_voltage)},
            {"category": "Depth", "name": "/camera/depth/points", "status": depth_status.upper(), "detail": f"{_state.point_cloud_points:,} points" if _state.point_cloud_points else "no samples", "severity": "ok" if depth_status == "live" else "bad"},
            {"category": "Localization", "name": "/odom", "status": odom_status.upper(), "detail": f"x={_state.odom_x:.2f}, y={_state.odom_y:.2f}", "severity": "ok" if odom_status == "live" else "bad"},
            {"category": "Autonomy", "name": "terrain grid", "status": "OK" if terrain.get("ok") else "WAITING", "detail": str(terrain.get("note", "no terrain status")), "severity": "ok" if terrain.get("ok") else "warn"},
            {"category": "Perception", "name": "red/orange flags", "status": "CANDIDATE" if best_flag else "NONE", "detail": f"{len(flags)} candidates", "severity": "ok" if best_flag else "idle"},
        ],
        "zones": [{"id": zone_id, **zone} for zone_id, zone in _state.zones.items()],
        "zoneMarking": {
            "poseFrame": _state.odom_pose_frame_id,
            "odomTopic": "/odom",
            "odomStatus": odom_status,
            "odomAge": odom_age,
            "x": round(float(_state.odom_x), 4),
            "y": round(float(_state.odom_y), 4),
            "yawDeg": round(math.degrees(float(_state.odom_yaw_rad)), 1),
        },
        "logs": logs,
        "trends": trends,
        "sensors": {
            "irLeft": _state.ir_left,
            "irRight": _state.ir_right,
            "encoderLeft": _state.encoder_left,
            "encoderRight": _state.encoder_right,
        },
        "pid": {"kp": 1.0, "ki": 0.0, "kd": 0.1},
        "audit": [
            {"label": "Live bridge", "status": "ok", "detail": "WebSocket snapshot server is running"},
            {"label": "Safe stop command path", "status": "ok", "detail": "ESTOP/pause/manual/drive stop publish zero velocity"},
            {"label": "Teleop drive pulses", "status": "warn", "detail": "forward/reverse/turn are short pulses (~0.35s); use keyboard TUI for sustained hold"},
            {"label": "Localization topic", "status": "ok" if odom_status == "live" else "bad", "detail": _status_for_topic(odom_sample)[1]},
            {"label": "Depth point cloud", "status": "ok" if depth_status == "live" else "bad", "detail": _status_for_topic(depth_sample)[1]},
        ],
        "terrainGrid": {
            "width": int(terrain_grid.get("width", 0)) if terrain_grid else 0,
            "height": int(terrain_grid.get("height", 0)) if terrain_grid else 0,
            "resolution": float(terrain_grid.get("resolution", 0.0)) if terrain_grid else 0.0,
            "frameId": str(terrain_grid.get("frame_id", "base_link")) if terrain_grid else "base_link",
            "ageMs": terrain_grid_age_ms,
            "status": terrain_grid_status,
            "cells": terrain_grid.get("cells", []) if terrain_grid else [],
            "obstacleCells": int(terrain_grid.get("obstacle_cells", 0)) if terrain_grid else 0,
            "cautionCells": int(terrain_grid.get("caution_cells", 0)) if terrain_grid else 0,
            "unknownCells": int(terrain_grid.get("unknown_cells", 0)) if terrain_grid else 0,
            "note": str(terrain.get("note", "no terrain grid")),
        },
        "rawConfig": (
            '[mission_bridge]\n'
            'mode = "operator_bridge"\n'
            f'port = {MISSION_BRIDGE_PORT}\n'
            'command_policy = "safety_bar_teleop_actuators_zone_nav"\n\n'
            '[topics]\n'
            'front_camera = "/camera/rgb/image_compressed"\n'
            'rear_camera = "/camera/rear/image_compressed"\n'
            'depth = "/camera/depth/points"\n'
            'odom = "/odom"\n'
        ),
    }


def _broadcast_snapshot() -> None:
    payload = json.dumps({"kind": "snapshot", "snapshot": build_snapshot()})
    stale = []
    with _clients_lock:
        clients = list(_clients)
    for client in clients:
        try:
            client.write_message(payload)
        except Exception:
            stale.append(client)
    if stale:
        with _clients_lock:
            for client in stale:
                _clients.discard(client)


def _schedule_snapshot() -> None:
    if _io_loop is not None:
        _io_loop.add_callback(_broadcast_snapshot)


def _append_log(level: str, name: str, message: str) -> None:
    _state.recent_logs.append(
        {
            "ts": time.strftime("%H:%M:%S"),
            "level": level,
            "message": f"[{name}] {message}",
        }
    )


def _parse_json_message(data: str) -> Dict[str, Any]:
    try:
        payload = json.loads(data)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _stream_status_from_age(last_seen: float | None) -> tuple[str, int | None]:
    if last_seen is None:
        return "missing", None
    age_ms = int(max(0.0, time.time() - last_seen) * 1000)
    if age_ms > int(MISSING_TOPIC_SEC * 1000):
        return "missing", age_ms
    if age_ms > int(STALE_TOPIC_SEC * 1000):
        return "stale", age_ms
    return "live", age_ms


def _tick_system() -> None:
    now = time.time()
    elapsed = max(0.001, now - _state.last_rate_tick)
    for sample in _state.topics.values():
        sample.rate_hz = max(0.0, (sample.count - sample.last_count) / elapsed)
        sample.last_count = sample.count
    _state.last_rate_tick = now

    _state.cpu_usage = float(psutil.cpu_percent())
    _state.ram_usage = float(psutil.virtual_memory().percent)
    _state.cpu_temp = _get_cpu_temp()
    _state.trends.append(
        {
            "label": f"{int(now - _state.started_at)}s",
            "cpu": _state.cpu_usage,
            "temp": _state.cpu_temp,
            "battery": _state.battery_voltage,
            "odomVelocity": _state.linear_vel,
            "commandVelocity": _state.baseline_vel,
        }
    )
    _schedule_snapshot()


def _drive_scale(speed_limit: float) -> float:
    return max(0.0, min(100.0, float(speed_limit))) / 100.0


def _twist_for_drive(command_name: str, speed_limit: float) -> "Any":
    from geometry_msgs.msg import Twist

    scale = _drive_scale(speed_limit)
    linear = 35.0 * scale
    angular = 35.0 * scale
    msg = Twist()
    if command_name == "forward":
        msg.linear.x = linear
    elif command_name == "reverse":
        msg.linear.x = -linear
    elif command_name == "left":
        msg.angular.z = angular
    elif command_name == "right":
        msg.angular.z = -angular
    return msg


def _run_ros_node() -> None:
    import rclpy
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import OccupancyGrid, Odometry
    from rcl_interfaces.msg import Log
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
    from sensor_msgs.msg import CompressedImage, PointCloud2
    from std_msgs.msg import Bool, Float32, Int16, Int32, String

    from lunar.keyboard_topics import KEYBOARD_PUBLISHER_TOPICS, clamp_pan_angle

    class MissionBridgeNode(Node):
        def __init__(self):
            super().__init__("lunar_mission_control_bridge")
            sensor_qos = QoSProfile(
                depth=3,
                reliability=QoSReliabilityPolicy.BEST_EFFORT,
                history=QoSHistoryPolicy.KEEP_LAST,
                durability=QoSDurabilityPolicy.VOLATILE,
            )
            for topic, note, safety in [
                ("/camera/rgb/image_compressed", "front RGB", False),
                ("/camera/rear/image_compressed", "rear RGB", False),
                ("/camera/depth/points", "depth grid source", True),
                ("/odom", "localization source", True),
                ("/tf", "frame transforms", True),
                ("cmd/velocity", "command echo/watchdog source", True),
            ]:
                _state.ensure_topic(topic, note, safety)

            self.create_subscription(CompressedImage, "/camera/rgb/image_compressed", lambda msg: self.camera_cb("/camera/rgb/image_compressed", msg), sensor_qos)
            self.create_subscription(CompressedImage, "/camera/rear/image_compressed", lambda msg: self.camera_cb("/camera/rear/image_compressed", msg), sensor_qos)
            self.create_subscription(PointCloud2, "/camera/depth/points", self.point_cloud_cb, sensor_qos)
            self.create_subscription(Odometry, "/odom", self.odom_cb, 10)
            self.create_subscription(Twist, "cmd/velocity", self.cmd_vel_cb, 10)
            self.create_subscription(Twist, "/cmd_vel", self.cmd_vel_cb, 10)
            self.create_subscription(Float32, "/sensor/battery", self.battery_cb, 10)
            self.create_subscription(Int16, "/sensor/ir/left", self.ir_left_cb, 10)
            self.create_subscription(Int16, "/sensor/ir/right", self.ir_right_cb, 10)
            self.create_subscription(Int32, "/sensor/encoder/left", self.encoder_left_cb, 10)
            self.create_subscription(Int32, "/sensor/encoder/right", self.encoder_right_cb, 10)
            self.create_subscription(Log, "/rosout", self.log_cb, 10)
            self.create_subscription(OccupancyGrid, "/autonomy/local_terrain_grid", self.terrain_grid_cb, 10)
            self.create_subscription(String, "/autonomy/terrain_status", self.terrain_status_cb, 10)
            self.create_subscription(String, "/perception/flag_candidates", self.flag_candidates_cb, 10)
            self.create_subscription(String, "/autonomy/state", self.autonomy_state_cb, 10)
            self.create_subscription(String, "/autonomy/nav_mission/state", self.nav_mission_state_cb, 10)
            self.create_subscription(String, "/autonomy/dig_sequence/state", self.dig_sequence_state_cb, 10)
            self.create_subscription(String, "/autonomy/navigation_status", self.navigation_status_cb, 10)
            self.pub_velocity = self.create_publisher(Twist, KEYBOARD_PUBLISHER_TOPICS["drive"], 10)
            self.pub_zone_mark = self.create_publisher(String, "/autonomy/zone_mark", 10)
            self.pub_navigation_active = self.create_publisher(Bool, "/autonomy/navigation_active", 10)
            self.pub_autonomy = self.create_publisher(String, "/cmd/autonomy", 10)
            self.pub_pan = self.create_publisher(Int16, KEYBOARD_PUBLISHER_TOPICS["pan"], 10)
            self.pub_camera_height = self.create_publisher(Int16, KEYBOARD_PUBLISHER_TOPICS["camera-height"], 10)
            self.pub_bucket_pos = self.create_publisher(Int16, KEYBOARD_PUBLISHER_TOPICS["bucket-pos"], 10)
            self.pub_bucket_vel = self.create_publisher(Int16, KEYBOARD_PUBLISHER_TOPICS["bucket-vel"], 10)
            self.pub_conveyor = self.create_publisher(Int16, KEYBOARD_PUBLISHER_TOPICS["conveyor"], 10)
            self._drive_stop_timer = None
            self._actuator_step = 5
            self._bucket_vel_mag = 35
            self.create_timer(1.0, _tick_system)
            self.create_timer(0.05, self.process_command_queue)
            self.get_logger().info("Mission control WebSocket bridge initialized")

        def _publish_stop_burst(self):
            stop_msg = Twist()
            for _ in range(5):
                self.pub_velocity.publish(stop_msg)
            _state.baseline_vel = 0.0
            _state.touch_topic("cmd/velocity")

        def _clear_navigation_active(self) -> None:
            _state.navigation_active = False
            m = Bool()
            m.data = False
            self.pub_navigation_active.publish(m)

        def _publish_autonomy(self, command: str) -> None:
            msg = String()
            msg.data = command
            self.pub_autonomy.publish(msg)

        def _publish_int16(self, publisher, value: int) -> None:
            msg = Int16()
            msg.data = int(value)
            publisher.publish(msg)

        def _cancel_drive_stop_timer(self) -> None:
            if self._drive_stop_timer is not None:
                self._drive_stop_timer.cancel()
                self._drive_stop_timer = None

        def _schedule_drive_stop(self) -> None:
            self._cancel_drive_stop_timer()
            self._drive_stop_timer = self.create_timer(0.35, self._drive_stop_once)

        def _drive_stop_once(self) -> None:
            self._cancel_drive_stop_timer()
            self._publish_stop_burst()

        def _publish_drive_pulse(self, command_name: str, speed_limit: float) -> None:
            twist = _twist_for_drive(command_name, speed_limit)
            self.pub_velocity.publish(twist)
            _state.baseline_vel = float(twist.linear.x)
            _state.touch_topic("cmd/velocity")
            self._schedule_drive_stop()

        def _command_result(self, command: QueuedCommand, accepted: bool, message: str) -> None:
            result = {
                "accepted": accepted,
                "message": message,
                "commandId": command.request_id,
            }
            command.reply(result)
            _append_log("info" if accepted else "warn", "mission_bridge", message)
            _schedule_snapshot()

        def process_command_queue(self):
            while True:
                try:
                    queued = _command_queue.get_nowait()
                except queue.Empty:
                    return
                try:
                    self.handle_dashboard_command(queued)
                except Exception as exc:
                    self._command_result(queued, False, f"Command failed in mission bridge: {exc}")

        def handle_dashboard_command(self, queued: QueuedCommand):
            command = queued.command or {}
            command_type = command.get("type")

            if command_type == "estop":
                _state.estop = True
                _state.armed = False
                _state.mode = "Estop"
                _state.mission_state = "ESTOP"
                _state.stop_reason = "Operator ESTOP command accepted by mission bridge."
                _state.last_decision = "Published zero velocity on cmd/velocity."
                _state.next_transition = "Clear ESTOP after physical safety check, then Resume."
                self._cancel_drive_stop_timer()
                self._publish_stop_burst()
                self._publish_autonomy("estop")
                self._clear_navigation_active()
                self._command_result(queued, True, "ESTOP accepted. Published zero velocity burst and /cmd/autonomy estop.")
                return

            if command_type == "clear_estop":
                _state.estop = False
                _state.mode = "Manual"
                _state.mission_state = "PAUSED"
                _state.stop_reason = "ESTOP cleared from dashboard; supervisor reset requested."
                _state.last_decision = "Published /cmd/autonomy reset."
                self._publish_autonomy("reset")
                self._command_result(queued, True, "ESTOP cleared locally. Published /cmd/autonomy reset.")
                return

            if command_type == "manual_takeover":
                _state.armed = False
                _state.mode = "Manual"
                _state.mission_state = "PAUSED"
                _state.stop_reason = "Manual takeover requested by operator."
                _state.last_decision = "Autonomy paused and zero velocity published."
                _state.next_transition = "Operator may teleop after verifying robot state."
                self._cancel_drive_stop_timer()
                self._publish_stop_burst()
                self._publish_autonomy("manual")
                self._clear_navigation_active()
                self._command_result(queued, True, "Manual takeover accepted. Published zero velocity burst.")
                return

            if command_type == "pause_autonomy":
                _state.armed = False
                _state.mode = "Paused"
                _state.mission_state = "PAUSED"
                _state.stop_reason = "Autonomy paused by operator."
                _state.last_decision = "Published zero velocity on pause."
                self._cancel_drive_stop_timer()
                self._publish_stop_burst()
                self._publish_autonomy("pause")
                self._clear_navigation_active()
                self._command_result(queued, True, "Pause accepted. Published zero velocity burst.")
                return

            if command_type == "drive" and command.get("command") == "stop":
                self._cancel_drive_stop_timer()
                _state.armed = False
                _state.mode = "Manual"
                _state.last_decision = "Drive stop command accepted."
                self._publish_stop_burst()
                self._clear_navigation_active()
                self._command_result(queued, True, "Drive stop accepted. Published zero velocity burst.")
                return

            if command_type == "drive":
                if _state.estop:
                    self._command_result(queued, False, "Rejected: ESTOP is active.")
                    return
                drive_cmd = str(command.get("command", ""))
                if drive_cmd not in ("forward", "reverse", "left", "right"):
                    self._command_result(queued, False, f"Rejected unknown drive command: {drive_cmd!r}")
                    return
                speed_limit = float(command.get("speedLimit", 30))
                self._publish_drive_pulse(drive_cmd, speed_limit)
                self._command_result(
                    queued,
                    True,
                    f"Drive {drive_cmd} pulse accepted (~0.35s at {speed_limit:.0f}% scale). Use lunar keyboard for sustained hold.",
                )
                return

            if command_type == "actuator":
                if _state.estop:
                    self._command_result(queued, False, "Rejected: ESTOP is active.")
                    return
                target = str(command.get("target", ""))
                action = str(command.get("action", ""))
                step = int(command.get("step") or self._actuator_step)
                if target == "pan":
                    if action == "increment":
                        _state.pan_angle = clamp_pan_angle(_state.pan_angle + step)
                    elif action == "decrement":
                        _state.pan_angle = clamp_pan_angle(_state.pan_angle - step)
                    elif action == "stop":
                        _state.pan_angle = 0
                    else:
                        self._command_result(queued, False, f"Unsupported pan action: {action}")
                        return
                    self._publish_int16(self.pub_pan, _state.pan_angle)
                    self._command_result(queued, True, f"Pan -> {_state.pan_angle} deg on {KEYBOARD_PUBLISHER_TOPICS['pan']}.")
                    return
                if target == "camera_height":
                    if action == "increment":
                        _state.camera_height = max(0, min(100, _state.camera_height + step))
                    elif action == "decrement":
                        _state.camera_height = max(0, min(100, _state.camera_height - step))
                    elif action == "stop":
                        pass
                    else:
                        self._command_result(queued, False, f"Unsupported camera_height action: {action}")
                        return
                    self._publish_int16(self.pub_camera_height, _state.camera_height)
                    self._command_result(queued, True, f"Camera height -> {_state.camera_height}.")
                    return
                if target == "bucket_pos":
                    if action == "increment":
                        _state.bucket_pos = max(0, min(100, _state.bucket_pos + step))
                    elif action == "decrement":
                        _state.bucket_pos = max(0, min(100, _state.bucket_pos - step))
                    elif action == "stop":
                        pass
                    else:
                        self._command_result(queued, False, f"Unsupported bucket_pos action: {action}")
                        return
                    self._publish_int16(self.pub_bucket_pos, _state.bucket_pos)
                    self._command_result(queued, True, f"Bucket position -> {_state.bucket_pos}.")
                    return
                if target == "bucket_vel":
                    if action == "increment":
                        _state.bucket_vel = self._bucket_vel_mag
                    elif action == "decrement":
                        _state.bucket_vel = -self._bucket_vel_mag
                    elif action == "stop":
                        _state.bucket_vel = 0
                    else:
                        self._command_result(queued, False, f"Unsupported bucket_vel action: {action}")
                        return
                    self._publish_int16(self.pub_bucket_vel, _state.bucket_vel)
                    self._command_result(queued, True, f"Bucket velocity -> {_state.bucket_vel}.")
                    return
                if target == "conveyor":
                    if action == "toggle":
                        _state.conveyor = 0 if _state.conveyor else 1
                    elif action == "stop":
                        _state.conveyor = 0
                    else:
                        self._command_result(queued, False, f"Unsupported conveyor action: {action}")
                        return
                    self._publish_int16(self.pub_conveyor, _state.conveyor)
                    self._command_result(queued, True, f"Conveyor -> {_state.conveyor}.")
                    return
                self._command_result(queued, False, f"Unknown actuator target: {target}")
                return

            if command_type == "set_navigation_active":
                if _state.estop:
                    self._command_result(queued, False, "Rejected: ESTOP is active.")
                    return
                active = bool(command.get("active", False))
                _state.navigation_active = active
                m = Bool()
                m.data = active
                self.pub_navigation_active.publish(m)
                self._command_result(
                    queued,
                    True,
                    f"Published /autonomy/navigation_active = {active}. "
                    "Requires navigation stack and supervisor gates for motion.",
                )
                return

            if command_type == "mark_zone":
                zone_id = str(command.get("zone", ""))
                if zone_id not in _state.zones:
                    self._command_result(queued, False, f"Rejected unknown zone: {zone_id}")
                    return
                pick = command.get("pick") or {}
                frame = str(pick.get("frameId", "") or "").lower()
                lx = float(pick.get("x", 0.0)) if pick else 0.0
                ly = float(pick.get("y", 0.0)) if pick else 0.0
                use_pick = bool(pick) and frame in ("base_link", "")
                if pick and frame not in ("base_link", ""):
                    self._command_result(queued, False, f"Rejected pick frame {frame!r} (only base_link).")
                    return
                yaw = float(_state.odom_yaw_rad)
                if use_pick:
                    mx = float(_state.odom_x) + math.cos(yaw) * lx - math.sin(yaw) * ly
                    my = float(_state.odom_y) + math.sin(yaw) * lx + math.cos(yaw) * ly
                else:
                    mx = float(_state.odom_x)
                    my = float(_state.odom_y)
                _state.zones[zone_id]["status"] = "operator_marked"
                _state.zones[zone_id]["detail"] = (
                    f"odom ({mx:.2f},{my:.2f})" + (f" ← base_link ({lx:.2f},{ly:.2f})" if use_pick else "")
                )
                _state.last_decision = f"Operator marked {zone_id} zone."
                zone_msg = String()
                payload: Dict[str, Any] = {
                    "stamp": time.time(),
                    "zone": zone_id,
                    "source": "operator_dashboard",
                    "odom_x": mx,
                    "odom_y": my,
                }
                if use_pick:
                    payload["pick_base_link"] = {"x": lx, "y": ly}
                zone_msg.data = json.dumps(payload)
                self.pub_zone_mark.publish(zone_msg)
                self._command_result(queued, True, f"Marked {zone_id} at odom ({mx:.2f}, {my:.2f}).")
                return

            if command_type == "resume_autonomy":
                if _state.estop:
                    self._command_result(
                        queued,
                        False,
                        "Rejected: ESTOP is active. Clear ESTOP after a physical safety check, then Resume.",
                    )
                    return
                _state.armed = False
                _state.mode = "Manual"
                _state.stop_reason = "Supervisor reset requested from dashboard."
                _state.last_decision = "Published /cmd/autonomy reset."
                _state.next_transition = "Supervisor re-runs readiness; arm when zones and health allow."
                self._publish_autonomy("reset")
                self._command_result(
                    queued,
                    True,
                    "Resume requested via /cmd/autonomy reset. Motion still gated by supervisor allow_motion.",
                )
                return

            if command_type in ("payload", "pid", "recording", "save_map"):
                self._command_result(
                    queued,
                    False,
                    f"Rejected {command_type}. Use lunar CLI (run dig, nav-dig, keyboard, run session) for payload, bags, maps, and PID.",
                )
                return

            rejected = command_type or "unknown"
            self._command_result(
                queued,
                False,
                f"Rejected unknown command type: {rejected}.",
            )

        def camera_cb(self, topic: str, msg):
            _state.touch_topic(topic)

        def point_cloud_cb(self, msg):
            _state.point_cloud_points = int(msg.width * msg.height)
            _state.touch_topic("/camera/depth/points", width=int(msg.width), height=int(msg.height))

        def odom_cb(self, msg):
            q = msg.pose.pose.orientation
            siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
            cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
            _state.odom_yaw_rad = math.atan2(siny_cosp, cosy_cosp)
            frame = (msg.header.frame_id or "").strip()
            _state.odom_pose_frame_id = frame if frame else "odom"
            _state.odom_x = float(msg.pose.pose.position.x)
            _state.odom_y = float(msg.pose.pose.position.y)
            _state.linear_vel = float(msg.twist.twist.linear.x)
            _state.angular_vel = float(msg.twist.twist.angular.z)
            _state.touch_topic("/odom")
            _schedule_snapshot()

        def cmd_vel_cb(self, msg):
            _state.baseline_vel = float(msg.linear.x)
            _state.touch_topic("cmd/velocity")
            _schedule_snapshot()

        def battery_cb(self, msg):
            _state.battery_voltage = float(msg.data)
            _state.touch_topic("/sensor/battery")

        def ir_left_cb(self, msg):
            _state.ir_left = int(msg.data)

        def ir_right_cb(self, msg):
            _state.ir_right = int(msg.data)

        def encoder_left_cb(self, msg):
            _state.encoder_left = int(msg.data)

        def encoder_right_cb(self, msg):
            _state.encoder_right = int(msg.data)

        def terrain_status_cb(self, msg):
            _state.terrain_status = _parse_json_message(msg.data)
            _schedule_snapshot()

        def terrain_grid_cb(self, msg):
            cells = list(msg.data)
            _state.terrain_grid = {
                "last_seen": time.time(),
                "width": int(msg.info.width),
                "height": int(msg.info.height),
                "resolution": float(msg.info.resolution),
                "frame_id": msg.header.frame_id,
                "cells": cells,
                "obstacle_cells": int(sum(1 for cell in cells if cell >= 90)),
                "caution_cells": int(sum(1 for cell in cells if 1 <= cell < 90)),
                "unknown_cells": int(sum(1 for cell in cells if cell < 0)),
            }
            _schedule_snapshot()

        def flag_candidates_cb(self, msg):
            _state.flag_candidates = _parse_json_message(msg.data)
            _schedule_snapshot()

        def autonomy_state_cb(self, msg):
            _state.autonomy_state = _parse_json_message(msg.data)
            _schedule_snapshot()

        def nav_mission_state_cb(self, msg):
            _state.nav_mission_state = _parse_json_message(msg.data)
            _schedule_snapshot()

        def dig_sequence_state_cb(self, msg):
            _state.dig_sequence_state = _parse_json_message(msg.data)
            _schedule_snapshot()

        def log_cb(self, msg):
            if msg.level < 30:
                return
            level = "error" if msg.level >= 40 else "warn"
            clean_message = re.sub(r"\s+", " ", str(msg.msg)).strip()
            _append_log(level, str(msg.name), clean_message)
            _schedule_snapshot()

    rclpy.init()
    node = MissionBridgeNode()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        executor.remove_node(node)
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def _run_web_server(port: int, host: str) -> None:
    global _io_loop
    asyncio.set_event_loop(asyncio.new_event_loop())
    _io_loop = tornado.ioloop.IOLoop.current()
    app = tornado.web.Application(
        [
            (r"/mission/ws", MissionControlWebSocket),
            (r"/healthz", HealthHandler),
        ]
    )
    app.listen(port, address=host)
    _append_log("warn", "mission_bridge", f"listening on ws://{host}:{port}/mission/ws")
    _io_loop.start()


def _assert_ros_cli_available() -> None:
    try:
        subprocess.run(["ros2", "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("ros2 CLI is not available; source ROS before running mission bridge") from exc


def main(port: int = MISSION_BRIDGE_PORT, host: str = "0.0.0.0") -> None:
    _assert_ros_cli_available()
    ros_thread = threading.Thread(target=_run_ros_node, daemon=True, name="mission-bridge-ros")
    ros_thread.start()
    _run_web_server(port, host)


if __name__ == "__main__":
    main()
