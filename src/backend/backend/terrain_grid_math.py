import numpy as np


TERRAIN_UNKNOWN = -1
TERRAIN_FREE = 0
TERRAIN_CAUTION = 60
TERRAIN_OBSTACLE = 100

GRID_PRESETS = {
    "coarse": {"resolution_m": 0.15, "forward_m": 3.0, "width_m": 3.0},
    "standard": {"resolution_m": 0.10, "forward_m": 3.0, "width_m": 3.0},
    "fine": {"resolution_m": 0.05, "forward_m": 3.0, "width_m": 3.0},
}


def resolve_grid_config(preset, forward_m, width_m, resolution_m):
    values = dict(GRID_PRESETS.get(str(preset).lower(), {}))
    return {
        "forward_m": float(forward_m if forward_m is not None else values.get("forward_m", 3.0)),
        "width_m": float(width_m if width_m is not None else values.get("width_m", 3.0)),
        "resolution_m": float(resolution_m if resolution_m is not None else values.get("resolution_m", 0.10)),
    }


def classify_local_terrain(
    points,
    *,
    forward_m,
    width_m,
    resolution_m,
    ground_min_z,
    ground_max_z,
    obstacle_z,
    drop_z,
):
    grid_w = max(1, int(width_m / resolution_m))
    grid_h = max(1, int(forward_m / resolution_m))
    grid = np.full((grid_h, grid_w), TERRAIN_UNKNOWN, dtype=np.int8)

    if points.size == 0:
        return grid

    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]
    mask = (x >= 0.0) & (x <= forward_m) & (y >= -width_m / 2.0) & (y <= width_m / 2.0)
    x = x[mask]
    y = y[mask]
    z = z[mask]

    if x.size == 0:
        return grid

    col = np.clip(((y + width_m / 2.0) / resolution_m).astype(np.int32), 0, grid_w - 1)
    row = np.clip((x / resolution_m).astype(np.int32), 0, grid_h - 1)

    for r, c, height in zip(row, col, z):
        if height >= obstacle_z:
            grid[r, c] = TERRAIN_OBSTACLE
        elif height <= drop_z:
            if grid[r, c] < TERRAIN_OBSTACLE:
                grid[r, c] = TERRAIN_CAUTION
        elif ground_min_z <= height <= ground_max_z and grid[r, c] < TERRAIN_CAUTION:
            grid[r, c] = TERRAIN_FREE

    return grid


def summarize_grid(grid):
    return {
        "obstacle_cells": int(np.count_nonzero(grid == TERRAIN_OBSTACLE)),
        "caution_cells": int(np.count_nonzero(grid == TERRAIN_CAUTION)),
        "unknown_cells": int(np.count_nonzero(grid == TERRAIN_UNKNOWN)),
        "free_cells": int(np.count_nonzero(grid == TERRAIN_FREE)),
    }
