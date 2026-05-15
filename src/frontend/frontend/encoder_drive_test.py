"""Timed open-loop drive for encoder bring-up: fwd/rev/left/right, then stop."""

from __future__ import annotations

import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node

from frontend.encoder_drive_sequence import (
    drive_cmd_for_encoder_drive_elapsed,
    encoder_drive_sequence_complete,
)

PUBLISH_HZ = 20.0


class EncoderDriveTest(Node):
    def __init__(self) -> None:
        super().__init__('encoder_drive_test')
        self.declare_parameter('linear_speed', 35.0)
        self.declare_parameter('turn_speed', 30.0)
        self.declare_parameter('phase_duration_sec', 5.0)
        self.declare_parameter('stop_publish_sec', 0.8)

        self._pub = self.create_publisher(Twist, 'cmd/velocity', 10)
        self._t0 = time.monotonic()
        self._finished_logged = False

        period = 1.0 / PUBLISH_HZ
        self._timer = self.create_timer(period, self._tick)

    def _tick(self) -> None:
        speed = float(self.get_parameter('linear_speed').value)
        turn = float(self.get_parameter('turn_speed').value)
        phase = float(self.get_parameter('phase_duration_sec').value)
        tail = float(self.get_parameter('stop_publish_sec').value)

        elapsed = time.monotonic() - self._t0
        msg = Twist()
        msg.linear.x, msg.angular.z = drive_cmd_for_encoder_drive_elapsed(
            elapsed,
            linear_speed=speed,
            turn_speed=turn,
            phase_duration_sec=phase,
        )
        if msg.linear.x == 0.0 and msg.angular.z == 0.0 and elapsed >= 4.0 * phase:
            if not self._finished_logged:
                self.get_logger().info(
                    f'Encoder drive test finished: forward/backward/left/right {phase:.1f}s each; publishing stop.'
                )
                self._finished_logged = True

        self._pub.publish(msg)

        if encoder_drive_sequence_complete(
            elapsed,
            phase_duration_sec=phase,
            stop_publish_sec=tail,
        ):
            self._timer.cancel()
            rclpy.shutdown()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = EncoderDriveTest()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
