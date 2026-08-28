from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package_share = FindPackageShare('my_first_ros_py')

    xacro_file = PathJoinSubstitution([
        package_share,
        'urdf',
        'physical_ai_robot.urdf.xacro',
    ])
    bridge_config = PathJoinSubstitution([
        package_share,
        'config',
        'gazebo_bridge.yaml',
    ])

    goal_x = LaunchConfiguration('goal_x')
    goal_y = LaunchConfiguration('goal_y')

    robot_description = ParameterValue(
        Command([
            'xacro ',
            xacro_file,
        ]),
        value_type=str,
    )

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            {
                'robot_description': robot_description,
                'use_sim_time': True,
            },
        ],
    )

    bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        parameters=[
            {
                'config_file': bridge_config,
            },
        ],
    )

    controller_node = Node(
        package='my_first_ros_py',
        executable='go_to_goal_controller',
        name='go_to_goal_controller',
        output='screen',
        parameters=[
            {
                'use_sim_time': True,
                'goal_x': ParameterValue(goal_x, value_type=float),
                'goal_y': ParameterValue(goal_y, value_type=float),
            },
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'goal_x',
            default_value='2.0',
            description='Target X position in meters.',
        ),
        DeclareLaunchArgument(
            'goal_y',
            default_value='1.0',
            description='Target Y position in meters.',
        ),
        robot_state_publisher_node,
        bridge_node,
        controller_node,
    ])
