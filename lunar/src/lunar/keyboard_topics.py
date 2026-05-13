"""Canonical ROS topic names for lunar keyboard teleop (publish + subscribe sides).

Used by the Textual keyboard TUI, legacy raw subsystem keyboard, and offline contract tests.
"""

from __future__ import annotations

# Outbound commands (geometry_msgs/Twist on drive; std_msgs/Int16 on others).
KEYBOARD_PUBLISHER_TOPICS: dict[str, str] = {
    "drive": "cmd/velocity",
    "camera-height": "/cmd/camera_height",
    "pan": "/cmd/pan",
    "bucket-pos": "/cmd/bucket_pos",
    "bucket-vel": "/cmd/bucket_vel",
    "conveyor": "/cmd/conveyor",
}

# Inbound telemetry consumed by the keyboard TUI for dashboard/IR/encoder display.
KEYBOARD_SENSOR_TOPICS: dict[str, str] = {
    "ir_general": "/sensor/ir",
    "ir_right": "/sensor/ir/right",
    "ir_left": "/sensor/ir/left",
    "encoder_left": "/sensor/encoder/left",
    "encoder_right": "/sensor/encoder/right",
}
