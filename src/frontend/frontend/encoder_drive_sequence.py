"""Pure timing logic for encoder bring-up drive (no ROS imports)."""

from typing import Tuple


def drive_cmd_for_encoder_drive_elapsed(
    elapsed_sec: float,
    *,
    linear_speed: float,
    turn_speed: float,
    phase_duration_sec: float,
) -> Tuple[float, float]:
    """Open-loop cmd/velocity sequence: forward, reverse, left turn, right turn, then stop."""
    if elapsed_sec < phase_duration_sec:
        return linear_speed, 0.0
    if elapsed_sec < 2.0 * phase_duration_sec:
        return -linear_speed, 0.0
    if elapsed_sec < 3.0 * phase_duration_sec:
        return 0.0, turn_speed
    if elapsed_sec < 4.0 * phase_duration_sec:
        return 0.0, -turn_speed
    return 0.0, 0.0


def encoder_drive_sequence_complete(
    elapsed_sec: float,
    *,
    phase_duration_sec: float,
    stop_publish_sec: float,
) -> bool:
    return elapsed_sec >= 4.0 * phase_duration_sec + stop_publish_sec
