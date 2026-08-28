"""ROS 2 node that detects and visualizes frontal LiDAR obstacles."""

import math

from geometry_msgs.msg import PointStamped

from my_first_ros_py.lidar_processing import classify_distance
from my_first_ros_py.lidar_processing import cluster_points
from my_first_ros_py.lidar_processing import direction_from_angle
from my_first_ros_py.lidar_processing import points_in_sector
from my_first_ros_py.lidar_processing import scan_to_points

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time

from sensor_msgs.msg import LaserScan

from std_msgs.msg import Bool, Float32, String

from tf2_geometry_msgs import do_transform_point

from tf2_ros import Buffer, TransformException, TransformListener

from visualization_msgs.msg import Marker, MarkerArray


class LidarObstacleDetector(Node):
    """Detect frontal obstacle clusters from sensor_msgs/LaserScan."""

    def __init__(self):
        """Initialize parameters, ROS interfaces, and the TF listener."""
        super().__init__('lidar_obstacle_detector')

        self._declare_parameters()
        self._read_parameters()

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.last_status = None
        self.transform_warning_reported = False

        self.scan_subscription = self.create_subscription(
            LaserScan,
            self.scan_topic,
            self.scan_callback,
            qos_profile_sensor_data,
        )
        self.detected_publisher = self.create_publisher(
            Bool,
            '/obstacle_detected',
            10,
        )
        self.status_publisher = self.create_publisher(
            String,
            '/obstacle_status',
            10,
        )
        self.direction_publisher = self.create_publisher(
            String,
            '/obstacle_direction',
            10,
        )
        self.distance_publisher = self.create_publisher(
            Float32,
            '/nearest_obstacle_distance',
            10,
        )
        self.point_publisher = self.create_publisher(
            PointStamped,
            '/nearest_obstacle_point',
            10,
        )
        self.marker_publisher = self.create_publisher(
            MarkerArray,
            '/obstacle_markers',
            10,
        )

        self.get_logger().info(
            'LiDAR obstacle detector: scan=%s front=±%.1fdeg '
            'warning=%.2fm danger=%.2fm output_frame=%s'
            % (
                self.scan_topic,
                self.front_half_angle_deg,
                self.warning_distance,
                self.danger_distance,
                self.output_frame,
            )
        )

    def _declare_parameters(self):
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('output_frame', 'base_link')
        self.declare_parameter('front_half_angle_deg', 30.0)
        self.declare_parameter('warning_distance', 1.0)
        self.declare_parameter('danger_distance', 0.5)
        self.declare_parameter('cluster_gap', 0.15)
        self.declare_parameter('minimum_cluster_points', 3)
        self.declare_parameter('center_tolerance_deg', 10.0)
        self.declare_parameter('publish_markers', True)

    def _read_parameters(self):
        self.scan_topic = self.get_parameter('scan_topic').value
        self.output_frame = self.get_parameter('output_frame').value
        self.front_half_angle_deg = self.get_parameter(
            'front_half_angle_deg'
        ).value
        self.warning_distance = self.get_parameter(
            'warning_distance'
        ).value
        self.danger_distance = self.get_parameter(
            'danger_distance'
        ).value
        self.cluster_gap = self.get_parameter('cluster_gap').value
        self.minimum_cluster_points = self.get_parameter(
            'minimum_cluster_points'
        ).value
        self.center_tolerance = math.radians(
            self.get_parameter('center_tolerance_deg').value
        )
        self.publish_markers = self.get_parameter(
            'publish_markers'
        ).value

        if self.front_half_angle_deg <= 0.0:
            raise ValueError('front_half_angle_deg must be positive')
        classify_distance(
            math.inf,
            self.warning_distance,
            self.danger_distance,
        )

    def scan_callback(self, message):
        """Process one LaserScan and publish the perception result."""
        points = scan_to_points(
            message.ranges,
            message.angle_min,
            message.angle_increment,
            message.range_min,
            message.range_max,
        )
        half_angle = math.radians(self.front_half_angle_deg)
        front_points = points_in_sector(points, -half_angle, half_angle)
        clusters = cluster_points(
            front_points,
            self.cluster_gap,
            self.minimum_cluster_points,
        )

        nearest_cluster = None
        if clusters:
            nearest_cluster = min(
                clusters,
                key=lambda cluster: cluster.nearest_distance,
            )

        distance = (
            nearest_cluster.nearest_distance
            if nearest_cluster is not None
            else math.inf
        )
        status = classify_distance(
            distance,
            self.warning_distance,
            self.danger_distance,
        )
        detected = status != 'CLEAR'
        direction = 'NONE'

        if detected:
            direction = direction_from_angle(
                nearest_cluster.center_angle,
                self.center_tolerance,
            )

        self._publish_summary(detected, status, direction, distance)

        if nearest_cluster is not None:
            self._publish_nearest_point(message, nearest_cluster)

        if self.publish_markers:
            self._publish_markers(message, clusters)

        if status != self.last_status:
            self.get_logger().info(
                'Obstacle status=%s direction=%s distance=%.3fm'
                % (status, direction, distance)
            )
            self.last_status = status

    def _publish_summary(self, detected, status, direction, distance):
        detected_message = Bool()
        detected_message.data = detected
        self.detected_publisher.publish(detected_message)

        status_message = String()
        status_message.data = status
        self.status_publisher.publish(status_message)

        direction_message = String()
        direction_message.data = direction
        self.direction_publisher.publish(direction_message)

        distance_message = Float32()
        distance_message.data = float(distance)
        self.distance_publisher.publish(distance_message)

    def _publish_nearest_point(self, scan_message, cluster):
        nearest = cluster.nearest_point
        point = PointStamped()
        point.header = scan_message.header
        point.point.x = nearest.x
        point.point.y = nearest.y
        point.point.z = 0.0

        if not self.output_frame or self.output_frame == point.header.frame_id:
            self.point_publisher.publish(point)
            return

        try:
            transform = self.tf_buffer.lookup_transform(
                self.output_frame,
                point.header.frame_id,
                Time(),
                timeout=Duration(seconds=0.05),
            )
            transformed = do_transform_point(point, transform)
            transformed.header.stamp = scan_message.header.stamp
            self.point_publisher.publish(transformed)
            self.transform_warning_reported = False
        except TransformException as error:
            if not self.transform_warning_reported:
                self.get_logger().warning(
                    'Cannot transform nearest obstacle from %s to %s: %s'
                    % (point.header.frame_id, self.output_frame, error)
                )
                self.transform_warning_reported = True
            self.point_publisher.publish(point)

    def _publish_markers(self, scan_message, clusters):
        marker_array = MarkerArray()
        delete_all = Marker()
        delete_all.action = Marker.DELETEALL
        marker_array.markers.append(delete_all)

        visible_clusters = [
            cluster for cluster in clusters
            if cluster.nearest_distance <= self.warning_distance
        ]

        for marker_id, cluster in enumerate(visible_clusters):
            status = classify_distance(
                cluster.nearest_distance,
                self.warning_distance,
                self.danger_distance,
            )
            marker = Marker()
            marker.header = scan_message.header
            marker.ns = 'lidar_obstacles'
            marker.id = marker_id
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            marker.pose.position.x = cluster.center_x
            marker.pose.position.y = cluster.center_y
            marker.pose.position.z = 0.10
            marker.pose.orientation.w = 1.0
            marker.scale.x = max(0.12, min(cluster.width, 0.60))
            marker.scale.y = marker.scale.x
            marker.scale.z = 0.20
            marker.color.a = 0.85
            marker.lifetime.nanosec = 300_000_000

            if status == 'DANGER':
                marker.color.r = 1.0
                marker.color.g = 0.10
            else:
                marker.color.r = 1.0
                marker.color.g = 0.75

            marker_array.markers.append(marker)

        self.marker_publisher.publish(marker_array)


def main(args=None):
    """Run the LiDAR obstacle detector node."""
    rclpy.init(args=args)
    node = LidarObstacleDetector()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
