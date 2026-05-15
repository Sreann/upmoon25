"""Encoder bring-up: Arduino (IR + encoders), Sabertooth drive, timed forward/back run."""

from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch_ros.actions import Node


def generate_launch_description():
    drive_motors_node = Node(
        package='frontend',
        executable='drive_motors',
        name='drive_motors_node',
        output='screen',
    )
    arduino_driver_node = Node(
        package='frontend',
        executable='arduino_driver',
        name='arduino_driver_node',
        output='screen',
    )
    encoder_drive_test_node = Node(
        package='frontend',
        executable='encoder_drive_test',
        name='encoder_drive_test_node',
        output='screen',
        parameters=[{
            'linear_speed': 35.0,
            'phase_duration_sec': 5.0,
            'stop_publish_sec': 0.8,
        }],
    )

    return LaunchDescription([
        drive_motors_node,
        arduino_driver_node,
        encoder_drive_test_node,
        RegisterEventHandler(
            OnProcessExit(
                target_action=encoder_drive_test_node,
                on_exit=[
                    EmitEvent(event=Shutdown(reason='Encoder drive test sequence finished.')),
                ],
            )
        ),
    ])
