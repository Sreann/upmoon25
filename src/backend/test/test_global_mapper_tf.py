import math

import numpy as np

from backend.global_mapper_tf import rotation_matrix_from_quaternion_xyzw, transform_points_xyz_to_map


def test_rotation_matrix_z_90_matches_numpy_expectation():
    """+90 deg about Z: x axis should map to +y axis."""
    half = math.sqrt(0.5)
    # quaternion for +90 deg about Z (x,y,z,w)
    R = rotation_matrix_from_quaternion_xyzw(0.0, 0.0, half, half)
    v = R @ np.array([1.0, 0.0, 0.0])
    assert np.allclose(v, [0.0, 1.0, 0.0], atol=1e-6)


def test_translation_only():
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float32)
    out = transform_points_xyz_to_map(pts, (2.0, -1.0, 0.5), (0.0, 0.0, 0.0, 1.0))
    assert np.allclose(out[0], [2.0, -1.0, 0.5])
    assert np.allclose(out[1], [3.0, -1.0, 0.5])


def test_rotation_z_90deg_about_origin():
    half = math.sqrt(0.5)
    pts = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    out = transform_points_xyz_to_map(pts, (0.0, 0.0, 0.0), (0.0, 0.0, half, half))
    assert np.allclose(out[0, 0], 0.0, atol=1e-5)
    assert np.allclose(out[0, 1], 1.0, atol=1e-5)
    assert np.allclose(out[0, 2], 0.0, atol=1e-5)


def test_empty_points_returns_empty():
    pts = np.zeros((0, 3), dtype=np.float32)
    out = transform_points_xyz_to_map(pts, (1.0, 2.0, 3.0), (0.0, 0.0, 0.0, 1.0))
    assert out.shape == (0, 3)
