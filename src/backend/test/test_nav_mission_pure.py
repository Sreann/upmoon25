"""Offline tests for nav_mission_pure helpers."""

import numpy as np

from backend.nav_mission_pure import dig_zone_has_pose, distance_to_zone_m, unknown_cell_fraction
from backend.navigation_controller_pure import zone_odom_xy


def test_unknown_cell_fraction_empty():
    assert unknown_cell_fraction(np.array([], dtype=np.int8)) == 1.0


def test_unknown_cell_fraction_half():
    g = np.array([[0, -1], [-1, 100]], dtype=np.int8)
    assert abs(unknown_cell_fraction(g) - 0.5) < 1e-6


def test_distance_to_zone_m():
    zones = {"dig": {"zone": "dig", "odom_x": 1.0, "odom_y": 0.0}}
    d = distance_to_zone_m(0.0, 0.0, zones, "dig")
    assert d is not None and abs(d - 1.0) < 1e-6


def test_dig_zone_has_pose():
    assert dig_zone_has_pose({}, "dig") is False
    assert dig_zone_has_pose({"dig": {"odom_x": 1, "odom_y": 2}}, "dig") is True


def test_zone_odom_xy_used_by_nav_mission():
    z = {"dig": {"odom_x": -0.5, "odom_y": 2.0}}
    xy = zone_odom_xy(z, "dig")
    assert xy is not None
    assert abs(xy[0] + 0.5) < 1e-9
