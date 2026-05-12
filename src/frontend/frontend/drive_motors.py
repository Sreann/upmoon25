# Copyright 2016 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from pysabertooth import Sabertooth
import os
import time
from pathlib import Path
from serial import SerialException
from serial.tools import list_ports

'''
    This node controls the driving of the robot via two Sabertooth motor controllers.
    
    Subscriptions:
    cmd/velocity - Twist, linear.x for forward/backward speed, angular.z for rotation speed
'''
class ReconnectableSaber:
    def __init__(self, logger, port="/dev/ttyUSB0", baudrate=9600, address=128, timeout=0.1, name="Saber", port_resolver=None):
        self.logger = logger
        self.port = port
        self.baudrate = baudrate
        self.address = address
        self.timeout = timeout
        self.name = name
        self.saber = None
        self.port_resolver = port_resolver
        self._connect()

    def _connect(self):
        try:
            resolved_port = self.port_resolver() if self.port_resolver else self.port
            if resolved_port and resolved_port != self.port:
                self.logger.info(f"[{self.name}] Port changed {self.port} -> {resolved_port}")
                self.port = resolved_port
            self.saber = Sabertooth(self.port, baudrate=self.baudrate, address=self.address, timeout=self.timeout)
            self.logger.info(f"[{self.name}] Connected to Sabertooth on {self.port}")
        except Exception as e:
            self.logger.error(f"[{self.name}] Failed to connect on {self.port}: {e}")
            self.saber = None

    def drive(self, motor, speed):
        if not self.saber:
            self._connect()
            if not self.saber:
                return

        try:
            self.saber.drive(motor, speed)
        except SerialException as e:
            self.logger.warn(f"[{self.name}] SerialException on {self.port}: {e}. Reconnecting...")
            self._connect()
        except Exception as e:
            self.logger.error(f"[{self.name}] Unexpected error on {self.port}: {e}")
    
    def stop(self):
        if not self.saber:
            self._connect()
            if not self.saber:
                return

        try:
            self.saber.stop()
        except SerialException as e:
            self.logger.warn(f"[{self.name}] SerialException on {self.port}: {e}. Reconnecting...")
            self._connect()
        except Exception as e:
            self.logger.error(f"[{self.name}] Unexpected error on {self.port}: {e}")


TURN_SPEED = 50.0
DIR = 1.0          # 1 is the correct direction, set to -1 for backwards
CONTROL_HZ = 30.0
CMD_TIMEOUT_SEC = 0.75
LINEAR_ACCEL_PER_SEC = 90.0
ANGULAR_ACCEL_PER_SEC = LINEAR_ACCEL_PER_SEC

ARDUINO_VID = 0x2341
ARDUINO_PID = 0x0043
SABER_PORT_GLOBS = ("/dev/ttyACM*",)


def _port_text(port):
    return " ".join(
        str(value or "")
        for value in (port.description, port.manufacturer, port.product, port.hwid, port.interface)
    ).lower()


def _is_arduino_port(port):
    return port.vid == ARDUINO_VID and port.pid == ARDUINO_PID


def _is_sabertooth_port(port):
    text = _port_text(port)
    return "sabertooth" in text or "dimension engineering" in text


def _symlink_lookup(dirname):
    root = Path(f"/dev/serial/{dirname}")
    if not root.exists():
        return {}

    mapping = {}
    for entry in root.iterdir():
        try:
            resolved = str(entry.resolve())
        except OSError:
            continue
        mapping[resolved] = str(entry)
    return mapping


def _discover_sabertooth_ports():
    explicit_left = os.environ.get("UPMOON25_SABER_LEFT_PORT")
    explicit_right = os.environ.get("UPMOON25_SABER_RIGHT_PORT")
    if explicit_left and explicit_right:
        return [explicit_left, explicit_right]

    by_path = _symlink_lookup("by-path")
    by_id = _symlink_lookup("by-id")

    candidates = []
    seen_devices = set()
    for port in list_ports.comports():
        device = str(port.device)
        if device in seen_devices or _is_arduino_port(port):
            continue
        seen_devices.add(device)

        # Sabertooths enumerate as ACM devices here; by-path names survive ttyACM renumbering.
        if not (_is_sabertooth_port(port) or device.startswith("/dev/ttyACM")):
            continue

        stable = by_path.get(device) or by_id.get(device) or device
        priority = 0 if device in by_path else 1 if device in by_id else 2
        candidates.append((priority, stable))

    if len(candidates) < 2:
        for pattern in SABER_PORT_GLOBS:
            for path in sorted(Path("/").glob(pattern.lstrip("/"))):
                device = str(path)
                if device in seen_devices:
                    continue
                candidates.append((3, device))
                seen_devices.add(device)

    ordered = []
    seen_stable = set()
    for _, stable in sorted(candidates, key=lambda item: (item[0], item[1])):
        if stable in seen_stable:
            continue
        ordered.append(stable)
        seen_stable.add(stable)

    if explicit_left:
        ordered = [explicit_left] + [port for port in ordered if port != explicit_left]
    if explicit_right:
        ordered = [port for port in ordered if port != explicit_right]
        if explicit_left:
            ordered = [explicit_left, explicit_right] + ordered
        else:
            ordered = [explicit_right] + ordered

    return ordered[:2]


def _resolve_sabertooth_port(index, fallback):
    ports = _discover_sabertooth_ports()
    if index < len(ports):
        return ports[index]
    return fallback

class DriveMotors(Node):

    def __init__(self):
        super().__init__('drive_motors')
        
        discovered_ports = _discover_sabertooth_ports()
        self.get_logger().info(
            f"Sabertooth candidates: {', '.join(discovered_ports) if discovered_ports else 'none found'}"
        )

        self.saber_l = ReconnectableSaber(
            self.get_logger(),
            _resolve_sabertooth_port(0, '/dev/ttyACM0'),
            baudrate=9600,
            address=128,
            timeout=0.1,
            name="Left",
            port_resolver=lambda: _resolve_sabertooth_port(0, '/dev/ttyACM0'),
        )
        self.saber_r = ReconnectableSaber(
            self.get_logger(),
            _resolve_sabertooth_port(1, '/dev/ttyACM1'),
            baudrate=9600,
            address=128,
            timeout=0.1,
            name="Right",
            port_resolver=lambda: _resolve_sabertooth_port(1, '/dev/ttyACM1'),
        )

        self.subscription = self.create_subscription(
            Twist,
            'cmd/velocity',
            self.listener_callback,
            10)
        self.subscription  # prevent unused variable warning
        self.target_throttle = 0.0
        self.target_rotation = 0.0
        self.current_throttle = 0.0
        self.current_rotation = 0.0
        self.last_cmd_time = time.monotonic()
        self.last_tick_time = time.monotonic()
        self.create_timer(1.0 / CONTROL_HZ, self.control_tick)
        self.get_logger().info('Successful initialization!')

    def listener_callback(self, msg):
        self.target_throttle = max(-100.0, min(100.0, float(msg.linear.x)))
        self.target_rotation = max(-100.0, min(100.0, float(msg.angular.z)))
        self.last_cmd_time = time.monotonic()

    def _step_toward(self, current, target, max_delta):
        if current < target:
            return min(target, current + max_delta)
        if current > target:
            return max(target, current - max_delta)
        return current

    def control_tick(self):
        now = time.monotonic()
        dt = max(0.0, now - self.last_tick_time)
        self.last_tick_time = now

        if now - self.last_cmd_time > CMD_TIMEOUT_SEC:
            self.target_throttle = 0.0
            self.target_rotation = 0.0

        self.current_throttle = self._step_toward(
            self.current_throttle,
            self.target_throttle,
            LINEAR_ACCEL_PER_SEC * dt,
        )
        self.current_rotation = self._step_toward(
            self.current_rotation,
            self.target_rotation,
            ANGULAR_ACCEL_PER_SEC * dt,
        )

        self.apply_drive(self.current_throttle, self.current_rotation)

    def apply_drive(self, throttle, rotation):
        if abs(throttle) < 0.01:
            throttle = 0.0
        if abs(rotation) < 0.01:
            rotation = 0.0

        if (throttle != 0.0 and rotation == 0.0):
            self.saber_l.drive(1, throttle*DIR)
            self.saber_l.drive(2, -throttle*DIR)
            self.saber_r.drive(1, throttle*DIR)
            self.saber_r.drive(2, -throttle*DIR)
        elif (throttle != 0.0 and rotation != 0.0):
            t1 = throttle
            t2 = throttle

            if (rotation < 0.0): # left turn
                t2 = int(t2 * 0.5)
            elif (rotation > 0.0): # right turn
                t1 = int(t2 * 0.5)

            self.saber_l.drive(1, t1*DIR)
            self.saber_l.drive(2, -t1*DIR)
            self.saber_r.drive(1, t2*DIR)
            self.saber_r.drive(2, -t2*DIR)
        elif (throttle == 0.0 and rotation != 0.0):
            # Use the same magnitude mapping as linear throttle so A/D ramping
            # matches W/S ramping exactly.
            turn_power = abs(rotation)
            if (rotation < 0.0): # left turn
                self.saber_r.drive(1, -turn_power*DIR)
                self.saber_r.drive(2, turn_power*DIR)
                self.saber_l.drive(1, turn_power*DIR)
                self.saber_l.drive(2, -turn_power*DIR)
            elif (rotation > 0.0): # right turn
                self.saber_l.drive(1, -turn_power*DIR)
                self.saber_l.drive(2, turn_power*DIR)
                self.saber_r.drive(1, turn_power*DIR)
                self.saber_r.drive(2, -turn_power*DIR)
        else:
            self.saber_l.stop()
            self.saber_r.stop()


def main(args=None):
    rclpy.init(args=args)
    drive_motors = DriveMotors()
    try:
        rclpy.spin(drive_motors)
    except KeyboardInterrupt:
        pass
    finally:
        drive_motors.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
