"""Offline tests for dig_sequence parameter / completion helpers."""

from backend.dig_sequence_params import (
    encoder_forward_target_reached,
    encoder_returned_home,
    ir_bucket_step_gate_released,
    ir_setup_stop_eq,
    ir_setup_stop_le,
    merge_timed_drive_ms,
    ros_param_non_negative_int,
    timed_leg_complete,
)


def test_ir_setup_stop_eq_exact_only():
    assert ir_setup_stop_eq(17, 17) is True
    assert ir_setup_stop_eq(16, 17) is False


def test_ir_setup_stop_le_ignores_unread_negative_one():
    stop, above = ir_setup_stop_le(-1, 17, 20, 20, False)
    assert stop is False and above is False


def test_ir_setup_stop_le_high_then_at_target():
    stop, above = ir_setup_stop_le(70, 17, 20, 20, False)
    assert stop is False and above is True
    stop2, above2 = ir_setup_stop_le(17, 17, 20, 20, above)
    assert stop2 is True and above2 is True


def test_ir_setup_stop_le_bucket_step_primes_below_target_edge():
    # Never saw iv > 17 but bucket stepped 21 > 20
    stop, above = ir_setup_stop_le(16, 17, 21, 20, False)
    assert stop is True and above is False


def test_ir_bucket_step_gate_disabled_when_min_drop_zero():
    assert ir_bucket_step_gate_released(10, -1, 0, elapsed_sec=0.0, timeout_sec=1.0) is True


def test_ir_bucket_step_gate_releases_when_ir_drops():
    assert ir_bucket_step_gate_released(68, 70, 2, elapsed_sec=0.0, timeout_sec=10.0) is True
    assert ir_bucket_step_gate_released(69, 70, 2, elapsed_sec=0.0, timeout_sec=10.0) is False


def test_ir_bucket_step_gate_negative_iv_blocks():
    assert ir_bucket_step_gate_released(-1, 70, 2, elapsed_sec=0.0, timeout_sec=99.0) is False


def test_ir_bucket_step_gate_anchor_negative_requires_timeout():
    assert ir_bucket_step_gate_released(50, -1, 2, elapsed_sec=0.0, timeout_sec=10.0) is False
    assert ir_bucket_step_gate_released(50, -1, 2, elapsed_sec=10.0, timeout_sec=10.0) is True


def test_ir_bucket_step_gate_timeout_releases_without_drop():
    assert ir_bucket_step_gate_released(70, 70, 5, elapsed_sec=11.0, timeout_sec=10.0) is True


def test_ros_param_coerces_numeric_string_and_float():
    assert ros_param_non_negative_int("5000") == 5000
    assert ros_param_non_negative_int(5000.4) == 5000
    assert ros_param_non_negative_int(5000.6) == 5001


def test_ros_param_bool_and_garbage_are_zero():
    assert ros_param_non_negative_int(True) == 0
    assert ros_param_non_negative_int(False) == 0
    assert ros_param_non_negative_int("nope") == 0


def test_merge_timed_prefers_explicit_over_legacy():
    assert merge_timed_drive_ms(2000, 5000) == 2000


def test_merge_timed_fallback_to_legacy_when_primary_zero():
    assert merge_timed_drive_ms(0, 4500) == 4500


def test_merge_timed_rejects_negative_as_zero_components():
    assert merge_timed_drive_ms(-100, -50) == 0


def test_timed_leg_not_complete_below_duration():
    assert timed_leg_complete(0.5, 1000) is False


def test_timed_leg_complete_at_exact_threshold():
    assert timed_leg_complete(1.0, 1000) is True


def test_timed_leg_complete_disabled_when_ms_zero():
    assert timed_leg_complete(999.0, 0) is False


def test_encoder_forward_increasing_reaches_tolerance_band():
    assert encoder_forward_target_reached(118, 120, tolerance=5, forward_encoder_increases=True) is True
    assert encoder_forward_target_reached(114, 120, tolerance=5, forward_encoder_increases=True) is False


def test_encoder_forward_decreasing_reaches_tolerance_band():
    assert encoder_forward_target_reached(104, 100, tolerance=5, forward_encoder_increases=False) is True
    assert encoder_forward_target_reached(106, 100, tolerance=5, forward_encoder_increases=False) is False


def test_encoder_home_within_tolerance():
    assert encoder_returned_home(1, tolerance=2) is True
    assert encoder_returned_home(10, tolerance=2) is False
