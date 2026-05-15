"""Offline-testable helpers for dig_sequence drive completion (used by dig_sequence_controller)."""

from __future__ import annotations


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


def ir_setup_stop_eq(ir_value: int, ir_target: int) -> bool:
    """Legacy IR setup: stop only on exact integer equality."""
    return int(ir_value) == int(ir_target)


def ir_setup_stop_le(
    ir_value: int,
    ir_target: int,
    bucket_pos_commanded: int,
    bucket_start_pos: int,
    was_above_target: bool,
) -> tuple[bool, bool]:
    """
    Typical dig: lowering the bucket lowers the IR reading toward ``ir_target``
    (e.g. IR ~70 initially, crosses down through ``ir_target`` 17).

    Stop when IR is **at or below** ``ir_target`` after priming: we observed IR **above``
    ``ir_target`` at least once, or ``bucket_pos`` has stepped past ``bucket_start_pos``.
    ``ir_value < 0`` is treated as no reading yet (startup sentinel -1 won't stop).

    Returns ``(stop_lowering_now, new_was_above_target)``.
    """
    iv = int(ir_value)
    it = int(ir_target)
    new_above = bool(was_above_target) or (iv > it)
    if iv < 0:
        return False, new_above
    bp = int(bucket_pos_commanded)
    bs = int(bucket_start_pos)
    primed = new_above or (bp > bs)
    return bool(iv <= it and primed), new_above


def ir_bucket_step_gate_released(
    ir_value: int,
    anchor_ir_before_step: int,
    min_drop: int,
    *,
    elapsed_sec: float,
    timeout_sec: float,
) -> bool:
    """
    After ``cmd/bucket_pos`` incremented, defer the **next** step until IR has moved deeper by at
    least ``min_drop`` points relative to the reading **before** that command (typically IR falls
    as the bucket lowers). If there was no valid IR before the step (``anchor < 0``), only
    ``timeout_sec`` releases the gate.

    Disable by passing ``min_drop <= 0`` (caller skips the wait entirely).
    """
    d = max(0, int(min_drop))
    if d <= 0:
        return True
    if float(elapsed_sec) >= float(timeout_sec):
        return True
    iv = int(ir_value)
    if iv < 0:
        return False
    anchor = int(anchor_ir_before_step)
    if anchor < 0:
        return False
    return iv <= anchor - d


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
