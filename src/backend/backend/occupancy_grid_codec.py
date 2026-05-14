"""
nav_msgs/OccupancyGrid data layout used across mapper, costmapper, and planner.

ROS 2 ``OccupancyGrid.data`` is row-major with ``index = row_y * width + column_x``
where ``width = msg.info.width`` (cells along +x) and ``height = msg.info.height``
(cells along +y). Values are int8: -1 unknown, 0–100 occupancy probability.

Internal code in this repo uses a dense 2D array ``cell[ix, iy]`` with shape
``(width, height)`` — first axis = map x cell index, second = map y cell index.
"""

from __future__ import annotations

import numpy as np


def decode_ros_data_to_cell_grid_xy(data: bytes | np.ndarray, width: int, height: int) -> np.ndarray:
    """
    Decode flat ROS ``OccupancyGrid.data`` into ``cell[ix, iy]`` with shape ``(width, height)``.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    flat = np.frombuffer(data, dtype=np.int8)
    if flat.size != width * height:
        raise ValueError(f"Expected {width * height} cells, got {flat.size}")
    row_major_hw = flat.reshape((height, width), order="C")
    return np.ascontiguousarray(row_major_hw.T, dtype=np.int8)


def encode_cell_grid_xy_to_ros_data(cell: np.ndarray) -> np.ndarray:
    """
    Encode ``cell[ix, iy]`` shape ``(width, height)`` to flat int8 ROS row-major ``data``.
    """
    if cell.ndim != 2:
        raise ValueError("cell must be 2-D (width, height)")
    width, height = int(cell.shape[0]), int(cell.shape[1])
    if width <= 0 or height <= 0:
        raise ValueError("cell dimensions must be positive")
    row_major = np.ascontiguousarray(cell.T, dtype=np.float64)
    return np.clip(np.round(row_major.ravel(order="C")), -1, 100).astype(np.int8)
