"""
Projects ``sensor_msgs/PointCloud2`` depth into ``map`` and publishes ``nav_msgs/OccupancyGrid``.

This node performs **2.5D height stamping** into a fixed world frame. It is **not** pose SLAM:
you must supply a consistent TF tree (``map`` → ``odom`` → sensor frames).

Publishes ``/map/global`` with ``nav_msgs`` row-major cell ordering (``index = iy * width + ix``).
"""

from __future__ import annotations

import threading
from typing import List, Optional, Tuple

import numpy as np
import quaternion
import rclpy
import tf2_ros
from geometry_msgs.msg import ColorRGBA, Point, Pose, Quaternion
from nav_msgs.msg import MapMetaData, OccupancyGrid
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node, QoSProfile
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Float32, Header, Int8
from visualization_msgs.msg import Marker

from backend.global_mapper_tf import transform_points_xyz_to_map
from backend.occupancy_grid_codec import encode_cell_grid_xy_to_ros_data
from backend.robot_footprint import FIELD_ARENA_GRID_EXTENT_M


class GlobalMapper(Node):
    def __init__(self):
        super().__init__("mapper")

        # --- QoS ---
        self.QOS = QoSProfile(
            depth=3,
            reliability=2,  # Best effort
            history=1,
            durability=2,  # Volatile
        )
        self.NAV_QOS = QoSProfile(
            depth=1,
            reliability=1,  # Reliable
            history=1,
            durability=1,  # Transient local
        )

        # --- Parameters ---
        self.declare_parameter("use_sim_data", True)
        self.declare_parameter("map_on", True)
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("default_point_cloud_frame", "depth_link_optical")

        self.declare_parameter("point_cloud_topic", "/camera/depth/points")
        self.declare_parameter("map_topic", "/map/global")
        self.declare_parameter("marker_topic", "/map_marker")

        self.declare_parameter("publish_period_s", 0.5)
        self.declare_parameter("grid_extent_m", FIELD_ARENA_GRID_EXTENT_M)
        self.declare_parameter("resolution_cpm", 25.0)  # cells per meter (pixels per meter legacy name)

        self.declare_parameter("point_z_top_m", 5.0)
        self.declare_parameter("point_z_bottom_m", -2.0)
        self.declare_parameter("min_range_m", 0.05)
        self.declare_parameter("max_range_m", 8.0)

        self.declare_parameter("pit_z_threshold_m", -0.8)
        self.declare_parameter("protrusion_z_threshold_m", -0.1)

        self.declare_parameter("max_points_per_cloud", 40000)
        self.declare_parameter("tf_timeout_s", 0.5)
        self.declare_parameter("enable_debug_logging", False)
        self.declare_parameter("publish_mode", "occupancy")  # occupancy | height_debug

        self.use_sim_data = bool(self.get_parameter("use_sim_data").value)
        self.map_on = bool(self.get_parameter("map_on").value)
        self.map_frame = str(self.get_parameter("map_frame").value)
        self.default_point_cloud_frame = str(self.get_parameter("default_point_cloud_frame").value)

        self._point_topic = str(self.get_parameter("point_cloud_topic").value)
        self._map_topic = str(self.get_parameter("map_topic").value)
        self._marker_topic = str(self.get_parameter("marker_topic").value)

        self._publish_period_s = float(self.get_parameter("publish_period_s").value)
        self._grid_extent_m = float(self.get_parameter("grid_extent_m").value)
        self._resolution_cpm = float(self.get_parameter("resolution_cpm").value)

        self._z_top = float(self.get_parameter("point_z_top_m").value)
        self._z_bottom = float(self.get_parameter("point_z_bottom_m").value)
        self._min_range = float(self.get_parameter("min_range_m").value)
        self._max_range = float(self.get_parameter("max_range_m").value)

        self._pit_z = float(self.get_parameter("pit_z_threshold_m").value)
        self._protrusion_z = float(self.get_parameter("protrusion_z_threshold_m").value)

        self._max_points = int(self.get_parameter("max_points_per_cloud").value)
        self._tf_timeout_s = float(self.get_parameter("tf_timeout_s").value)
        self._debug = bool(self.get_parameter("enable_debug_logging").value)
        self._publish_mode = str(self.get_parameter("publish_mode").value).strip().lower()

        self.tf_buffer = tf2_ros.Buffer()
        tf2_ros.TransformListener(self.tf_buffer, self)

        self.grid_resolution = max(1e-3, self._resolution_cpm)
        extent = max(1.0, self._grid_extent_m)
        self.grid_x = int(round(extent * self.grid_resolution))
        self.grid_y = int(round(extent * self.grid_resolution))

        self.grid = np.zeros((self.grid_x, self.grid_y), dtype=np.float32)
        self.obstacle_map = np.full((self.grid_x, self.grid_y), -1.0, dtype=np.float32)

        self._lock = threading.Lock()
        self._rng = np.random.default_rng()

        self.update = True
        self.robot_z = 0.0

        sub_group = MutuallyExclusiveCallbackGroup()

        self.create_subscription(
            PointCloud2,
            self._point_topic,
            callback=self.handle_depth,
            qos_profile=self.QOS,
            callback_group=sub_group,
        )
        self.create_subscription(Int8, "/cmd_map", callback=self.handle_cmd, qos_profile=self.QOS, callback_group=sub_group)
        self.create_subscription(Point, "/cmd_map_marker", callback=self.handle_marker_cmd, qos_profile=self.QOS, callback_group=sub_group)
        self.create_subscription(Float32, "/robo_z", callback=self.handle_robo_z, qos_profile=self.QOS, callback_group=sub_group)

        self.PUB_global = self.create_publisher(OccupancyGrid, self._map_topic, qos_profile=self.NAV_QOS)
        self.PUB_marker = self.create_publisher(Marker, self._marker_topic, qos_profile=self.QOS)

        self.timer = self.create_timer(max(0.05, self._publish_period_s), self.clk)

        self.get_logger().info(
            f"global_mapper: frame={self.map_frame!r} topic={self._point_topic!r} "
            f"grid={self.grid_x}x{self.grid_y} sim={self.use_sim_data} mode={self._publish_mode!r}"
        )

    def clk(self) -> None:
        with self._lock:
            self.update = True

    def handle_robo_z(self, msg: Float32) -> None:
        self.robot_z = float(msg.data)

    def handle_marker_cmd(self, cmd: Point) -> None:
        msg = Marker()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.map_frame
        msg.type = Marker.SPHERE
        msg.id = 1
        msg.action = Marker.ADD
        msg.ns = "zone_marker"
        msg.scale.x = 0.35
        msg.scale.y = 0.35
        msg.scale.z = 0.35

        msg.color = ColorRGBA(r=1.0, g=0.2, b=0.1, a=0.9)

        msg.pose = Pose()
        msg.pose.position.x = float(cmd.x)
        msg.pose.position.y = float(cmd.y)
        msg.pose.position.z = 1.5

        np_quat = quaternion.from_euler_angles(0, np.pi / 2, 0)
        msg.pose.orientation = Quaternion(x=np_quat.x, y=np_quat.y, z=np_quat.z, w=np_quat.w)

        self.PUB_marker.publish(msg)

    def _decode_pointcloud2_xyz(self, msg: PointCloud2) -> np.ndarray:
        if self.use_sim_data:
            raw = np.frombuffer(msg.data, dtype=np.float32)
            if raw.size == 0 or raw.size % 8 != 0:
                return np.zeros((0, 3), dtype=np.float32)
            reshaped = raw.reshape(-1, 8)
            return np.ascontiguousarray(reshaped[:, :3], dtype=np.float32)

        try:
            import sensor_msgs_py.point_cloud2 as pc2

            pts: List[Tuple[float, float, float]] = []
            for index, tup in enumerate(pc2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True)):
                if index >= self._max_points:
                    break
                pts.append((float(tup[0]), float(tup[1]), float(tup[2])))
            if pts:
                return np.asarray(pts, dtype=np.float32)
            return np.zeros((0, 3), dtype=np.float32)
        except Exception as exc:
            self.get_logger().warn(f"sensor_msgs_py decode failed ({exc}); using raw float32 xyz layout")

        raw = np.frombuffer(msg.data, dtype=np.float32)
        if raw.size == 0 or raw.size % 3 != 0:
            return np.zeros((0, 3), dtype=np.float32)
        return raw.reshape(-1, 3)

    def _maybe_subsample(self, points: np.ndarray) -> np.ndarray:
        n = int(points.shape[0])
        if n <= self._max_points:
            return points
        idx = self._rng.choice(n, size=self._max_points, replace=False)
        return points[idx]

    def _range_mask_source(self, points: np.ndarray) -> np.ndarray:
        r = np.linalg.norm(points, axis=1)
        return (r >= self._min_range) & (r <= self._max_range)

    def filter_snap_points(self, points: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Project ``points`` (map frame, Nx3) into ``self.grid`` height stamps. Returns ix bounds or None."""
        self.grid.fill(0.0)

        valid = (
            np.isfinite(points).all(axis=1)
            & (points[:, 2] < self._z_top)
            & (points[:, 2] > self._z_bottom)
        )
        pts = points[valid]
        if pts.shape[0] == 0:
            return None

        x = pts[:, 0]
        y = pts[:, 1]
        z = pts[:, 2]

        x_grid = np.round((x * self.grid_resolution) + self.grid_x / 2.0).astype(np.int32)
        y_grid = np.round((y * self.grid_resolution) + self.grid_y / 2.0).astype(np.int32)

        inside = (x_grid >= 0) & (x_grid < self.grid_x) & (y_grid >= 0) & (y_grid < self.grid_y)
        x_grid = x_grid[inside]
        y_grid = y_grid[inside]
        z = z[inside]
        if x_grid.size == 0:
            return None

        self.grid[x_grid, y_grid] = z
        return int(x_grid.min()), int(x_grid.max()), int(y_grid.min()), int(y_grid.max())

    def detect_obstacles(self) -> None:
        if self._publish_mode == "height_debug":
            gridmax = float(self.grid.max())
            gridmin = float(self.grid.min())
            if self._debug:
                self.get_logger().info(f"height_debug grid z min={gridmin:.3f} max={gridmax:.3f}")
            span = abs(gridmax - gridmin)
            if span < 1e-6:
                return
            self.grid += abs(gridmin)
            self.grid *= 100.0 / span
            return

        seen = self.grid != 0.0
        high = seen & (self.grid > self._protrusion_z)
        pit = seen & (self.grid < self._pit_z)
        occupied = high | pit

        self.obstacle_map[seen & ~occupied] = 0.0
        self.obstacle_map[occupied] = 100.0

        if self._debug:
            self.get_logger().info(
                f"mapper z grid min={float(self.grid.min()):.3f} max={float(self.grid.max()):.3f} "
                f"robo_z={self.robot_z:.3f} pit<{self._pit_z} protrusion>{self._protrusion_z}"
            )

    def transform_points(self, points: np.ndarray, stamp, source_frame: str) -> Tuple[np.ndarray, bool]:
        if points.shape[0] == 0:
            return points, False

        def _lookup(time_msg: Time):
            return self.tf_buffer.lookup_transform(
                self.map_frame,
                source_frame,
                time_msg,
                timeout=rclpy.duration.Duration(seconds=self._tf_timeout_s),
            )

        tf_msg = None
        try:
            tf_msg = _lookup(Time.from_msg(stamp))
        except Exception:
            try:
                tf_msg = _lookup(Time())
            except Exception as exc_latest:
                self.get_logger().warn(
                    f"TF {self.map_frame} <- {source_frame} unavailable: {exc_latest}"
                )
                return points, False

        tr = tf_msg.transform.translation
        rot = tf_msg.transform.rotation
        tf_pos = (float(tr.x), float(tr.y), float(tr.z))
        quat_xyzw = (float(rot.x), float(rot.y), float(rot.z), float(rot.w))

        finite = np.isfinite(points).all(axis=1)
        in_range = self._range_mask_source(points)
        if self.use_sim_data:
            valid = finite & in_range & (points[:, 2] != 0.0) & (points[:, 2] != np.inf)
        else:
            valid = finite & in_range & (points[:, 2] != 0.0) & (points[:, 2] != np.inf) & (points[:, 2] <= 3.0)

        src = points[valid]
        if src.shape[0] == 0:
            return np.zeros((0, 3), dtype=np.float32), True

        mapped = transform_points_xyz_to_map(src, tf_pos, quat_xyzw).astype(np.float32)
        return mapped, True

    def gen_map(self, points: np.ndarray, stamp, source_frame: str) -> None:
        mapped, ok = self.transform_points(points, stamp, source_frame)
        if not ok or mapped.shape[0] == 0:
            return

        bounds: Optional[Tuple[int, int, int, int]] = None
        with self._lock:
            if not self.map_on:
                return
            bounds = self.filter_snap_points(mapped)
            if bounds is None:
                return
            self.detect_obstacles()
            self.publish_obstacle_map(stamp)
            self.update = False

        if self._debug and bounds is not None:
            ix0, ix1, iy0, iy1 = bounds
            self.get_logger().info(f"stamp updated cells ix=[{ix0},{ix1}] iy=[{iy0},{iy1}]")

    def handle_cmd(self, msg):
        self.map_on = int(msg.data) > 0

    def handle_depth(self, msg: PointCloud2) -> None:
        with self._lock:
            allow = self.update and self.map_on
        if not allow:
            return

        raw = self._decode_pointcloud2_xyz(msg)
        raw = self._maybe_subsample(raw)
        source = (msg.header.frame_id or "").strip() or self.default_point_cloud_frame
        self.gen_map(raw, msg.header.stamp, source)

    def publish_obstacle_map(self, stamp) -> None:
        info = MapMetaData()
        info.map_load_time = stamp
        info.resolution = 1.0 / self.grid_resolution
        info.width = self.grid_x
        info.height = self.grid_y

        info.origin.position.x = -(self.grid_x) / (2.0 * self.grid_resolution)
        info.origin.position.y = -(self.grid_y) / (2.0 * self.grid_resolution)
        info.origin.position.z = 0.0

        quat = quaternion.from_euler_angles(-np.pi / 2, np.pi, 0)
        info.origin.orientation.x = quat.x
        info.origin.orientation.y = quat.y
        info.origin.orientation.z = quat.z
        info.origin.orientation.w = quat.w

        if self._publish_mode == "height_debug":
            payload = encode_cell_grid_xy_to_ros_data(self.grid.astype(np.float32))
        else:
            payload = encode_cell_grid_xy_to_ros_data(self.obstacle_map)

        msg = OccupancyGrid()
        msg.info = info
        msg.header = Header(frame_id=self.map_frame, stamp=stamp)
        msg.data = payload.tolist()

        self.PUB_global.publish(msg)

    # Backwards-compatible names for external references / launch introspection
    handleCmd = handle_cmd
    handleDepth = handle_depth


def main(args=None):
    rclpy.init(args=args)
    mapper = GlobalMapper()
    executor = MultiThreadedExecutor()
    executor.add_node(mapper)
    try:
        executor.spin()
    finally:
        mapper.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
