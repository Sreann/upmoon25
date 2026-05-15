"""Pure timing logic for encoder bring-up drive (no ROS imports)."""


def linear_x_for_encoder_drive_elapsed(
    elapsed_sec: float,
    *,
    linear_speed: float,
    phase_duration_sec: float,
) -> float:
    """Open-loop cmd/velocity linear.x: forward, reverse, then zero (matches drive_motors scale)."""
    if elapsed_sec < phase_duration_sec:
        return linear_speed
    if elapsed_sec < 2.0 * phase_duration_sec:
        return -linear_speed
    return 0.0


def encoder_drive_sequence_complete(
    elapsed_sec: float,
    *,
    phase_duration_sec: float,
    stop_publish_sec: float,
) -> bool:
    return elapsed_sec >= 2.0 * phase_duration_sec + stop_publish_sec
