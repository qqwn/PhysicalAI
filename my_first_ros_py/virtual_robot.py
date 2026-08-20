import math

# ROS 2를 위한 기본 라이브러리
import rclpy

# ROS 2 Node의 기본 기능을 제공하는 클래스
from rclpy.node import Node

# /cmd_vel Topic에서 받을 메시지 타입
from geometry_msgs.msg import Twist

# /odom Topic으로 발행할 메시지 타입
from nav_msgs.msg import Odometry


class VirtualRobot(Node):

    def __init__(self):
        # ROS 2에서 사용할 Node 이름 설정
        super().__init__('virtual_robot')

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        self.linear_velocity = 0.0
        self.angular_velocity = 0.0

        self.dt = 0.05

        self.cmd_vel_subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10,
        )

        self.odom_publisher = self.create_publisher(
            Odometry,
            '/odom',
            10,
        )

        self.timer = self.create_timer(
            self.dt,
            self.update_pose,
        )

    def cmd_vel_callback(self, msg):
        self.linear_velocity = msg.linear.x
        self.angular_velocity = msg.angular.z

    def update_pose(self):
        current_theta = self.theta

        self.x += (
            self.linear_velocity
            * math.cos(current_theta)
            * self.dt
        )

        self.y += (
            self.linear_velocity
            * math.sin(current_theta)
            * self.dt
        )

        self.theta += (
            self.angular_velocity
            * self.dt
        )

        self.theta = math.atan2(
            math.sin(self.theta),
            math.cos(self.theta),
        )

        odom_msg = Odometry()

        odom_msg.header.stamp = (
            self.get_clock().now().to_msg()
        )

        # odom은 출발점을 기준으로 고정된 좌표계
        odom_msg.header.frame_id = 'odom'

        # base_link는 로봇 몸체에 붙어 이동하는 좌표계
        odom_msg.child_frame_id = 'base_link'

        odom_msg.pose.pose.position.x = self.x
        odom_msg.pose.pose.position.y = self.y
        odom_msg.pose.pose.position.z = 0.0

        # 이번 예제에서는 Roll과 Pitch 없이 Yaw만 사용
        odom_msg.pose.pose.orientation.x = 0.0
        odom_msg.pose.pose.orientation.y = 0.0
        odom_msg.pose.pose.orientation.z = math.sin(
            self.theta / 2.0
        )
        odom_msg.pose.pose.orientation.w = math.cos(
            self.theta / 2.0
        )

        odom_msg.twist.twist.linear.x = (
            self.linear_velocity
        )

        odom_msg.twist.twist.angular.z = (
            self.angular_velocity
        )

        self.odom_publisher.publish(odom_msg)


def main(args=None):
    rclpy.init(args=args)

    node = VirtualRobot()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass

        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
