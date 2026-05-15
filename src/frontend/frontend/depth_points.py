from __future__ import annotations

import numpy as np


def sanitize_point_vertices(vertices: np.ndarray, max_points: int | None = None) -> np.ndarray:
    """Return contiguous Nx3 float32 vertices with non-finite rows removed.

    Optionally downsample to ``max_points`` using a fixed stride to cap payload size.
    """
    arr = np.asarray(vertices, dtype=np.float32)
    if arr.size == 0:
        return np.empty((0, 3), dtype=np.float32)

    arr = arr.reshape(-1, 3)
    arr = arr[np.isfinite(arr).all(axis=1)]

    if max_points is not None and max_points > 0 and arr.shape[0] > max_points:
        stride = max(1, arr.shape[0] // max_points)
        arr = arr[::stride][:max_points]

    return np.ascontiguousarray(arr, dtype=np.float32)
