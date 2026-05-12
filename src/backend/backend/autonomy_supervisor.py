import json
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import String

from backend.autonomy_shadow_logic import compute_shadow_tick, parse_autonomy_command


class AutonomySupervisor(Node):
    """
    Shadow-mode mission supervisor for field bring-up.

    It consumes perception/localization/planning readiness signals and publishes
    a mission state. It intentionally does not command autonomous motion yet.
    That keeps the next field test focused on proving sensors and readiness
    before enabling drive control.
    """

    def __init__(self):
        super().__init__("autonomy_supervisor")
        self.declare_parameter("allow_motion", False)
        self.declare_parameter("health_timeout_sec", 2.0)
        self.declare_parameter("terrain_timeout_sec", 2.0)
        self.declare_parameter("flag_timeout_sec", 2.0)

        self.mode = "Manual"
        self.state = "HEALTH_CHECK"
        self._last_published_state = self.state
        self.stop_reason = "Waiting for autonomy health signals."
        self.last_decision = "Shadow supervisor started."
        self.next_transition = "Validate perception health, terrain, localization, and zones."
        self.confidence = 0.0
        self.cycle = 0
        self.payload = "unknown"
        self.zone_marks = {}
        self.odom = None
        self.last_odom_time = None
        self.perception_health = None
        self.terrain_status = None
        self.flag_candidates = None
        self.last_perception_time = None
        self.last_terrain_time = None
        self.last_flag_time = None
        self.paused = False
        self.estop = False

        self.create_subscription(String, "/cmd/autonomy", self._cmd_cb, 10)
        self.create_subscription(String, "/autonomy/perception_health", self._perception_cb, 10)
        self.create_subscription(String, "/autonomy/terrain_status", self._terrain_cb, 10)
        self.create_subscription(String, "/perception/flag_candidates", self._flags_cb, 10)
        self.create_subscription(String, "/autonomy/zone_mark", self._zone_cb, 10)
        self.create_subscription(Odometry, "/odom", self._odom_cb, 10)

        self.pub_state = self.create_publisher(String, "/autonomy/state", 10)
        self.pub_velocity = self.create_publisher(Twist, "cmd/velocity", 10)
        self.create_timer(0.5, self._tick)
        self.get_logger().info("Autonomy supervisor initialized in shadow mode")

    def _cmd_cb(self, msg):
        command = msg.data.strip().lower()
        allow_motion = bool(self.get_parameter("allow_motion").value)
        publish_stop, updates = parse_autonomy_command(command, allow_motion)
        for key, value in updates.items():
            setattr(self, key, value)
        if publish_stop:
            self._publish_stop()

    def _perception_cb(self, msg):
        self.perception_health = self._parse_json(msg.data)
        self.last_perception_time = time.monotonic()

    def _terrain_cb(self, msg):
        self.terrain_status = self._parse_json(msg.data)
        self.last_terrain_time = time.monotonic()

    def _flags_cb(self, msg):
        self.flag_candidates = self._parse_json(msg.data)
        self.last_flag_time = time.monotonic()

    def _zone_cb(self, msg):
        payload = self._parse_json(msg.data)
        zone_id = payload.get("zone")
        if zone_id:
            self.zone_marks[zone_id] = payload

    def _odom_cb(self, msg):
        self.odom = msg
        self.last_odom_time = time.monotonic()

    def _parse_json(self, data):
        try:
            return json.loads(data)
        except Exception:
            return {}

    def _publish_stop(self):
        msg = Twist()
        self.pub_velocity.publish(msg)

    def _tick(self):
        if self.estop:
            self._publish_state()
            return

        now = time.monotonic()
        out = compute_shadow_tick(
            paused=self.paused,
            perception_health=self.perception_health,
            terrain_status=self.terrain_status,
            flag_candidates=self.flag_candidates,
            zone_marks=self.zone_marks,
            last_perception_time=self.last_perception_time,
            last_terrain_time=self.last_terrain_time,
            last_flag_time=self.last_flag_time,
            last_odom_time=self.last_odom_time,
            now_mono=now,
            health_timeout_sec=float(self.get_parameter("health_timeout_sec").value),
            terrain_timeout_sec=float(self.get_parameter("terrain_timeout_sec").value),
            flag_timeout_sec=float(self.get_parameter("flag_timeout_sec").value),
        )
        self.confidence = out["confidence"]
        self.state = out["state"]
        self.mode = out["mode"]
        self.last_decision = out["last_decision"]
        self.next_transition = out["next_transition"]
        if "stop_reason" in out:
            self.stop_reason = out["stop_reason"]

        self._publish_state()

    def _publish_state(self):
        if self._last_published_state != self.state:
            self.cycle += 1
            self._last_published_state = self.state

        msg = String()
        msg.data = json.dumps(
            {
                "stamp": time.time(),
                "mode": self.mode,
                "state": self.state,
                "armed": bool(self.get_parameter("allow_motion").value) and self.mode == "Auto",
                "estop": self.estop,
                "confidence": self.confidence,
                "cycle": self.cycle,
                "payload": self.payload,
                "stop_reason": self.stop_reason,
                "last_decision": self.last_decision,
                "next_transition": self.next_transition,
                "zones": self.zone_marks,
            }
        )
        self.pub_state.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = AutonomySupervisor()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
