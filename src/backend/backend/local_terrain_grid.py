import json
import math
import time

import numpy as np
import rclpy
from geometry_msgs.msg import Quaternion
from nav_msgs.msg import MapMetaData, OccupancyGrid
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Header, String
from tf2_ros import Buffer, TransformException, TransformListener

from backend.terrain_grid_math import classify_local_terrain, resolve_grid_config, summarize_grid

try:
    import sensor_msgs_py.point_cloud2 as pc2
except Exception:
    pc2 = None


def _yaw_quaternion(yaw):
    q = Quaternion()
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


def _rotate_points(points, quat):
    qx, qy, qz, qw = quat.x, quat.y, quat.z, quat.w
    x, y, z = points[:, 0], points[:, 1], points[:, 2]

    # Quaternion vector rotation, expanded to avoid extra dependencies.
    tx = 2.0 * (qy * z - qz * y)
    ty = 2.0 * (qz * x - qx * z)
    tz = 2.0 * (qx * y - qy * x)

    rx = x + qw * tx + (qy * tz - qz * ty)
    ry = y + qw * ty + (qz * tx - qx * tz)
    rz = z + qw * tz + (qx * ty - qy * tx)
    return np.stack([rx, ry, rz], axis=1)


class LocalTerrainGrid(Node):
    """
    Builds a robot-relative 2D traversability grid from depth points.

    Occupancy values:
    - -1 unknown
    - 0 likely traversable
    - 60 caution/drop risk
    - 100 obstacle
    """

    def __init__(self):
        super().__init__("local_terrain_grid")
        self.declare_parameter("point_topic", "/camera/depth/points")
        self.declare_parameter("target_frame", "base_link")
        self.declare_parameter("grid_preset", "standard")
        self.declare_parameter("forward_m", 0.0)
        self.declare_parameter("width_m", 0.0)
        self.declare_parameter("resolution_m", 0.0)
        self.declare_parameter("ground_min_z", -0.35)
        self.declare_parameter("ground_max_z", 0.25)
        self.declare_parameter("obstacle_z", 0.28)
        self.declare_parameter("drop_z", -0.45)
        self.declare_parameter("max_points", 20000)

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        sensor_qos = QoSProfile(
            depth=2,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        self.create_subscription(PointCloud2, str(self.get_parameter("point_topic").value), self._points_cb, sensor_qos)
        self.pub_grid = self.create_publisher(OccupancyGrid, "/autonomy/local_terrain_grid", 10)
        self.pub_status = self.create_publisher(String, "/autonomy/terrain_status", 10)
        self.get_logger().info("Local terrain grid initialized")

    def _grid_config(self):
        forward = float(self.get_parameter("forward_m").value)
        width = float(self.get_parameter("width_m").value)
        resolution = float(self.get_parameter("resolution_m").value)
        return resolve_grid_config(
            self.get_parameter("grid_preset").value,
            None if forward <= 0 else forward,
            None if width <= 0 else width,
            None if resolution <= 0 else resolution,
        )

    def _points_to_numpy(self, msg):
        if pc2 is None:
            raise RuntimeError("sensor_msgs_py.point_cloud2 is not available")
        points = []
        max_points = int(self.get_parameter("max_points").value)
        for index, point in enumerate(pc2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True)):
            if index >= max_points:
                break
            points.append((float(point[0]), float(point[1]), float(point[2])))
        if not points:
            return np.empty((0, 3), dtype=np.float32)
        return np.asarray(points, dtype=np.float32)

    def _transform_to_base(self, points, msg):
        target_frame = str(self.get_parameter("target_frame").value)
        source_frame = msg.header.frame_id or target_frame
        if source_frame == target_frame:
            return points, True, "already in target frame"
        try:
            tf = self.tf_buffer.lookup_transform(
                target_frame,
                source_frame,
                msg.header.stamp,
                timeout=Duration(seconds=0.1),
            )
        except TransformException as exc:
            return points, False, str(exc)

        rotated = _rotate_points(points, tf.transform.rotation)
        translation = tf.transform.translation
        rotated[:, 0] += translation.x
        rotated[:, 1] += translation.y
        rotated[:, 2] += translation.z
        return rotated, True, f"{source_frame}->{target_frame}"

    def _points_cb(self, msg):
        started = time.monotonic()
        try:
            points = self._points_to_numpy(msg)
            points, tf_ok, tf_note = self._transform_to_base(points, msg)
        except Exception as exc:
            self._publish_status(False, str(exc), 0, 0, 0, 0.0)
            return

        config = self._grid_config()
        forward_m = config["forward_m"]
        width_m = config["width_m"]
        resolution_m = config["resolution_m"]
        grid_w = max(1, int(width_m / resolution_m))
        grid_h = max(1, int(forward_m / resolution_m))

        grid = np.full((grid_h, grid_w), -1, dtype=np.int8)
        if not tf_ok or points.size == 0:
            self._publish_grid(grid, resolution_m, width_m)
            self._publish_status(False, tf_note, int(points.shape[0]), 0, 0, time.monotonic() - started)
            return

        in_bounds = points[
            (points[:, 0] >= 0.0)
            & (points[:, 0] <= forward_m)
            & (points[:, 1] >= -width_m / 2.0)
            & (points[:, 1] <= width_m / 2.0)
        ]

        if in_bounds.size == 0:
            self._publish_grid(grid, resolution_m, width_m)
            self._publish_status(False, "no points inside local grid", int(points.shape[0]), 0, 0, time.monotonic() - started)
            return

        grid = classify_local_terrain(
            points,
            forward_m=forward_m,
            width_m=width_m,
            resolution_m=resolution_m,
            ground_min_z=float(self.get_parameter("ground_min_z").value),
            ground_max_z=float(self.get_parameter("ground_max_z").value),
            obstacle_z=float(self.get_parameter("obstacle_z").value),
            drop_z=float(self.get_parameter("drop_z").value),
        )
        summary = summarize_grid(grid)
        self._publish_grid(grid, resolution_m, width_m)
        self._publish_status(
            True,
            f"{tf_note}; preset={self.get_parameter('grid_preset').value}; res={resolution_m:.2f}m",
            int(points.shape[0]),
            summary["obstacle_cells"],
            summary["caution_cells"],
            time.monotonic() - started,
            unknown_count=summary["unknown_cells"],
        )

    def _publish_grid(self, grid, resolution_m, width_m):
        msg = OccupancyGrid()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = str(self.get_parameter("target_frame").value)
        msg.info = MapMetaData()
        msg.info.resolution = float(resolution_m)
        msg.info.width = int(grid.shape[1])
        msg.info.height = int(grid.shape[0])
        msg.info.origin.position.x = 0.0
        msg.info.origin.position.y = -float(width_m) / 2.0
        msg.info.origin.position.z = 0.0
        msg.info.origin.orientation = _yaw_quaternion(0.0)
        msg.data = grid.flatten(order="C").astype(np.int8).tolist()
        self.pub_grid.publish(msg)

    def _publish_status(self, ok, note, point_count, obstacle_count, caution_count, latency_sec, unknown_count=0):
        msg = String()
        msg.data = json.dumps(
            {
                "stamp": time.time(),
                "ok": bool(ok),
                "note": note,
                "point_count": int(point_count),
                "obstacle_cells": int(obstacle_count),
                "caution_cells": int(caution_count),
                "unknown_cells": int(unknown_count),
                "latency_ms": round(latency_sec * 1000.0, 1),
            }
        )
        self.pub_status.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = LocalTerrainGrid()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
