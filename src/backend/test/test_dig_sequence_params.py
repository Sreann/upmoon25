"""Offline tests for dig_sequence parameter / completion helpers."""

from backend.dig_sequence_params import (
    encoder_forward_target_reached,
    encoder_returned_home,
    merge_timed_drive_ms,
    timed_leg_complete,
)


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
