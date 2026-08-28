from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import (
    Command,
    LaunchConfiguration,
    PathJoinSubstitution,
)

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    publish_joint_states = LaunchConfiguration('publish_joint_states')

    xacro_file = PathJoinSubstitution([
        FindPackageShare('my_first_ros_py'),
        'urdf',
        'physical_ai_robot.urdf.xacro',
    ])

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
                'use_sim_time': ParameterValue(
                    use_sim_time,
                    value_type=bool,
                ),
            },
        ],
    )

    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
        condition=IfCondition(publish_joint_states),
        parameters=[
            {
                'robot_description': robot_description,
                'use_sim_time': ParameterValue(
                    use_sim_time,
                    value_type=bool,
                ),
            },
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use the clock published by the simulator.',
        ),
        DeclareLaunchArgument(
            'publish_joint_states',
            default_value='true',
            description='Run the non-simulated joint state publisher.',
        ),
        robot_state_publisher_node,
        joint_state_publisher_node,
    ])
