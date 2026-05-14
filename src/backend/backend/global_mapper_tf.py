"""Pure geometry helpers for global_mapper (TF: source cloud frame -> map frame)."""

from __future__ import annotations

import numpy as np


def rotation_matrix_from_quaternion_xyzw(x: float, y: float, z: float, w: float) -> np.ndarray:
    """Unit quaternion in geometry_msgs order (x, y, z, w) -> 3x3 rotation matrix."""
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    return np.array(
        [
            [1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy)],
            [2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx)],
            [2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy)],
        ],
        dtype=np.float64,
    )


def transform_points_xyz_to_map(
    points: np.ndarray,
    translation_xyz: tuple[float, float, float],
    quat_xyzw: tuple[float, float, float, float],
) -> np.ndarray:
    """
    Apply a rigid transform T_map_source.

    ``points`` are Nx3 in the point cloud's ``header.frame_id`` (source).
    ``quat_xyzw`` uses geometry_msgs order (x, y, z, w).

    Returns Nx3 in the map frame: p_map = R @ p_src + t
    """
    if points.size == 0:
        return points.astype(np.float64, copy=False)

    tx, ty, tz = translation_xyz
    qx, qy, qz, qw = quat_xyzw
    rot = rotation_matrix_from_quaternion_xyzw(qx, qy, qz, qw)
    tvec = np.array([tx, ty, tz], dtype=np.float64)
    pts = np.asarray(points, dtype=np.float64)
    return (rot @ pts.T).T + tvec
