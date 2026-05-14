"""
Start→dig nav mission executor (ROS 2).

Phases (see ``NavMissionPhase``): map spin → head sweep → corridor follow to dig
zone → handoff (nav controller disabled for dig autonomy).

**Testing**
  1. Run ``autonomy_supervisor``, ``local_terrain_grid``, ``navigation_controller``
     with ``use_zone_goal:=true`` ``zone_goal_id:=dig`` ``goal_preference:=zone``.
  2. Mark dig zone (``/autonomy/zone_mark`` with ``odom_x``/``odom_y``).
  3. ``ros2 topic pub --once /autonomy/nav_mission/command std_msgs/String \"data: start\"``

Executor publishes ``/autonomy/nav_mission/state`` (JSON), ``/autonomy/nav_mission_twist``,
optional ``/cmd/pan``, ``/autonomy/dig_arm`` (Bool) at dig handoff, and latches
``/autonomy/navigation_active`` only while a mission is armed.

Mission bridge may also publish ``/autonomy/navigation_active`` — during scripted tests,
avoid toggling nav from the dashboard, or last-writer wins.
"""

from __future__ import annotations

import json
import math
import time
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.node import Node
from std_msgs.msg import Bool, Int16, String

from backend.nav_mission_pure import dig_zone_has_pose, distance_to_zone_m, unknown_cell_fraction


class NavMissionPhase(str, Enum):
    IDLE = "IDLE"
    MAP_EXPLORE = "MAP_EXPLORE"
    HEAD_SWEEP = "HEAD_SWEEP"
    BACKUP_RECOVER = "BACKUP_RECOVER"
    FOLLOW_TO_DIG = "FOLLOW_TO_DIG"
    AT_DIG_HANDOFF = "AT_DIG_HANDOFF"
    COMPLETE = "COMPLETE"
    ABORTED = "ABORTED"


def _parse_json(data: str) -> Dict[str, Any]:
    try:
        out = json.loads(data)
        return out if isinstance(out, dict) else {}
    except json.JSONDecodeError:
        return {}


class NavMissionExecutor(Node):
    def __init__(self) -> None:
        super().__init__("nav_mission_executor")

        self.declare_parameter("dig_zone_id", "dig")
        self.declare_parameter("at_dig_distance_m", 0.38)
        self.declare_parameter("at_dig_hold_sec", 0.45)
        self.declare_parameter("explore_duration_sec", 5.0)
        self.declare_parameter("explore_angular_z", 0.32)
        self.declare_parameter("explore_unknown_max", 0.34)
        self.declare_parameter("head_sweep_deg", [-35, 0, 35, 0])
        self.declare_parameter("head_sweep_dwell_sec", 1.1)
        self.declare_parameter("publish_cmd_pan", True)
        self.declare_parameter("publish_navigation_active", True)
        self.declare_parameter("backup_linear_x", -0.12)
        self.declare_parameter("backup_duration_sec", 0.55)
        self.declare_parameter("follow_stuck_dist_window_m", 0.02)
        self.declare_parameter("follow_stuck_time_sec", 4.5)
        self.declare_parameter("mission_state_hz", 10.0)
        self.declare_parameter("publish_dig_arm", True)

        self._phase = NavMissionPhase.IDLE
        self._phase_started = time.monotonic()
        self._mission_armed = False
        self._at_dig_accum = 0.0
        self._last_tick = time.monotonic()
        self._follow_last_dist: Optional[float] = None
        self._follow_stuck_since: Optional[float] = None

        self._odom: Optional[Odometry] = None
        self._autonomy: Dict[str, Any] = {}
        self._grid: Optional[np.ndarray] = None
        self._grid_mono: Optional[float] = None

        self.pub_state = self.create_publisher(String, "/autonomy/nav_mission/state", 10)
        self.pub_twist = self.create_publisher(Twist, "/autonomy/nav_mission_twist", 10)
        self.pub_pan = self.create_publisher(Int16, "/cmd/pan", 10)
        self.pub_nav_active = self.create_publisher(Bool, "/autonomy/navigation_active", 10)
        self.pub_dig_arm = self.create_publisher(Bool, "/autonomy/dig_arm", 10)
        self._dig_arm_out: Optional[bool] = None

        self.create_subscription(String, "/autonomy/nav_mission/command", self._cmd_cb, 10)
        self.create_subscription(String, "/autonomy/state", self._state_cb, 10)
        self.create_subscription(Odometry, "/odom", self._odom_cb, 10)
        self.create_subscription(OccupancyGrid, "/autonomy/local_terrain_grid", self._grid_cb, 10)

        hz = float(self.get_parameter("mission_state_hz").value)
        hz = max(2.0, min(50.0, hz))
        self.create_timer(1.0 / hz, self._tick)
        self.get_logger().info("nav_mission_executor ready; pub /autonomy/nav_mission/state")

    def _dig_zone(self) -> str:
        return str(self.get_parameter("dig_zone_id").value)

    def _zones(self) -> Dict[str, Any]:
        z = self._autonomy.get("zones")
        return z if isinstance(z, dict) else {}

    def _cmd_cb(self, msg: String) -> None:
        cmd = msg.data.strip().lower()
        if cmd in {"abort", "stop", "cancel"}:
            self._abort("operator_command")
            return
        if cmd == "reset":
            self._hard_reset()
            return
        if cmd == "start":
            self._try_start()

    def _try_start(self) -> None:
        if self._mission_armed and self._phase not in (
            NavMissionPhase.COMPLETE,
            NavMissionPhase.ABORTED,
            NavMissionPhase.IDLE,
        ):
            self.get_logger().warn("start ignored: mission already running")
            return
        zones = self._zones()
        if not dig_zone_has_pose(zones, self._dig_zone()):
            self.get_logger().error("start rejected: dig zone missing odom_x/odom_y in /autonomy/state zones")
            self._set_dig_arm(False)
            self._publish_phase(NavMissionPhase.ABORTED, "missing_dig_zone", controller_mode="idle")
            return
        if self._autonomy.get("estop"):
            self.get_logger().warn("start rejected: estop active")
            return
        self._set_dig_arm(False)
        self._mission_armed = True
        self._phase = NavMissionPhase.MAP_EXPLORE
        self._phase_started = time.monotonic()
        self._at_dig_accum = 0.0
        self._follow_last_dist = None
        self._follow_stuck_since = None
        self.get_logger().info("nav mission started → MAP_EXPLORE")

    def _abort(self, reason: str) -> None:
        self.get_logger().warn(f"nav mission abort: {reason}")
        self._mission_armed = False
        self._set_dig_arm(False)
        self._publish_nav_active(False)
        self._publish_twist(Twist())
        self._publish_phase(NavMissionPhase.ABORTED, reason, controller_mode="idle")
        self._phase = NavMissionPhase.IDLE

    def _hard_reset(self) -> None:
        self._mission_armed = False
        self._set_dig_arm(False)
        self._phase = NavMissionPhase.IDLE
        self._publish_nav_active(False)
        self._publish_twist(Twist())
        self._publish_phase(NavMissionPhase.IDLE, "reset", controller_mode="idle")

    def _state_cb(self, msg: String) -> None:
        self._autonomy = _parse_json(msg.data)

    def _odom_cb(self, msg: Odometry) -> None:
        self._odom = msg

    def _grid_cb(self, msg: OccupancyGrid) -> None:
        if msg.info.width <= 0 or msg.info.height <= 0:
            return
        try:
            arr = np.asarray(msg.data, dtype=np.int8).reshape((msg.info.height, msg.info.width), order="C")
        except ValueError:
            return
        self._grid = arr
        self._grid_mono = time.monotonic()

    def _publish_nav_active(self, active: bool) -> None:
        if not bool(self.get_parameter("publish_navigation_active").value):
            return
        m = Bool()
        m.data = bool(active)
        self.pub_nav_active.publish(m)

    def _set_dig_arm(self, active: bool) -> None:
        if not bool(self.get_parameter("publish_dig_arm").value):
            return
        b = bool(active)
        if self._dig_arm_out == b:
            return
        self._dig_arm_out = b
        msg = Bool()
        msg.data = b
        self.pub_dig_arm.publish(msg)

    def _publish_twist(self, t: Twist) -> None:
        self.pub_twist.publish(t)

    def _publish_pan_deg(self, deg: int) -> None:
        if not bool(self.get_parameter("publish_cmd_pan").value):
            return
        self.pub_pan.publish(Int16(data=int(max(-90, min(90, deg)))))

    def _robot_xy(self) -> Optional[tuple[float, float]]:
        if self._odom is None:
            return None
        p = self._odom.pose.pose.position
        return float(p.x), float(p.y)

    def _elapsed_phase(self) -> float:
        return time.monotonic() - self._phase_started

    def _advance(self, next_phase: NavMissionPhase) -> None:
        self._phase = next_phase
        self._phase_started = time.monotonic()
        self.get_logger().info(f"nav mission → {next_phase.value}")

    def _publish_phase(
        self,
        phase: NavMissionPhase,
        detail: str,
        *,
        controller_mode: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "stamp": time.time(),
            "phase": phase.value,
            "controller_mode": controller_mode,
            "detail": detail,
            "dig_autonomy_enabled": phase == NavMissionPhase.AT_DIG_HANDOFF,
            "nav_controller_corridor_enabled": controller_mode == "corridor_follow",
        }
        if extra:
            payload.update(extra)
        m = String()
        m.data = json.dumps(payload)
        self.pub_state.publish(m)

    def _tick(self) -> None:
        now = time.monotonic()
        dt = now - self._last_tick
        self._last_tick = now

        if self._autonomy.get("estop") or str(self._autonomy.get("mode", "")) == "Paused":
            if self._mission_armed:
                self._abort("estop_or_pause")
            return

        twist = Twist()
        controller_mode = "idle"
        detail = ""

        if self._phase == NavMissionPhase.IDLE:
            self._publish_nav_active(False)
            self._publish_twist(twist)
            self._publish_phase(NavMissionPhase.IDLE, "idle", controller_mode="idle")
            return

        if self._phase == NavMissionPhase.ABORTED:
            self._publish_nav_active(False)
            self._publish_twist(twist)
            return

        if self._phase == NavMissionPhase.COMPLETE:
            self._set_dig_arm(False)
            self._publish_nav_active(False)
            self._publish_twist(twist)
            self._publish_phase(NavMissionPhase.COMPLETE, "complete", controller_mode="idle")
            return

        zones = self._zones()
        rx, ry = (0.0, 0.0)
        xy = self._robot_xy()
        if xy is not None:
            rx, ry = xy
        dig_dist = distance_to_zone_m(rx, ry, zones, self._dig_zone())

        unk = unknown_cell_fraction(self._grid) if self._grid is not None else 1.0

        if self._phase == NavMissionPhase.MAP_EXPLORE:
            controller_mode = "mission_twist"
            twist.angular.z = float(self.get_parameter("explore_angular_z").value)
            detail = "in_place_spin_for_local_grid"
            t_max = float(self.get_parameter("explore_duration_sec").value)
            unk_max = float(self.get_parameter("explore_unknown_max").value)
            if self._elapsed_phase() >= t_max or unk <= unk_max:
                self._advance(NavMissionPhase.HEAD_SWEEP)
                return

        elif self._phase == NavMissionPhase.HEAD_SWEEP:
            controller_mode = "mission_twist"
            detail = "head_sweep"
            sweep = list(self.get_parameter("head_sweep_deg").value)
            dwell = float(self.get_parameter("head_sweep_dwell_sec").value)
            if not sweep or dwell <= 0.05:
                self._advance(NavMissionPhase.FOLLOW_TO_DIG)
                return
            elapsed = self._elapsed_phase()
            step = int(elapsed // dwell)
            if step >= len(sweep):
                self._advance(NavMissionPhase.FOLLOW_TO_DIG)
                return
            self._publish_pan_deg(int(sweep[step]))

        elif self._phase == NavMissionPhase.BACKUP_RECOVER:
            controller_mode = "mission_twist"
            twist.linear.x = float(self.get_parameter("backup_linear_x").value)
            detail = "backup_recover"
            if self._elapsed_phase() >= float(self.get_parameter("backup_duration_sec").value):
                self._advance(NavMissionPhase.FOLLOW_TO_DIG)
                self._follow_last_dist = dig_dist
                self._follow_stuck_since = None
                return

        elif self._phase == NavMissionPhase.FOLLOW_TO_DIG:
            controller_mode = "corridor_follow"
            detail = "follow_zone_goal"
            self._publish_nav_active(True)
            # stuck detection: distance not closing
            if dig_dist is not None and math.isfinite(dig_dist):
                if self._follow_last_dist is not None and dig_dist is not None:
                    if abs(self._follow_last_dist - dig_dist) < float(
                        self.get_parameter("follow_stuck_dist_window_m").value
                    ):
                        if self._follow_stuck_since is None:
                            self._follow_stuck_since = now
                        elif (now - self._follow_stuck_since) > float(
                            self.get_parameter("follow_stuck_time_sec").value
                        ):
                            self._publish_nav_active(False)
                            self._advance(NavMissionPhase.BACKUP_RECOVER)
                            self._follow_stuck_since = None
                            self._follow_last_dist = dig_dist
                            return
                    else:
                        self._follow_stuck_since = None
                self._follow_last_dist = dig_dist

            hold = float(self.get_parameter("at_dig_hold_sec").value)
            thr = float(self.get_parameter("at_dig_distance_m").value)
            if dig_dist is not None and dig_dist <= thr:
                self._at_dig_accum += dt
                if self._at_dig_accum >= hold:
                    self._publish_nav_active(False)
                    self._advance(NavMissionPhase.AT_DIG_HANDOFF)
                    self._at_dig_accum = 0.0
                    return
            else:
                self._at_dig_accum = 0.0

        elif self._phase == NavMissionPhase.AT_DIG_HANDOFF:
            controller_mode = "none"
            detail = "dig_autonomy_takeover"
            self._set_dig_arm(True)
            self._publish_nav_active(False)
            self._publish_twist(Twist())
            self._publish_phase(
                NavMissionPhase.AT_DIG_HANDOFF,
                detail,
                controller_mode=controller_mode,
                extra={"hint": "Run dig_sequence or manual dig; nav mission corridor disabled."},
            )
            if self._elapsed_phase() >= 0.35:
                self._advance(NavMissionPhase.COMPLETE)
                self._mission_armed = False
            return

        extra: Dict[str, Any] = {"unknown_fraction": unk}
        if dig_dist is not None:
            extra["dig_distance_m"] = dig_dist
        self._publish_twist(twist)
        self._publish_phase(self._phase, detail, controller_mode=controller_mode, extra=extra)

        if self._phase not in (NavMissionPhase.FOLLOW_TO_DIG,):
            self._publish_nav_active(False)


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = NavMissionExecutor()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
