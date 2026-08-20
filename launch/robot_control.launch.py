from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    virtual_robot_node = Node(
        package='my_first_ros_py',
        executable='virtual_robot',
        name='virtual_robot',
        output='screen',
    )

    controller_node = Node(
        package='my_first_ros_py',
        executable='go_to_goal_controller',
        name='go_to_goal_controller',
        output='screen',
        parameters=[
            {
                'goal_x': 3.0,
                'goal_y': 2.0,
            },
        ],
    )

    return LaunchDescription([
        virtual_robot_node,
        controller_node,
    ])
