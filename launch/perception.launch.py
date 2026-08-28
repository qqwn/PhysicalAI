"""Launch the Digital Twin and frontal LiDAR perception node."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    """Create the integrated Gazebo and LiDAR perception launch graph."""
    package_share = FindPackageShare('my_first_ros_py')

    run_controller = LaunchConfiguration('run_controller')
    use_rviz = LaunchConfiguration('use_rviz')
    goal_x = LaunchConfiguration('goal_x')
    goal_y = LaunchConfiguration('goal_y')

    digital_twin_launch = PathJoinSubstitution([
        package_share,
        'launch',
        'digital_twin.launch.py',
    ])
    perception_config = PathJoinSubstitution([
        package_share,
        'config',
        'perception.yaml',
    ])

    digital_twin = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(digital_twin_launch),
        launch_arguments={
            'run_controller': run_controller,
            'use_rviz': use_rviz,
            'goal_x': goal_x,
            'goal_y': goal_y,
        }.items(),
    )

    obstacle_detector = Node(
        package='my_first_ros_py',
        executable='lidar_obstacle_detector',
        name='lidar_obstacle_detector',
        output='screen',
        parameters=[perception_config],
    )

    return LaunchDescription([
        DeclareLaunchArgument('run_controller', default_value='false'),
        DeclareLaunchArgument('use_rviz', default_value='false'),
        DeclareLaunchArgument('goal_x', default_value='2.0'),
        DeclareLaunchArgument('goal_y', default_value='0.0'),
        digital_twin,
        obstacle_detector,
    ])
