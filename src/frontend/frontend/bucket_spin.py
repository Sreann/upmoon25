#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int16
import time
from pathlib import Path

import serial.tools.list_ports

from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.exceptions import ModbusIOException

SPEED_FACTOR = 30

RAMP = 0xA0 # 10rpm/s
CONTROL_HZ = 30.0
CMD_TIMEOUT_SEC = 0.75
ACCEL_CMD_PER_SEC = 90.0

STARTING_TORQUE = 0xFF # Range: 0x00 - 0xFF
MODBUS_PORT_CANDIDATES = ['/dev/ttyUSB1', '/dev/ttyUSB0']
CP2102_VID = 0x10C4
CP2102_PID = 0xEA60

'''
    This node operates the bucket chain. 

    Subscrpitions:
    /cmd/bucket_vel - Int16, the desired bucket chain speed in RPM
'''
class MotorControllerNode(Node):
    def __init__(self):
        super().__init__('bld515c_motor_controller')
        self.port = self._find_port()
        if self.port is None:
            raise RuntimeError('No Modbus motor controller serial port detected.')

        # Modbus config
        self.client = ModbusClient(
            method='rtu',
            port=self.port,
            baudrate=9600,
            stopbits=1,
            bytesize=8,
            parity='N',
            timeout=1
        )
        self.slave_id = 1  # Modbus address of the motor controller
        self.current_rpm = 0
        self.is_enabled = False # Track if the motor is enabled/disabled
        self.target_cmd = 0.0
        self.current_cmd = 0.0
        self.last_cmd_time = time.monotonic()
        self.last_tick_time = time.monotonic()

        # Motor control registers
        self.REG_CONTROL = 0x8106
        self.REG_SPEED = 0x8110

        # Init Modbus connection
        if not self.client.connect():
            raise RuntimeError(f'Failed to connect to motor controller on {self.port}.')
        
        # set starting torque
        self.client.write_register(0x8109, STARTING_TORQUE, unit=1)

        acc_dec_word = (RAMP << 8) | RAMP  # High byte first
        self.client.write_register(0x810B, acc_dec_word, unit=1)


        # Subscribe to RPM commands
        self.subscriber = self.create_subscription(
            Int16,
            'cmd/bucket_vel',
            self.rpm_callback,
            10
        )
        self.timer = self.create_timer(1.0 / CONTROL_HZ, self.control_tick)
        self.get_logger().info('Bucket Chain Motor controller node initialized.')

    def _find_port(self):
        for path in MODBUS_PORT_CANDIDATES:
            if Path(path).exists():
                return path

        try:
            for port in serial.tools.list_ports.comports():
                if port.vid == CP2102_VID and port.pid == CP2102_PID:
                    return port.device
        except Exception:
            pass

        return None

    def rpm_callback(self, msg: Int16):
        self.target_cmd = float(msg.data)
        self.last_cmd_time = time.monotonic()

    def _step_toward(self, current: float, target: float, max_delta: float) -> float:
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
            self.target_cmd = 0.0

        self.current_cmd = self._step_toward(
            self.current_cmd,
            self.target_cmd,
            ACCEL_CMD_PER_SEC * dt,
        )
        self._apply_cmd(self.current_cmd)

    def _apply_cmd(self, cmd: float):
        rounded_cmd = int(round(cmd))
        rpm = int(SPEED_FACTOR * abs(rounded_cmd))
        direction = 1 if rounded_cmd < 0 else 0  # 1 = reverse, 0 = forward

        if rounded_cmd == 0:
            if self.current_rpm != 0 or self.is_enabled:
                self.current_rpm = 0
                self.set_motor_speed(0)
                self.set_motor_control(False, 0)
            return

        if rpm == self.current_rpm and self.is_enabled:
            return

        try:
            self.current_rpm = rpm
            self.set_motor_control(True, direction)
            self.set_motor_speed(rpm)
        except ModbusIOException as e:
            self.get_logger().error(f'Modbus IO error: {e}')
        except Exception as e:
            self.get_logger().error(f'Unexpected error: {e}')


    def set_motor_control(self, enable: bool, direction: int):
        # Build control byte:
        # Bit 0 = EN (1: enable)
        # Bit 1 = FR (1: reverse)
        control_byte = 0
        if enable:
            self.is_enabled = True
            control_byte |= 0x01  # Enable motor
        else:
            self.is_enabled = False
        if direction == 1:
            control_byte |= 0x02  # Reverse

        control_word = (0x03 << 8) | control_byte  # Internal control + internal speed mode?

        result = self.client.write_register(self.REG_CONTROL, control_word, unit=self.slave_id)

        if result.isError():
            self.get_logger().warn(f'Failed to write motor control: {control_word:#04x}')

    def set_motor_speed(self, rpm: int):
        result = self.client.write_register(self.REG_SPEED, rpm, unit=self.slave_id)
        if result.isError():
            self.get_logger().warn(f'Failed to set speed to {rpm} RPM')

    # def ramp_speed_to(self, target_rpm: int, direction: int, step: int = RAMP_STEP, delay: float = RAMP_DELAY):
    #     start_rpm = self.current_rpm
    #     self.current_rpm = target_rpm

    #     self.set_motor_control(enable=True, direction=direction)

    #     for rpm in range(start_rpm, target_rpm + 1, step):
    #         self.set_motor_speed(rpm)
    #         time.sleep(delay)

    #     # Ensure exact target RPM is set
    #     self.set_motor_speed(target_rpm)


    def destroy_node(self):
        self.client.close()
        self.get_logger().info('Closed Modbus connection.')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = MotorControllerNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        if node is not None:
            node.get_logger().info('Shutting down...')
    except Exception as e:
        logger = node.get_logger() if node is not None else rclpy.logging.get_logger('bucket_spin')
        logger.error(str(e))
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
