from frontend.encoder_drive_sequence import (
    encoder_drive_sequence_complete,
    linear_x_for_encoder_drive_elapsed,
)


def test_linear_x_forward_phase_uses_positive_speed():
    assert (
        linear_x_for_encoder_drive_elapsed(
            0.0,
            linear_speed=35.0,
            phase_duration_sec=5.0,
        )
        == 35.0
    )
    assert (
        linear_x_for_encoder_drive_elapsed(
            4.99,
            linear_speed=35.0,
            phase_duration_sec=5.0,
        )
        == 35.0
    )


def test_linear_x_backward_phase_uses_negative_speed():
    assert (
        linear_x_for_encoder_drive_elapsed(
            5.0,
            linear_speed=35.0,
            phase_duration_sec=5.0,
        )
        == -35.0
    )
    assert (
        linear_x_for_encoder_drive_elapsed(
            9.99,
            linear_speed=35.0,
            phase_duration_sec=5.0,
        )
        == -35.0
    )


def test_linear_x_after_two_phases_is_zero():
    assert (
        linear_x_for_encoder_drive_elapsed(
            10.0,
            linear_speed=35.0,
            phase_duration_sec=5.0,
        )
        == 0.0
    )
    assert (
        linear_x_for_encoder_drive_elapsed(
            99.0,
            linear_speed=35.0,
            phase_duration_sec=5.0,
        )
        == 0.0
    )


def test_sequence_complete_requires_both_phases_plus_tail():
    phase = 5.0
    tail = 0.8
    assert not encoder_drive_sequence_complete(
        10.7,
        phase_duration_sec=phase,
        stop_publish_sec=tail,
    )
    assert encoder_drive_sequence_complete(
        10.8,
        phase_duration_sec=phase,
        stop_publish_sec=tail,
    )
    assert encoder_drive_sequence_complete(
        11.0,
        phase_duration_sec=phase,
        stop_publish_sec=tail,
    )
