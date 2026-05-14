"""
Pure helpers for start→dig nav mission (no rclpy).

Used by ``nav_mission_executor`` and offline tests. Grid values match
``local_terrain_grid`` / ``navigation_controller_pure`` (-1 unknown, 0 free, …).
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np

from backend.navigation_controller_pure import zone_odom_xy


def unknown_cell_fraction(grid: np.ndarray) -> float:
    """Fraction of cells that are unknown (-1). Empty grid → 1.0."""
    if grid is None or grid.size == 0:
        return 1.0
    flat = grid.ravel()
    unk = np.sum(flat == np.int8(-1))
    return float(unk) / float(flat.size)


def distance_to_zone_m(
    robot_x: float,
    robot_y: float,
    zones: Optional[Dict[str, Any]],
    zone_id: str,
) -> Optional[float]:
    """Euclidean distance in the same frame as ``zone_odom_xy`` (typically odom)."""
    if not isinstance(zones, dict):
        return None
    xy = zone_odom_xy(zones, zone_id)
    if xy is None:
        return None
    return float(math.hypot(xy[0] - float(robot_x), xy[1] - float(robot_y)))


def dig_zone_has_pose(zones: Optional[Dict[str, Any]], zone_id: str = "dig") -> bool:
    if not isinstance(zones, dict):
        return False
    return zone_odom_xy(zones, zone_id) is not None
