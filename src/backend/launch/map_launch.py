import launch


from launch_ros.actions import Node

# ros2 launch sim launch.py world:=~/Documents/robotics/gz_worlds/arena1.world gui:=false

def generate_launch_description():
    
    map_odom_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=[
            '0', '0', '0', '0', '0', '0',
            'map', 'odom'
        ],
        parameters=[{
            'use_sim_time': True
        }]
    )

    mapper = Node(
        package='backend',
        executable='global_mapper',
        output='screen',
        parameters=[{
            'use_sim_data': False,
            'map_on': True,
            'use_sim_time': True
        }]
    )

    costmapper = Node(
        package='backend',
        executable='global_costmapper',
        output='screen',
        parameters=[{
            'use_sim_time': True
        }]
    )

    return launch.LaunchDescription([
        map_odom_tf,
        mapper,
        costmapper,
    ])
