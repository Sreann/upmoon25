from pathlib import Path
import sys
from unittest.mock import patch

LUNAR_SRC = Path(__file__).resolve().parents[3] / "lunar" / "src"
if str(LUNAR_SRC) not in sys.path:
    sys.path.insert(0, str(LUNAR_SRC))

from lunar.cli import ControlTarget, _parse_subsystems, resolve_control_topic
from lunar.keyboard_topics import KEYBOARD_PUBLISHER_TOPICS, KEYBOARD_SENSOR_TOPICS, clamp_pan_angle
from lunar.keyboard_tui import ARDUINO_CAM_HEIGHT_PIN, ARDUINO_PAN_PIN, RobotActuators, _clamp, _clamp_float


class FakeSerial:
    def __init__(self):
        self.writes = []
        self.flushed = 0
        self.closed = False

    def write(self, payload):
        self.writes.append(payload)

    def flush(self):
        self.flushed += 1

    def close(self):
        self.closed = True


def test_parse_subsystems_all_and_empty_enable_everything():
    expected = {"drive", "camera-height", "pan", "bucket-pos", "bucket-vel", "conveyor"}

    assert _parse_subsystems("") == expected
    assert _parse_subsystems("all") == expected


def test_parse_subsystems_aliases_and_ignores_unknown_values():
    assert _parse_subsystems("cam,bucket,bucket_vel,conveyor,garbage") == {
        "camera-height",
        "bucket-pos",
        "bucket-vel",
        "conveyor",
    }


def test_keyboard_clamps_integer_and_float_values():
    assert _clamp(-1, 0, 100) == 0
    assert _clamp(101, 0, 100) == 100
    assert _clamp(42, 0, 100) == 42
    assert _clamp_float(-0.5, 0.0, 1.0) == 0.0
    assert _clamp_float(1.5, 0.0, 1.0) == 1.0
    assert _clamp_float(0.25, 0.0, 1.0) == 0.25


def test_direct_serial_camera_height_clamps_and_writes_arduino_pin():
    actuator = RobotActuators()
    actuator.serial = FakeSerial()

    assert actuator.set_camera_height(120) is True

    assert actuator.serial.writes == [f"{ARDUINO_CAM_HEIGHT_PIN}:100\n".encode("utf-8")]
    assert actuator.serial.flushed == 1


def test_direct_serial_pan_clamps_to_safe_range_and_writes_arduino_pin():
    actuator = RobotActuators()
    actuator.serial = FakeSerial()

    assert actuator.set_pan(-20) is True

    expected = clamp_pan_angle(-20)
    assert actuator.serial.writes == [f"{ARDUINO_PAN_PIN}:{expected}\n".encode("utf-8")]
    assert actuator.serial.flushed == 1


def test_keyboard_publisher_topic_contract():
    """Outbound topics must stay aligned with frontend/backend subscribers."""
    assert KEYBOARD_PUBLISHER_TOPICS == {
        "drive": "cmd/velocity",
        "camera-height": "/cmd/camera_height",
        "pan": "/cmd/pan",
        "bucket-pos": "/cmd/bucket_pos",
        "bucket-vel": "/cmd/bucket_vel",
        "conveyor": "/cmd/conveyor",
    }


def test_actuator_enum_strings_are_keyboard_publisher_keys():
    """`lunar act` uses Actuator enum values that must match keyboard_topics keys."""
    from lunar.cli import Actuator

    kt = KEYBOARD_PUBLISHER_TOPICS
    for actuator in (
        Actuator.BUCKET_VEL,
        Actuator.BUCKET_POS,
        Actuator.CONVEYOR,
        Actuator.CAMERA_HEIGHT,
        Actuator.PAN,
    ):
        assert actuator.value in kt, f"missing keyboard_topics key for {actuator!r}"


def test_keyboard_sensor_subscription_topic_contract():
    """Telemetry topics the keyboard TUI listens on (IR + encoders + debug frame)."""
    assert KEYBOARD_SENSOR_TOPICS == {
        "ir_general": "/sensor/ir",
        "ir_right": "/sensor/ir/right",
        "ir_left": "/sensor/ir/left",
        "encoder_left": "/sensor/encoder/left",
        "encoder_right": "/sensor/encoder/right",
        "encoder_telemetry": "/sensor/encoder/telemetry",
    }


def test_encoder_telemetry_callback_updates_all_debug_fields():
    actuator = RobotActuators()
    msg = type("Msg", (), {"data": [3, 1, 2, 0, 14, 9]})()

    actuator._on_encoder_telemetry(msg)

    assert actuator.telemetry["enc_pin_right"] == 3
    assert actuator.telemetry["enc_pin_left"] == 1
    assert actuator.telemetry["enc_dec_right"] == 2
    assert actuator.telemetry["enc_dec_left"] == 0
    assert actuator.telemetry["enc_bad_right"] == 14
    assert actuator.telemetry["enc_bad_left"] == 9


def test_encoder_telemetry_callback_ignores_short_payload():
    actuator = RobotActuators()
    before = dict(actuator.telemetry)
    msg = type("Msg", (), {"data": [1, 2, 3]})()

    actuator._on_encoder_telemetry(msg)

    assert actuator.telemetry == before


def test_resolve_control_topic_explicit_sim_and_robot():
    assert resolve_control_topic(ControlTarget.SIM) == "/cmd_vel"
    assert resolve_control_topic(ControlTarget.ROBOT) == "cmd/velocity"


@patch("lunar.cli._subscriber_count")
def test_resolve_control_topic_auto_robot_stack_only(mock_sub):
    mock_sub.side_effect = lambda topic: 1 if topic == "cmd/velocity" else 0
    assert resolve_control_topic(ControlTarget.AUTO) == "cmd/velocity"
    assert mock_sub.call_count == 2


@patch("lunar.cli._subscriber_count")
def test_resolve_control_topic_auto_sim_only(mock_sub):
    mock_sub.side_effect = lambda topic: 1 if topic == "/cmd_vel" else 0
    assert resolve_control_topic(ControlTarget.AUTO) == "/cmd_vel"


@patch("lunar.cli._subscriber_count")
def test_resolve_control_topic_auto_both_subscribed_prefers_robot(mock_sub):
    mock_sub.return_value = 1
    assert resolve_control_topic(ControlTarget.AUTO) == "cmd/velocity"


@patch("lunar.cli._subscriber_count")
def test_resolve_control_topic_auto_neither_defaults_to_robot_topic(mock_sub):
    mock_sub.return_value = 0
    assert resolve_control_topic(ControlTarget.AUTO) == "cmd/velocity"


def test_stop_all_attempts_drive_bucket_and_conveyor_stop():
    calls = []
    actuator = RobotActuators()
    setattr(
        actuator,
        "set_drive",
        lambda linear, angular: calls.append(("drive", linear, angular)) or True,
    )
    setattr(actuator, "set_bucket_vel", lambda value: calls.append(("bucket-vel", value)) or True)
    setattr(actuator, "set_conveyor", lambda value: calls.append(("conveyor", value)) or True)

    actuator.stop_all()

    assert calls == [
        ("drive", 0.0, 0.0),
        ("bucket-vel", 0),
        ("conveyor", 0),
    ]
