from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.actions import TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch.substitutions import PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package_share = FindPackageShare('my_first_ros_py')

    world_name = LaunchConfiguration('world_name')
    robot_name = LaunchConfiguration('robot_name')
    robot_x = LaunchConfiguration('robot_x')
    robot_y = LaunchConfiguration('robot_y')
    robot_z = LaunchConfiguration('robot_z')
    goal_x = LaunchConfiguration('goal_x')
    goal_y = LaunchConfiguration('goal_y')
    run_controller = LaunchConfiguration('run_controller')
    use_rviz = LaunchConfiguration('use_rviz')
    verbosity = LaunchConfiguration('verbosity')

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
    rviz_config = PathJoinSubstitution([
        package_share,
        'rviz',
        'digital_twin.rviz',
    ])
    gazebo_world_launch = PathJoinSubstitution([
        package_share,
        'launch',
        'gazebo_world.launch.py',
    ])

    robot_description_content = Command([
        FindExecutable(name='xacro'),
        ' ',
        xacro_file,
    ])
    robot_description = ParameterValue(
        robot_description_content,
        value_type=str,
    )

    gazebo_world = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gazebo_world_launch),
        launch_arguments={'verbosity': verbosity}.items(),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }],
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        parameters=[{'config_file': bridge_config}],
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_physical_ai_robot',
        output='screen',
        arguments=[
            '-world', world_name,
            '-name', robot_name,
            '-string', robot_description_content,
            '-x', robot_x,
            '-y', robot_y,
            '-z', robot_z,
        ],
    )

    controller = Node(
        package='my_first_ros_py',
        executable='go_to_goal_controller',
        name='go_to_goal_controller',
        output='screen',
        condition=IfCondition(run_controller),
        parameters=[{
            'use_sim_time': True,
            'goal_x': ParameterValue(goal_x, value_type=float),
            'goal_y': ParameterValue(goal_y, value_type=float),
        }],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        condition=IfCondition(use_rviz),
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'world_name',
            default_value='physical_ai_world',
        ),
        DeclareLaunchArgument(
            'robot_name',
            default_value='physical_ai_robot',
        ),
        DeclareLaunchArgument('robot_x', default_value='0.0'),
        DeclareLaunchArgument('robot_y', default_value='0.0'),
        DeclareLaunchArgument('robot_z', default_value='0.2'),
        DeclareLaunchArgument('goal_x', default_value='2.0'),
        DeclareLaunchArgument('goal_y', default_value='0.0'),
        DeclareLaunchArgument('run_controller', default_value='true'),
        DeclareLaunchArgument('use_rviz', default_value='false'),
        DeclareLaunchArgument('verbosity', default_value='3'),
        gazebo_world,
        robot_state_publisher,
        bridge,
        TimerAction(period=3.0, actions=[spawn_robot]),
        TimerAction(period=5.0, actions=[controller]),
        rviz,
    ])
