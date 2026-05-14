"""Offline checks: dig terrain slices use the same corridor planner as nav."""

import numpy as np

from backend.navigation_controller_pure import plan_corridor_step
from backend.terrain_grid_math import TERRAIN_FREE, TERRAIN_OBSTACLE


def test_forward_slice_clear_allows_drive():
    g = np.full((24, 30), TERRAIN_FREE, dtype=np.int8)
    sub = g[:8, :]
    ln, an, reason = plan_corridor_step(sub, look_rows=8, unknown_ratio_max=0.45)
    assert ln > 0
    assert reason == "center_clear"


def test_forward_slice_obstacle_blocks():
    g = np.full((24, 30), TERRAIN_FREE, dtype=np.int8)
    g[:8, :] = TERRAIN_OBSTACLE
    sub = g[:8, :]
    ln, an, reason = plan_corridor_step(sub, look_rows=8, unknown_ratio_max=0.45)
    assert ln == 0.0 and an == 0.0
    assert reason == "blocked"


def test_reverse_slice_matches_rear_rows():
    g = np.full((24, 30), TERRAIN_FREE, dtype=np.int8)
    g[-8:, :] = TERRAIN_OBSTACLE
    sub = g[-8:, :]
    ln, an, reason = plan_corridor_step(sub, look_rows=8, unknown_ratio_max=0.45)
    assert reason == "blocked"
