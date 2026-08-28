"""Learning node that prints representative values from LaserScan."""

import math

from my_first_ros_py.lidar_processing import nearest_distance
from my_first_ros_py.lidar_processing import points_in_sector
from my_first_ros_py.lidar_processing import scan_to_points

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import LaserScan


class LidarScanReader(Node):
    """Read and summarize front, left, right, and global scan ranges."""

    def __init__(self):
        """Initialize the LaserScan subscription and log controls."""
        super().__init__('lidar_scan_reader')

        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('log_every_n_scans', 10)

        scan_topic = self.get_parameter('scan_topic').value
        self.log_every_n_scans = max(
            1,
            self.get_parameter('log_every_n_scans').value,
        )
        self.scan_count = 0

        self.subscription = self.create_subscription(
            LaserScan,
            scan_topic,
            self.scan_callback,
            qos_profile_sensor_data,
        )

        self.get_logger().info(f'Reading LaserScan from {scan_topic}')

    def scan_callback(self, message):
        """Log directional minimum ranges at a controlled rate."""
        self.scan_count += 1
        if self.scan_count % self.log_every_n_scans != 0:
            return

        points = scan_to_points(
            message.ranges,
            message.angle_min,
            message.angle_increment,
            message.range_min,
            message.range_max,
        )

        front = points_in_sector(
            points,
            math.radians(-30.0),
            math.radians(30.0),
        )
        left = points_in_sector(
            points,
            math.radians(30.0),
            math.radians(120.0),
        )
        right = points_in_sector(
            points,
            math.radians(-120.0),
            math.radians(-30.0),
        )

        self.get_logger().info(
            'samples=%d valid=%d front=%.3fm left=%.3fm '
            'right=%.3fm minimum=%.3fm'
            % (
                len(message.ranges),
                len(points),
                nearest_distance(front),
                nearest_distance(left),
                nearest_distance(right),
                nearest_distance(points),
            )
        )


def main(args=None):
    """Run the LiDAR scan reader node."""
    rclpy.init(args=args)
    node = LidarScanReader()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
