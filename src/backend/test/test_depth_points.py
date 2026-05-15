from __future__ import annotations

import numpy as np

from frontend.depth_points import sanitize_point_vertices


def test_sanitize_point_vertices_drops_non_finite_rows():
    vertices = np.array(
        [
            [1.0, 2.0, 3.0],
            [np.nan, 1.0, 2.0],
            [1.0, np.inf, 3.0],
            [4.0, 5.0, 6.0],
        ],
        dtype=np.float32,
    )

    out = sanitize_point_vertices(vertices)

    assert out.shape == (2, 3)
    assert np.allclose(out[0], [1.0, 2.0, 3.0])
    assert np.allclose(out[1], [4.0, 5.0, 6.0])


def test_sanitize_point_vertices_caps_count_with_stride():
    vertices = np.array([[float(i), 0.0, 1.0] for i in range(12)], dtype=np.float32)

    out = sanitize_point_vertices(vertices, max_points=5)

    assert out.shape == (5, 3)
    assert np.allclose(out[:, 0], [0.0, 2.0, 4.0, 6.0, 8.0])
