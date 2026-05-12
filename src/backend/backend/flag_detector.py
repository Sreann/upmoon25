import json
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String

from backend.flag_detection_math import detect_red_orange_flags


class FlagDetector(Node):
    """
    Detects red/orange dump-zone flag candidates using inspectable HSV thresholds.

    This is the field-debuggable baseline. Model-based detection can be added
    later, but the autonomy stack should first have a fast color detector with
    clear confidence and bearing outputs.
    """

    def __init__(self):
        super().__init__("flag_detector")
        self.declare_parameter("image_topic", "/camera/rgb/image_compressed")
        self.declare_parameter("horizontal_fov_deg", 69.0)
        self.declare_parameter("min_area_px", 180.0)
        self.declare_parameter("max_candidates", 5)

        sensor_qos = QoSProfile(
            depth=3,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        image_topic = str(self.get_parameter("image_topic").value)
        self.create_subscription(CompressedImage, image_topic, self._image_cb, sensor_qos)
        self.pub_candidates = self.create_publisher(String, "/perception/flag_candidates", 10)
        self.get_logger().info(f"Flag detector initialized on {image_topic}")

    def _image_cb(self, msg):
        frame = cv2.imdecode(np.frombuffer(msg.data, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return

        height, width = frame.shape[:2]
        candidates = detect_red_orange_flags(
            frame,
            horizontal_fov_deg=float(self.get_parameter("horizontal_fov_deg").value),
            min_area_px=float(self.get_parameter("min_area_px").value),
            max_candidates=int(self.get_parameter("max_candidates").value),
        )
        payload = {
            "stamp": time.time(),
            "image_topic": str(self.get_parameter("image_topic").value),
            "image_width": width,
            "image_height": height,
            "candidates": candidates,
        }
        out = String()
        out.data = json.dumps(payload)
        self.pub_candidates.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = FlagDetector()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
