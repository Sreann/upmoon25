"""
Autonomous dig sequence for lunar `run dig`.

Runs once after IR/bucket calibration, then repeats drive-forward → drive-back →
dump → bucket bump until the cycle counter exceeds max_cycles (see params).

If IR reaches the target first, bucket chain stops for the drive phases. If the bucket
position safety cap is reached first (without IR), bucket chain stays on until the full
sequence ends (abort / timeout / normal completion).

Prerequisite: frontend stack publishing /sensor/ir, wheel encoders, and
subscribed to cmd/velocity, cmd/bucket_pos, cmd/bucket_vel, cmd/conveyor.
"""

from __future__ import annotations

from enum import Enum

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import Int16, Int32


class DigState(Enum):
    SETUP_IR = 0
    DRIVE_FORWARD = 1
    DRIVE_BACK = 2
    CONVEYOR_DUMP = 3
    DONE = 5


class DigSequenceController(Node):
    def __init__(self):
        super().__init__("dig_sequence")

        self.declare_parameter("calibrated_rotary", 0)
        self.declare_parameter("encoder_side", "left")
        self.declare_parameter("encoder_tolerance", 2)
        self.declare_parameter("forward_encoder_increases", True)
        self.declare_parameter("ir_target", 17)
        self.declare_parameter("bucket_start_pos", 20)
        self.declare_parameter("bucket_safety_stop", 34)
        self.declare_parameter("bucket_chain_speed", 100)
        self.declare_parameter("max_cycles_le", 5)
        self.declare_parameter("forward_linear", 35.0)
        self.declare_parameter("backward_linear", -35.0)
        self.declare_parameter("control_dt", 0.05)
        self.declare_parameter("ir_bucket_step_every_sec", 0.2)
        self.declare_parameter("conveyor_seconds", 5.0)
        self.declare_parameter("phase_timeout_sec", 180.0)

        self.calibrated_rotary = int(self.get_parameter("calibrated_rotary").value)
        enc_side = str(self.get_parameter("encoder_side").value).strip().lower()
        if enc_side not in {"left", "right"}:
            self.get_logger().warn("encoder_side must be 'left' or 'right'; defaulting to 'left'.")
            enc_side = "left"
        self.encoder_topic = f"/sensor/encoder/{enc_side}"

        self.encoder_tolerance = max(0, int(self.get_parameter("encoder_tolerance").value))
        self.forward_encoder_increases = bool(self.get_parameter("forward_encoder_increases").value)
        self.ir_target = int(self.get_parameter("ir_target").value)
        self.bucket_start_pos = int(self.get_parameter("bucket_start_pos").value)
        self.bucket_safety_stop = int(self.get_parameter("bucket_safety_stop").value)
        self.bucket_chain_speed = int(self.get_parameter("bucket_chain_speed").value)
        self.max_cycles_le = int(self.get_parameter("max_cycles_le").value)
        self.forward_linear = float(self.get_parameter("forward_linear").value)
        self.backward_linear = float(self.get_parameter("backward_linear").value)
        self.control_dt = float(self.get_parameter("control_dt").value)
        self.ir_bucket_step_every_sec = float(self.get_parameter("ir_bucket_step_every_sec").value)
        self.conveyor_seconds = float(self.get_parameter("conveyor_seconds").value)
        self.phase_timeout_sec = float(self.get_parameter("phase_timeout_sec").value)

        if self.calibrated_rotary <= 0:
            raise RuntimeError("Parameter 'calibrated_rotary' must be set to a positive tick target.")

        sens_qos = QoSProfile(depth=3, reliability=2, history=1, durability=2)

        self.pub_vel = self.create_publisher(Twist, "cmd/velocity", 10)
        self.pub_bucket_pos = self.create_publisher(Int16, "cmd/bucket_pos", 10)
        self.pub_bucket_vel = self.create_publisher(Int16, "cmd/bucket_vel", 10)
        self.pub_conveyor = self.create_publisher(Int16, "cmd/conveyor", 10)

        self.ir_value = -1
        self.encoder_value = 0

        self.create_subscription(Int16, "/sensor/ir", self._on_ir, sens_qos)
        self.create_subscription(Int32, self.encoder_topic, self._on_encoder, sens_qos)

        self.state = DigState.SETUP_IR
        self.phase_clock = self.get_clock().now()
        self.ir_last_step_time = self.get_clock().now()
        self.conveyor_until = None
        self._conveyor_end_applied = False

        self.bucket_pos_commanded = self.bucket_start_pos
        self.cycle_counter = 0
        self.setup_complete = False
        # True if setup exited via bucket_safety_stop: dig motor stays on until sequence ends (not IR-hit path).
        self.keep_bucket_chain_until_done = False

        self.timer = self.create_timer(self.control_dt, self._tick)
        self.get_logger().info(
            f"dig_sequence start: IR→{self.ir_target}, bucket {self.bucket_start_pos}..{self.bucket_safety_stop}, "
            f"encoder target {self.calibrated_rotary} on {self.encoder_topic}, repeat while counter<={self.max_cycles_le}"
        )

    def _on_ir(self, msg: Int16) -> None:
        self.ir_value = int(msg.data)

    def _on_encoder(self, msg: Int32) -> None:
        self.encoder_value = int(msg.data)

    def _stop_motion(self) -> None:
        t = Twist()
        self.pub_vel.publish(t)

    def _publish_vel(self, linear_x: float) -> None:
        t = Twist()
        t.linear.x = float(linear_x)
        self.pub_vel.publish(t)

    def _phase_elapsed(self) -> float:
        return (self.get_clock().now() - self.phase_clock).nanoseconds / 1e9

    def _reset_phase_clock(self) -> None:
        self.phase_clock = self.get_clock().now()

    def _abort(self, reason: str) -> None:
        self.get_logger().error(reason)
        self.keep_bucket_chain_until_done = False
        self._stop_motion()
        self.pub_bucket_vel.publish(Int16(data=0))
        self.pub_conveyor.publish(Int16(data=0))
        self.state = DigState.DONE
        self.timer.cancel()
        if rclpy.ok():
            rclpy.shutdown()

    def _tick(self) -> None:
        if self.state == DigState.DONE:
            return

        if self._phase_elapsed() > self.phase_timeout_sec:
            self._abort("Phase timed out.")
            return

        if self.state == DigState.SETUP_IR:
            self._tick_setup_ir()
        elif self.state == DigState.DRIVE_FORWARD:
            self._tick_drive_forward()
        elif self.state == DigState.DRIVE_BACK:
            self._tick_drive_back()
        elif self.state == DigState.CONVEYOR_DUMP:
            self._tick_conveyor()

        if self.keep_bucket_chain_until_done and self.state not in (DigState.SETUP_IR, DigState.DONE):
            self.pub_bucket_vel.publish(Int16(data=int(self.bucket_chain_speed)))

    def _tick_setup_ir(self) -> None:
        if not self.setup_complete:
            self._reset_phase_clock()
            self.bucket_pos_commanded = self.bucket_start_pos
            self.pub_bucket_pos.publish(Int16(data=int(self.bucket_pos_commanded)))
            self.pub_bucket_vel.publish(Int16(data=int(self.bucket_chain_speed)))
            self.setup_complete = True
            self.ir_last_step_time = self.get_clock().now()

        if self.ir_value == self.ir_target:
            self.keep_bucket_chain_until_done = False
            self.get_logger().info("IR target reached; stopping bucket chain.")
            self.pub_bucket_vel.publish(Int16(data=0))
            self._stop_motion()
            self.state = DigState.DRIVE_FORWARD
            self._reset_phase_clock()
            return

        if self.bucket_pos_commanded >= self.bucket_safety_stop:
            self.keep_bucket_chain_until_done = True
            self.get_logger().warn(
                f"Bucket position safety stop at {self.bucket_safety_stop} (IR did not reach {self.ir_target}); "
                "keeping dig motors running until the sequence terminates."
            )
            self._stop_motion()
            self.state = DigState.DRIVE_FORWARD
            self._reset_phase_clock()
            return

        step_elapsed = (self.get_clock().now() - self.ir_last_step_time).nanoseconds / 1e9
        if step_elapsed >= self.ir_bucket_step_every_sec:
            self.bucket_pos_commanded += 1
            self.pub_bucket_pos.publish(Int16(data=int(self.bucket_pos_commanded)))
            self.ir_last_step_time = self.get_clock().now()

    def _tick_drive_forward(self) -> None:
        reached = (
            self.encoder_value >= self.calibrated_rotary - self.encoder_tolerance
            if self.forward_encoder_increases
            else self.encoder_value <= self.calibrated_rotary + self.encoder_tolerance
        )
        if reached:
            self.get_logger().info(f"Encoder {self.encoder_value} reached forward target ~{self.calibrated_rotary}.")
            self._stop_motion()
            self.state = DigState.DRIVE_BACK
            self._reset_phase_clock()
            return
        self._publish_vel(self.forward_linear)

    def _tick_drive_back(self) -> None:
        if abs(self.encoder_value) <= self.encoder_tolerance:
            self.get_logger().info("Encoder returned to ~0.")
            self._stop_motion()
            self.state = DigState.CONVEYOR_DUMP
            self._reset_phase_clock()
            self._conveyor_end_applied = False
            self.pub_conveyor.publish(Int16(data=1))
            self.conveyor_until = self.get_clock().now() + rclpy.duration.Duration(seconds=self.conveyor_seconds)
            return
        self._publish_vel(self.backward_linear)

    def _tick_conveyor(self) -> None:
        if self.conveyor_until is None:
            self.pub_conveyor.publish(Int16(data=1))
            self.conveyor_until = self.get_clock().now() + rclpy.duration.Duration(seconds=self.conveyor_seconds)

        now = self.get_clock().now()
        if now < self.conveyor_until or self._conveyor_end_applied:
            return

        self._conveyor_end_applied = True
        self.pub_conveyor.publish(Int16(data=0))

        self.bucket_pos_commanded += 1
        self.pub_bucket_pos.publish(Int16(data=int(self.bucket_pos_commanded)))
        self.cycle_counter += 1
        self.get_logger().info(
            f"Post-cycle bump: bucket_pos={self.bucket_pos_commanded}, cycle_counter={self.cycle_counter}"
        )

        if self.cycle_counter <= self.max_cycles_le:
            self.get_logger().info("Repeating drive-forward phase.")
            self.state = DigState.DRIVE_FORWARD
            self.conveyor_until = None
            self._reset_phase_clock()
        else:
            self.get_logger().info("Counter exceeded limit; terminating loop.")
            self.keep_bucket_chain_until_done = False
            self._stop_motion()
            self.pub_bucket_vel.publish(Int16(data=0))
            self.pub_conveyor.publish(Int16(data=0))
            self.state = DigState.DONE
            self.timer.cancel()
            if rclpy.ok():
                rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = DigSequenceController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node._stop_motion()
        node.pub_bucket_vel.publish(Int16(data=0))
        node.pub_conveyor.publish(Int16(data=0))
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()
