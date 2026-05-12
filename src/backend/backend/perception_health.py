import json
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import CompressedImage, PointCloud2
from std_msgs.msg import String


class PerceptionHealth(Node):
    """
    Publishes a compact health summary for autonomy-critical perception topics.

    This is intentionally independent from the dashboard. The dashboard can show
    it, but autonomy can also consume it directly to decide whether it is allowed
    to move.
    """

    def __init__(self):
        super().__init__("perception_health")
        sensor_qos = QoSProfile(
            depth=3,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            durability=QoSDurabilityPolicy.VOLATILE,
        )

        self.declare_parameter("stale_seconds", 1.0)
        self.declare_parameter("missing_seconds", 3.0)

        self.samples = {
            "/camera/rgb/image_compressed": self._sample("front RGB", False),
            "/camera/rear/image_compressed": self._sample("rear RGB", False),
            "/camera/depth/points": self._sample("depth point cloud", True),
            "/odom": self._sample("localization", True),
            "cmd/velocity": self._sample("command echo", True),
        }

        self.create_subscription(
            CompressedImage,
            "/camera/rgb/image_compressed",
            lambda msg: self._touch("/camera/rgb/image_compressed", width=0, height=0),
            sensor_qos,
        )
        self.create_subscription(
            CompressedImage,
            "/camera/rear/image_compressed",
            lambda msg: self._touch("/camera/rear/image_compressed", width=0, height=0),
            sensor_qos,
        )
        self.create_subscription(PointCloud2, "/camera/depth/points", self._depth_cb, sensor_qos)
        self.create_subscription(Odometry, "/odom", lambda msg: self._touch("/odom"), 10)
        self.create_subscription(Twist, "cmd/velocity", lambda msg: self._touch("cmd/velocity"), 10)

        self.pub_health = self.create_publisher(String, "/autonomy/perception_health", 10)
        self.create_timer(0.5, self._publish)
        self.get_logger().info("Perception health monitor initialized")

    def _sample(self, note, safety_critical):
        return {
            "note": note,
            "safety_critical": safety_critical,
            "last_seen": None,
            "count": 0,
            "last_count": 0,
            "rate_hz": 0.0,
            "point_count": 0,
            "last_rate_tick": time.monotonic(),
        }

    def _touch(self, topic, *, width=None, height=None):
        sample = self.samples[topic]
        sample["last_seen"] = time.monotonic()
        sample["count"] += 1
        if width is not None and height is not None:
            sample["point_count"] = int(width * height)

    def _depth_cb(self, msg):
        self._touch("/camera/depth/points", width=msg.width, height=msg.height)

    def _topic_status(self, sample):
        stale_seconds = float(self.get_parameter("stale_seconds").value)
        missing_seconds = float(self.get_parameter("missing_seconds").value)
        if sample["last_seen"] is None:
            return "missing", None
        age = time.monotonic() - sample["last_seen"]
        if age > missing_seconds:
            return "missing", age
        if age > stale_seconds:
            return "stale", age
        return "live", age

    def _update_rates(self):
        now = time.monotonic()
        for sample in self.samples.values():
            elapsed = max(0.001, now - sample["last_rate_tick"])
            sample["rate_hz"] = (sample["count"] - sample["last_count"]) / elapsed
            sample["last_count"] = sample["count"]
            sample["last_rate_tick"] = now

    def _publish(self):
        self._update_rates()
        topics = []
        safety_ok = True
        for topic, sample in self.samples.items():
            status, age = self._topic_status(sample)
            if sample["safety_critical"] and status != "live":
                safety_ok = False
            topics.append(
                {
                    "topic": topic,
                    "status": status,
                    "age_sec": None if age is None else round(age, 3),
                    "rate_hz": round(sample["rate_hz"], 2),
                    "note": sample["note"],
                    "safety_critical": sample["safety_critical"],
                    "point_count": sample["point_count"],
                }
            )

        msg = String()
        msg.data = json.dumps(
            {
                "stamp": time.time(),
                "safety_ok": safety_ok,
                "topics": topics,
            }
        )
        self.pub_health.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = PerceptionHealth()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
