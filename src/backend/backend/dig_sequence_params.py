"""Offline-testable helpers for dig_sequence drive completion (used by dig_sequence_controller)."""


def ros_param_non_negative_int(raw: object) -> int:
    """
    Coerce a ROS parameter value to a non-negative int.

    Handles ints, floats, and numeric strings (CLI/YAML quirks). Booleans map to 0.
    """
    if raw is None:
        return 0
    if isinstance(raw, bool):
        return 0
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 0
    if v < 0 or v != v:
        return 0
    return int(round(v))


def merge_timed_drive_ms(timed_drive_ms: int, forward_drive_ms_legacy: int) -> int:
    """Prefer explicit ``timed_drive_ms``; fall back to deprecated ``forward_drive_ms`` when unset."""
    td = max(0, int(timed_drive_ms))
    legacy = max(0, int(forward_drive_ms_legacy))
    return td if td > 0 else legacy


def timed_leg_complete(elapsed_sec: float, timed_drive_ms: int) -> bool:
    """True when ``elapsed_sec`` covers ``timed_drive_ms`` milliseconds."""
    if timed_drive_ms <= 0:
        return False
    return elapsed_sec * 1000.0 >= float(timed_drive_ms)


def encoder_forward_target_reached(
    encoder_value: int,
    calibrated_rotary: int,
    tolerance: int,
    forward_encoder_increases: bool,
) -> bool:
    t = max(0, int(tolerance))
    if forward_encoder_increases:
        return encoder_value >= calibrated_rotary - t
    return encoder_value <= calibrated_rotary + t


def encoder_returned_home(encoder_value: int, tolerance: int) -> bool:
    return abs(int(encoder_value)) <= max(0, int(tolerance))
