import math

import numpy as np

from backend.navigation_controller_pure import (
    heading_error_deg,
    plan_corridor_step,
    plan_navigation_step,
    scale_twist,
    steering_bearing_from_heading_error,
    wrap_deg,
    zone_odom_xy,
)
from backend.terrain_grid_math import TERRAIN_FREE, TERRAIN_OBSTACLE, TERRAIN_UNKNOWN


def test_center_corridor_clear_moves_forward():
    g = np.full((20, 30), TERRAIN_FREE, dtype=np.int8)
    lx, az, reason = plan_corridor_step(g, look_rows=8, unknown_ratio_max=0.5)
    assert reason == "center_clear"
    assert lx > 0 and az == 0.0


def test_center_blocked_opens_left():
    g = np.full((20, 30), TERRAIN_FREE, dtype=np.int8)
    g[:10, 10:20] = TERRAIN_OBSTACLE
    g[:10, :9] = TERRAIN_FREE
    g[:10, 21:] = TERRAIN_OBSTACLE
    lx, az, reason = plan_corridor_step(g, look_rows=10, unknown_ratio_max=0.5)
    assert "left" in reason
    assert az > 0


def test_unknown_dominant_blocks():
    g = np.full((15, 30), TERRAIN_UNKNOWN, dtype=np.int8)
    lx, az, reason = plan_corridor_step(g, look_rows=8, unknown_ratio_max=0.2)
    assert lx == 0.0 and az == 0.0
    assert reason == "blocked"


def test_scale_twist_respects_limits():
    lin, ang = scale_twist(1.0, 0.5, v_max=0.2, w_max=0.4)
    assert abs(lin - 0.2) < 1e-6 and abs(ang - 0.2) < 1e-6


def test_bearing_positive_biases_turn_right():
    g = np.full((20, 30), TERRAIN_FREE, dtype=np.int8)
    lx0, az0, _ = plan_corridor_step(g, look_rows=8, unknown_ratio_max=0.5)
    lx, az, reason = plan_navigation_step(
        g,
        look_rows=8,
        unknown_ratio_max=0.5,
        bearing_deg=30.0,
        bearing_weight=0.5,
    )
    assert "bearing" in reason
    assert lx0 > 0 and lx > 0
    assert az < az0  # more negative angular = turn toward +bearing (right)


def test_bearing_ignored_when_weight_zero():
    g = np.full((20, 30), TERRAIN_FREE, dtype=np.int8)
    a = plan_navigation_step(
        g,
        look_rows=8,
        unknown_ratio_max=0.5,
        bearing_deg=45.0,
        bearing_weight=0.0,
    )
    b = plan_corridor_step(g, look_rows=8, unknown_ratio_max=0.5)
    assert a == b


def test_wrap_deg():
    assert abs(wrap_deg(370.0) - 10.0) < 1e-9
    assert abs(wrap_deg(-190.0) - 170.0) < 1e-9
    assert abs(wrap_deg(180.0) - 180.0) < 1e-9


def test_heading_error_deg_aligned_and_left():
    e0 = heading_error_deg(0.0, 0.0, 0.0, 1.0, 0.0)
    assert abs(e0) < 1e-6
    e90 = heading_error_deg(0.0, 0.0, 0.0, 0.0, 1.0)
    assert abs(e90 - 90.0) < 1e-6
    e45 = heading_error_deg(0.0, 0.0, math.pi / 4, 1.0, 0.0)
    assert abs(e45 + 45.0) < 1e-6


def test_steering_bearing_negates_heading_error():
    assert abs(steering_bearing_from_heading_error(20.0) + 20.0) < 1e-9


def test_zone_odom_xy_reads_zone():
    zones = {"dig": {"odom_x": 1.5, "odom_y": -2.0}}
    xy = zone_odom_xy(zones, "dig")
    assert xy is not None
    assert abs(xy[0] - 1.5) < 1e-9 and abs(xy[1] + 2.0) < 1e-9
    assert zone_odom_xy(zones, "missing") is None
    assert zone_odom_xy({}, "dig") is None
    assert zone_odom_xy({"dig": "bad"}, "dig") is None
