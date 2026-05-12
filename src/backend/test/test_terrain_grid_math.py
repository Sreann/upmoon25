import numpy as np

from backend.terrain_grid_math import (
    TERRAIN_CAUTION,
    TERRAIN_FREE,
    TERRAIN_OBSTACLE,
    TERRAIN_UNKNOWN,
    classify_local_terrain,
    resolve_grid_config,
    summarize_grid,
)


def test_standard_preset_uses_10_cm_cells():
    config = resolve_grid_config("standard", None, None, None)

    assert config["forward_m"] == 3.0
    assert config["width_m"] == 3.0
    assert config["resolution_m"] == 0.10


def test_explicit_resolution_overrides_preset():
    config = resolve_grid_config("standard", None, None, 0.05)

    assert config["resolution_m"] == 0.05


def test_classifies_free_obstacle_caution_and_unknown_cells():
    points = np.array(
        [
            [0.25, 0.00, 0.00],
            [0.55, 0.25, 0.42],
            [0.80, -0.25, -0.60],
        ],
        dtype=np.float32,
    )

    grid = classify_local_terrain(
        points,
        forward_m=1.0,
        width_m=1.0,
        resolution_m=0.25,
        ground_min_z=-0.20,
        ground_max_z=0.20,
        obstacle_z=0.30,
        drop_z=-0.45,
    )
    summary = summarize_grid(grid)

    assert grid.shape == (4, 4)
    assert TERRAIN_FREE in grid
    assert TERRAIN_OBSTACLE in grid
    assert TERRAIN_CAUTION in grid
    assert summary["unknown_cells"] > 0


def test_obstacle_wins_over_ground_in_same_cell():
    points = np.array(
        [
            [0.25, 0.00, 0.00],
            [0.25, 0.00, 0.50],
        ],
        dtype=np.float32,
    )

    grid = classify_local_terrain(
        points,
        forward_m=1.0,
        width_m=1.0,
        resolution_m=0.25,
        ground_min_z=-0.20,
        ground_max_z=0.20,
        obstacle_z=0.30,
        drop_z=-0.45,
    )

    assert TERRAIN_OBSTACLE in grid
    assert np.count_nonzero(grid == TERRAIN_UNKNOWN) == 15
