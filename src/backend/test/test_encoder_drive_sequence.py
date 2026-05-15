from frontend.encoder_drive_sequence import (
    drive_cmd_for_encoder_drive_elapsed,
    encoder_drive_sequence_complete,
)


def test_drive_cmd_forward_phase_uses_positive_linear():
    assert drive_cmd_for_encoder_drive_elapsed(
            0.0,
            linear_speed=35.0,
            turn_speed=30.0,
            phase_duration_sec=5.0,
        ) == (35.0, 0.0)
    assert drive_cmd_for_encoder_drive_elapsed(
            4.99,
            linear_speed=35.0,
            turn_speed=30.0,
            phase_duration_sec=5.0,
        ) == (35.0, 0.0)


def test_drive_cmd_backward_phase_uses_negative_linear():
    assert drive_cmd_for_encoder_drive_elapsed(
            5.0,
            linear_speed=35.0,
            turn_speed=30.0,
            phase_duration_sec=5.0,
        ) == (-35.0, 0.0)
    assert drive_cmd_for_encoder_drive_elapsed(
            9.99,
            linear_speed=35.0,
            turn_speed=30.0,
            phase_duration_sec=5.0,
        ) == (-35.0, 0.0)


def test_drive_cmd_left_turn_phase_uses_positive_angular():
    assert drive_cmd_for_encoder_drive_elapsed(
            10.0,
            linear_speed=35.0,
            turn_speed=30.0,
            phase_duration_sec=5.0,
        ) == (0.0, 30.0)
    assert drive_cmd_for_encoder_drive_elapsed(
            14.99,
            linear_speed=35.0,
            turn_speed=30.0,
            phase_duration_sec=5.0,
        ) == (0.0, 30.0)


def test_drive_cmd_right_turn_phase_uses_negative_angular():
    assert drive_cmd_for_encoder_drive_elapsed(
            15.0,
            linear_speed=35.0,
            turn_speed=30.0,
            phase_duration_sec=5.0,
        ) == (0.0, -30.0)
    assert drive_cmd_for_encoder_drive_elapsed(
            19.99,
            linear_speed=35.0,
            turn_speed=30.0,
            phase_duration_sec=5.0,
        ) == (0.0, -30.0)


def test_drive_cmd_after_four_phases_is_zero():
    assert drive_cmd_for_encoder_drive_elapsed(
            20.0,
            linear_speed=35.0,
            turn_speed=30.0,
            phase_duration_sec=5.0,
        ) == (0.0, 0.0)
    assert drive_cmd_for_encoder_drive_elapsed(
            99.0,
            linear_speed=35.0,
            turn_speed=30.0,
            phase_duration_sec=5.0,
        ) == (0.0, 0.0)


def test_sequence_complete_requires_all_phases_plus_tail():
    phase = 5.0
    tail = 0.8
    assert not encoder_drive_sequence_complete(
        20.7,
        phase_duration_sec=phase,
        stop_publish_sec=tail,
    )
    assert encoder_drive_sequence_complete(
        20.8,
        phase_duration_sec=phase,
        stop_publish_sec=tail,
    )
    assert encoder_drive_sequence_complete(
        21.0,
        phase_duration_sec=phase,
        stop_publish_sec=tail,
    )
