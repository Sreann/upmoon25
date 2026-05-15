"""Inflates obstacles from ``/map/global`` into a robot-footprint-aware cost grid."""

from __future__ import annotations

import threading
from typing import Optional

import numpy as np
import quaternion
import rclpy
from map_msgs.msg import OccupancyGridUpdate
from nav_msgs.msg import MapMetaData, OccupancyGrid
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import Header

from backend.occupancy_grid_codec import decode_ros_data_to_cell_grid_xy, encode_cell_grid_xy_to_ros_data
from backend.robot_footprint import GLOBAL_ROBOT_CLEARANCE_RADIUS_M


class GlobalCostmapper(Node):
    """
    Subscribes to the global occupancy grid and publishes ``map/global_costmap``
    with circular inflation around hard obstacles (100).
    """

    def __init__(self):
        super().__init__("global_costmapper")

        self.declare_parameter("map_frame", "map")
        self.declare_parameter("robot_radius_m", GLOBAL_ROBOT_CLEARANCE_RADIUS_M)
        self.declare_parameter("inflation_multiplier", 1.66)
        self.declare_parameter("global_map_topic", "map/global")
        self.declare_parameter("global_updates_topic", "map/global_updates")
        self.declare_parameter("costmap_topic", "map/global_costmap")
        self.declare_parameter("publish_log_interval", 0)

        self.NAV_QOS = QoSProfile(
            depth=1,
            reliability=1,
            history=1,
            durability=1,
        )

        self._frame = str(self.get_parameter("map_frame").value)
        self._robot_rad = float(self.get_parameter("robot_radius_m").value)
        self._inflate_mult = float(self.get_parameter("inflation_multiplier").value)
        self._map_topic = str(self.get_parameter("global_map_topic").value)
        self._updates_topic = str(self.get_parameter("global_updates_topic").value)
        self._cost_topic = str(self.get_parameter("costmap_topic").value)
        self._publish_log_interval = int(self.get_parameter("publish_log_interval").value)

        self._lock = threading.Lock()
        self._map_initialized = False
        self._map_x: Optional[int] = None
        self._map_y: Optional[int] = None
        self._map_res_cpm: Optional[float] = None
        self._costmap: Optional[np.ndarray] = None
        self._publish_count = 0

        self.PUB_costmap = self.create_publisher(OccupancyGrid, self._cost_topic, self.NAV_QOS)
        self.create_subscription(OccupancyGrid, self._map_topic, self.on_map_init, self.NAV_QOS)
        self.create_subscription(OccupancyGridUpdate, self._updates_topic, self.on_map_update, self.NAV_QOS)

        self.get_logger().info(
            f"global_costmapper: map={self._map_topic!r} cost={self._cost_topic!r} frame={self._frame!r}"
        )

    def on_map_update(self, msg: OccupancyGridUpdate) -> None:
        with self._lock:
            if not self._map_initialized or self._costmap is None:
                return
            try:
                patch = decode_ros_data_to_cell_grid_xy(msg.data, int(msg.width), int(msg.height))
            except ValueError as exc:
                self.get_logger().warning(f"Ignoring invalid map update: {exc}")
                return

            x0, y0 = int(msg.x), int(msg.y)
            x1, y1 = x0 + int(msg.width), y0 + int(msg.height)
            if x0 < 0 or y0 < 0 or x1 > self._map_x or y1 > self._map_y:
                self.get_logger().warning("Map update rectangle out of bounds; ignoring")
                return

            self._update_costmap(patch, x0, x1, y0, y1, msg.header.stamp)

    def on_map_init(self, msg: OccupancyGrid) -> None:
        with self._lock:
            try:
                obstacles = decode_ros_data_to_cell_grid_xy(msg.data, int(msg.info.width), int(msg.info.height))
            except ValueError as exc:
                self.get_logger().error(f"Invalid global map message: {exc}")
                return

            self._map_x = obstacles.shape[0]
            self._map_y = obstacles.shape[1]
            self._map_res_cpm = 1.0 / float(msg.info.resolution)
            self._costmap = np.zeros((self._map_x, self._map_y), dtype=np.int8)
            self._map_initialized = True

            self._update_costmap(obstacles, 0, self._map_x, 0, self._map_y, msg.header.stamp)

    def _update_costmap(
        self,
        obst_map: np.ndarray,
        x_min: int,
        x_max: int,
        y_min: int,
        y_max: int,
        stamp,
    ) -> None:
        assert self._costmap is not None and self._map_x is not None and self._map_y is not None
        assert self._map_res_cpm is not None

        circle_rad = max(1, int(self._robot_rad * self._map_res_cpm))
        buffer_rad = max(1, int(circle_rad * self._inflate_mult))

        hard = obst_map == np.int8(100)
        xs, ys = np.where(hard)

        for lx, ly in zip(xs.tolist(), ys.tolist()):
            gx = int(lx + x_min)
            gy = int(ly + y_min)

            for xi in range(-buffer_rad, buffer_rad + 1):
                for yi in range(-buffer_rad, buffer_rad + 1):
                    radial = xi * xi + yi * yi
                    if radial > buffer_rad * buffer_rad:
                        continue
                    color = 50
                    if radial <= circle_rad * circle_rad:
                        color = 99

                    x_index = int(xi + gx)
                    y_index = int(yi + gy)
                    if 0 <= x_index < self._map_x and 0 <= y_index < self._map_y:
                        if int(self._costmap[x_index, y_index]) > 50:
                            continue
                        self._costmap[x_index, y_index] = np.int8(color)

            self._costmap[gx, gy] = np.int8(100)

        self._publish_costmap(stamp)

    def _publish_costmap(self, stamp) -> None:
        assert self._costmap is not None and self._map_x is not None and self._map_y is not None
        assert self._map_res_cpm is not None

        msg = OccupancyGrid()
        info = MapMetaData()
        info.height = self._map_y
        info.width = self._map_x
        info.resolution = 1.0 / self._map_res_cpm
        info.map_load_time = stamp

        info.origin.position.x = -(self._map_x) / (2.0 * self._map_res_cpm)
        info.origin.position.y = -(self._map_y) / (2.0 * self._map_res_cpm)
        info.origin.position.z = 0.0

        quat = quaternion.from_euler_angles(-np.pi / 2, np.pi, 0)
        info.origin.orientation.x = quat.x
        info.origin.orientation.y = quat.y
        info.origin.orientation.z = quat.z
        info.origin.orientation.w = quat.w

        payload = encode_cell_grid_xy_to_ros_data(self._costmap.astype(np.float32))
        msg.data = payload.tolist()
        msg.info = info
        msg.header = Header(frame_id=self._frame, stamp=stamp)

        self.PUB_costmap.publish(msg)

        self._publish_count += 1
        if self._publish_log_interval > 0 and self._publish_count % self._publish_log_interval == 0:
            self.get_logger().info(f"Published costmap ({self._publish_count} messages)")


def main(args=None):
    rclpy.init(args=args)
    node = GlobalCostmapper()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
