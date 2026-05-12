import math

import cv2
import numpy as np


def detect_red_orange_flags(frame_bgr, *, horizontal_fov_deg=69.0, min_area_px=180.0, max_candidates=5):
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    red_low = cv2.inRange(hsv, np.array([0, 80, 60]), np.array([12, 255, 255]))
    red_high = cv2.inRange(hsv, np.array([170, 80, 60]), np.array([179, 255, 255]))
    orange = cv2.inRange(hsv, np.array([8, 70, 70]), np.array([32, 255, 255]))
    mask = cv2.bitwise_or(cv2.bitwise_or(red_low, red_high), orange)
    mask = cv2.medianBlur(mask, 5)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = frame_bgr.shape[:2]
    center_x = width / 2.0
    h_fov = math.radians(float(horizontal_fov_deg))

    candidates = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < min_area_px:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if w <= 0 or h <= 0:
            continue
        fill_ratio = area / float(w * h)
        aspect = h / float(w)
        if fill_ratio < 0.25 or aspect < 0.5:
            continue

        centroid_x = x + w / 2.0
        bearing_rad = ((centroid_x - center_x) / max(1.0, width)) * h_fov
        confidence = min(1.0, (area / 2500.0) * min(1.0, fill_ratio * 2.0))
        candidates.append(
            {
                "bearing_rad": round(bearing_rad, 4),
                "bearing_deg": round(math.degrees(bearing_rad), 2),
                "confidence": round(confidence, 3),
                "area_px": round(area, 1),
                "bbox": [int(x), int(y), int(w), int(h)],
                "color": "red_orange",
            }
        )

    candidates.sort(key=lambda item: item["confidence"], reverse=True)
    return candidates[: int(max_candidates)]
