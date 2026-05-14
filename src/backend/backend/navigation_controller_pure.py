"""
Pure short-segment navigation from a local traversability grid (no rclpy).

Grid layout matches ``local_terrain_grid`` / ``classify_local_terrain`` output:
``grid[forward_ix, lateral_ix]`` with forward along robot +x, lateral +y left.
Values: -1 unknown, 0 free, 60 caution, 100 obstacle.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

import numpy as np

from backend.terrain_grid_math import TERRAIN_CAUTION, TERRAIN_OBSTACLE, TERRAIN_UNKNOWN


def _band_blocked(slice_2d: np.ndarray, *, unknown_ratio_max: float) -> bool:
    """True if slice should not be driven (obstacle or too much unknown)."""
    if slice_2d.size == 0:
        return True
    flat = slice_2d.ravel()
    if np.any(flat >= TERRAIN_OBSTACLE):
        return True
    unknown = np.sum(flat == TERRAIN_UNKNOWN)
    if unknown / float(flat.size) > unknown_ratio_max:
        return True
    caution = np.sum(flat == TERRAIN_CAUTION)
    if caution / float(flat.size) > 0.55:
        return True
    return False


def plan_corridor_step(
    grid: np.ndarray,
    *,
    look_rows: int,
    unknown_ratio_max: float,
) -> Tuple[float, float, str]:
    """
    Return (linear_x, angular_z, reason) in robot base_link convention (+x forward, +z CCW).

    Uses three lateral bands in the near forward window; prefers center, then biases turn.
    """
    if grid.ndim != 2 or grid.size == 0:
        return 0.0, 0.0, "empty_grid"
    h, w = int(grid.shape[0]), int(grid.shape[1])
    if h < 2 or w < 3:
        return 0.0, 0.0, "grid_too_small"

    lr = max(1, min(look_rows, h))
    slice_full = grid[:lr, :]

    third = max(1, w // 3)
    left = slice_full[:, :third]
    center = slice_full[:, third : w - third] if w - 2 * third >= 1 else slice_full[:, w // 3 : (2 * w) // 3 + 1]
    right = slice_full[:, w - third :]

    left_b = _band_blocked(left, unknown_ratio_max=unknown_ratio_max)
    center_b = _band_blocked(center, unknown_ratio_max=unknown_ratio_max)
    right_b = _band_blocked(right, unknown_ratio_max=unknown_ratio_max)

    if not center_b:
        return 1.0, 0.0, "center_clear"
    if not left_b and right_b:
        return 0.35, 0.65, "bias_left_center_blocked"
    if not right_b and left_b:
        return 0.35, -0.65, "bias_right_center_blocked"
    if not left_b and not right_b:
        return 0.2, 0.45, "squeeze_center_blocked_both_sides_open"
    return 0.0, 0.0, "blocked"


def plan_navigation_step(
    grid: np.ndarray,
    *,
    look_rows: int,
    unknown_ratio_max: float,
    bearing_deg: Optional[float] = None,
    bearing_weight: float = 0.0,
    min_bearing_deg: float = 2.0,
) -> Tuple[float, float, str]:
    """
    Corridor plan plus optional visual bearing toward a flag (``bearing_deg`` from perception).

    Convention matches flag detector tests: negative deg = object left of image center,
    positive = right. ROS ``angular.z``: + = CCW (turn left). We use ``w_goal = clip(-bearing/45, -1, 1)``
    so a flag on the right (+bearing) yields negative ``angular.z`` (turn right).
    """
    ln, an, reason = plan_corridor_step(grid, look_rows=look_rows, unknown_ratio_max=unknown_ratio_max)
    if bearing_deg is None or bearing_weight <= 0.0:
        return ln, an, reason
    if not math.isfinite(bearing_deg) or abs(float(bearing_deg)) < min_bearing_deg:
        return ln, an, reason
    w_goal = float(np.clip(-float(bearing_deg) / 45.0, -1.0, 1.0))
    an = float(np.clip((1.0 - bearing_weight) * an + bearing_weight * w_goal, -1.0, 1.0))
    if abs(an) > 0.35:
        ln *= 0.75
    return float(ln), an, f"{reason}+bearing"


def wrap_deg(angle_deg: float) -> float:
    """Wrap degrees to (-180, 180]."""
    x = float(angle_deg)
    while x <= -180.0:
        x += 360.0
    while x > 180.0:
        x -= 360.0
    return x


def heading_error_deg(
    robot_x: float,
    robot_y: float,
    robot_yaw_rad: float,
    goal_x: float,
    goal_y: float,
) -> float:
    """
    Signed heading error (deg) from robot +x to the goal in the same plane as ``robot_*`` / ``goal_*``.

    Positive => goal lies counterclockwise from forward (turn left / +``angular.z`` in ROS).
    """
    if not all(map(math.isfinite, (robot_x, robot_y, robot_yaw_rad, goal_x, goal_y))):
        return 0.0
    gx = float(goal_x) - float(robot_x)
    gy = float(goal_y) - float(robot_y)
    if abs(gx) < 1e-9 and abs(gy) < 1e-9:
        return 0.0
    bearing_world = math.degrees(math.atan2(gy, gx))
    return wrap_deg(bearing_world - math.degrees(float(robot_yaw_rad)))


def steering_bearing_from_heading_error(heading_err_deg: float) -> float:
    """
    Map planar heading error into the ``bearing_deg`` convention expected by ``plan_navigation_step``
    (same as camera flag bearing: positive => cue on right => negative ``angular.z``).
    """
    return -float(heading_err_deg)


def zone_odom_xy(zones: Dict[str, Any], zone_id: str) -> Optional[Tuple[float, float]]:
    """Read ``odom_x`` / ``odom_y`` from supervisor ``zones`` entry if present."""
    z = zones.get(zone_id)
    if not isinstance(z, dict):
        return None
    try:
        ox = z.get("odom_x")
        oy = z.get("odom_y")
        if ox is None or oy is None:
            return None
        return float(ox), float(oy)
    except (TypeError, ValueError):
        return None


def scale_twist(linear_norm: float, angular_norm: float, *, v_max: float, w_max: float) -> Tuple[float, float]:
    """Map normalized plan output to physical limits."""
    return float(linear_norm * v_max), float(angular_norm * w_max)


def navigation_status_dict(
    *,
    active: bool,
    gated_reason: str,
    plan_reason: str,
    linear_x: float,
    angular_z: float,
    bearing_deg: Optional[float] = None,
    bearing_confidence: Optional[float] = None,
    goal_source: Optional[str] = None,
    goal_distance_m: Optional[float] = None,
    heading_error_deg_odom: Optional[float] = None,
    mission_phase: Optional[str] = None,
    mission_controller_mode: Optional[str] = None,
) -> Dict[str, object]:
    out: Dict[str, object] = {
        "active": bool(active),
        "gated_reason": gated_reason,
        "plan_reason": plan_reason,
        "linear_x": float(linear_x),
        "angular_z": float(angular_z),
    }
    if bearing_deg is not None and math.isfinite(float(bearing_deg)):
        out["bearing_deg"] = float(bearing_deg)
    if bearing_confidence is not None and math.isfinite(float(bearing_confidence)):
        out["bearing_confidence"] = float(bearing_confidence)
    if goal_source:
        out["goal_source"] = str(goal_source)
    if goal_distance_m is not None and math.isfinite(float(goal_distance_m)):
        out["goal_distance_m"] = float(goal_distance_m)
    if heading_error_deg_odom is not None and math.isfinite(float(heading_error_deg_odom)):
        out["heading_error_deg_odom"] = float(heading_error_deg_odom)
    if mission_phase:
        out["mission_phase"] = str(mission_phase)
    if mission_controller_mode:
        out["mission_controller_mode"] = str(mission_controller_mode)
    return out
