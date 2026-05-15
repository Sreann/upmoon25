"""Nav autonomy stack plus ``dig_sequence`` waiting on ``/autonomy/dig_arm``.

Includes ``nav_autonomy_mission.launch.py`` and ``dig_sequence`` with
``wait_for_nav_dig_arm:=true``. Override encoder target for your rig::

  ros2 launch backend nav_autonomy_with_dig.launch.py dig_encoder_target:=600
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    nav_stack = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("backend"), "launch", "nav_autonomy_mission.launch.py")
        )
    )
    dig_enc = DeclareLaunchArgument("dig_encoder_target", default_value="500")
    dig = Node(
        package="backend",
        executable="dig_sequence",
        output="screen",
        parameters=[
            {
                "wait_for_nav_dig_arm": True,
                "calibrated_rotary": LaunchConfiguration("dig_encoder_target"),
            }
        ],
    )
    return LaunchDescription([dig_enc, nav_stack, dig])
