import cv2
import numpy as np

from backend.flag_detection_math import detect_red_orange_flags


def _blank_image():
    return np.zeros((120, 160, 3), dtype=np.uint8)


def test_detects_center_orange_flag_with_near_zero_bearing():
    image = _blank_image()
    cv2.rectangle(image, (72, 25), (88, 95), (0, 120, 255), -1)

    candidates = detect_red_orange_flags(image, horizontal_fov_deg=60.0, min_area_px=100)

    assert len(candidates) == 1
    assert abs(candidates[0]["bearing_deg"]) < 1.0
    assert candidates[0]["confidence"] > 0.2


def test_left_flag_has_negative_bearing_and_right_flag_has_positive_bearing():
    left = _blank_image()
    right = _blank_image()
    cv2.rectangle(left, (20, 25), (38, 95), (0, 0, 255), -1)
    cv2.rectangle(right, (122, 25), (140, 95), (0, 0, 255), -1)

    left_candidate = detect_red_orange_flags(left, horizontal_fov_deg=60.0, min_area_px=100)[0]
    right_candidate = detect_red_orange_flags(right, horizontal_fov_deg=60.0, min_area_px=100)[0]

    assert left_candidate["bearing_deg"] < 0
    assert right_candidate["bearing_deg"] > 0


def test_ignores_small_red_noise_below_area_threshold():
    image = _blank_image()
    cv2.rectangle(image, (40, 40), (45, 45), (0, 0, 255), -1)

    candidates = detect_red_orange_flags(image, min_area_px=100)

    assert candidates == []


def test_limits_candidates_by_confidence_order():
    image = _blank_image()
    cv2.rectangle(image, (10, 20), (22, 80), (0, 0, 255), -1)
    cv2.rectangle(image, (70, 10), (95, 105), (0, 120, 255), -1)
    cv2.rectangle(image, (130, 30), (140, 70), (0, 0, 255), -1)

    candidates = detect_red_orange_flags(image, min_area_px=100, max_candidates=2)

    assert len(candidates) == 2
    assert candidates[0]["confidence"] >= candidates[1]["confidence"]
