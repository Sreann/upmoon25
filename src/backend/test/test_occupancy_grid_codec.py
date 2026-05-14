import numpy as np

from backend.occupancy_grid_codec import decode_ros_data_to_cell_grid_xy, encode_cell_grid_xy_to_ros_data


def test_roundtrip_small_grid():
    w, h = 5, 4
    cell = np.zeros((w, h), dtype=np.float32)
    cell[1, 2] = 100
    cell[3, 0] = -1
    cell[0, 0] = 0
    flat = encode_cell_grid_xy_to_ros_data(cell)
    assert flat.shape == (w * h,)
    back = decode_ros_data_to_cell_grid_xy(flat, w, h)
    assert back.shape == (w, h)
    assert back[1, 2] == 100
    assert back[3, 0] == -1
    assert back[0, 0] == 0


def test_decode_rejects_wrong_length():
    raw = np.zeros(10, dtype=np.int8).tobytes()
    try:
        decode_ros_data_to_cell_grid_xy(raw, 3, 3)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_ros_row_ordering_matches_index_formula():
    w, h = 3, 2
    cell = np.zeros((w, h), dtype=np.float32)
    cell[2, 1] = 42
    flat = encode_cell_grid_xy_to_ros_data(cell)
    # iy=1, ix=2 -> k = 1 * w + 2 = 5
    assert flat[1 * w + 2] == 42
