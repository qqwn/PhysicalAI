from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution

from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    verbosity = LaunchConfiguration('verbosity')

    world_file = PathJoinSubstitution([
        FindPackageShare('my_first_ros_py'),
        'worlds',
        'physical_ai_world.sdf',
    ])
    gazebo_launch_file = PathJoinSubstitution([
        FindPackageShare('ros_gz_sim'),
        'launch',
        'gz_sim.launch.py',
    ])

    gazebo_server = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gazebo_launch_file),
        launch_arguments={
            'gz_args': [
                '-r -s -v ',
                verbosity,
                ' ',
                world_file,
            ],
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'verbosity',
            default_value='3',
            description='Gazebo console verbosity from 0 to 4.',
        ),
        gazebo_server,
    ])
