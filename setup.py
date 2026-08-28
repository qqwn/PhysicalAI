"""Install the my_first_ros_py ROS 2 package."""

import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'my_first_ros_py'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py'),
        ),
        (
            os.path.join('share', package_name, 'urdf'),
            glob('urdf/*.urdf.xacro'),
        ),
        (
            os.path.join('share', package_name, 'config'),
            glob('config/*.yaml'),
        ),
        (
            os.path.join('share', package_name, 'worlds'),
            glob('worlds/*.sdf'),
        ),
        (
            os.path.join('share', package_name, 'rviz'),
            glob('rviz/*.rviz'),
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='root@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'simple_publisher = my_first_ros_py.simple_publisher:main',
            'simple_subscriber = my_first_ros_py.simple_subscriber:main',
            'virtual_robot = my_first_ros_py.virtual_robot:main',
            'go_to_goal_controller = '
            'my_first_ros_py.go_to_goal_controller:main',
            'lidar_scan_reader = my_first_ros_py.lidar_scan_reader:main',
            'lidar_obstacle_detector = '
            'my_first_ros_py.lidar_obstacle_detector:main',
        ],
    },
)
