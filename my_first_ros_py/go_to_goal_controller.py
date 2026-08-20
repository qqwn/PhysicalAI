import math

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


class GoToGoalController(Node):

    def __init__(self):
        super().__init__('go_to_goal_controller')

        # 사용할 ROS 2 Parameter와 기본값 선언
        self.declare_parameter('goal_x', 2.0)
        self.declare_parameter('goal_y', 1.0)

        self.declare_parameter('linear_gain', 0.8)
        self.declare_parameter('angular_gain', 1.5)

        self.declare_parameter('max_linear_velocity', 0.6)
        self.declare_parameter('max_angular_velocity', 1.5)

        self.declare_parameter('goal_tolerance', 0.1)
        self.declare_parameter('heading_tolerance', 0.2)

        self.goal_x = self.get_parameter('goal_x').value
        self.goal_y = self.get_parameter('goal_y').value

        self.linear_gain = self.get_parameter('linear_gain').value
        self.angular_gain = self.get_parameter('angular_gain').value

        self.max_linear_velocity = self.get_parameter(
            'max_linear_velocity'
        ).value

        self.max_angular_velocity = self.get_parameter(
            'max_angular_velocity'
        ).value

        self.goal_tolerance = self.get_parameter(
            'goal_tolerance'
        ).value

        self.heading_tolerance = self.get_parameter(
            'heading_tolerance'
        ).value

        self.goal_reached = False

        # 계산한 속도 명령을 /cmd_vel 토픽으로 발행
        self.cmd_vel_publisher = self.create_publisher(
            Twist,
            '/cmd_vel',
            10,
        )

        # /odom 메시지가 도착할 때마다 odom_callback 실행
        self.odom_subscription = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10,
        )

        self.get_logger().info(
            f'Goal: ({self.goal_x}, {self.goal_y})'
        )

    def normalize_angle(self, angle):
        # 각도를 -pi부터 pi 범위로 정규화
        return math.atan2(
            math.sin(angle),
            math.cos(angle),
        )

    def odom_callback(self, msg):
        # 현재 위치 읽기
        current_x = msg.pose.pose.position.x
        current_y = msg.pose.pose.position.y

        orientation = msg.pose.pose.orientation

        # Roll과 Pitch가 없는 현재 예제의 쿼터니언을 Yaw로 변환
        current_theta = 2.0 * math.atan2(
            orientation.z,
            orientation.w,
        )

        # 현재 위치에서 목표점까지의 차이
        dx = self.goal_x - current_x
        dy = self.goal_y - current_y

        # 목표점까지의 거리와 목표점이 있는 방향 계산
        distance = math.hypot(dx, dy)
        target_theta = math.atan2(dy, dx)

        # 목표 방향과 현재 방향의 차이를 계산하고 정규화
        angle_error = self.normalize_angle(
            target_theta - current_theta
        )

        # 목표점까지의 거리가 10cm 이내라면 정지
        if distance <= self.goal_tolerance:
            self.stop_robot()

            if not self.goal_reached:
                self.get_logger().info('Goal reached')
                self.goal_reached = True

            return

        self.goal_reached = False

        # 방향 오차가 클수록 빠르게 회전
        angular_velocity = (
            self.angular_gain * angle_error
        )

        # 각속도를 최대 각속도 범위로 제한
        angular_velocity = max(
            -self.max_angular_velocity,
            min(
                angular_velocity,
                self.max_angular_velocity,
            ),
        )

        # 방향 오차가 크면 제자리 회전부터 수행
        if abs(angle_error) > self.heading_tolerance:
            linear_velocity = 0.0
        else:
            # 목표점이 가까울수록 선속도를 줄임
            linear_velocity = (
                self.linear_gain * distance
            )

            # 선속도를 최대 선속도 이하로 제한
            linear_velocity = min(
                linear_velocity,
                self.max_linear_velocity,
            )

        cmd_vel_msg = Twist()
        cmd_vel_msg.linear.x = linear_velocity
        cmd_vel_msg.angular.z = angular_velocity

        self.cmd_vel_publisher.publish(cmd_vel_msg)

    def stop_robot(self):
        # 모든 속도의 기본값이 0인 Twist 메시지를 발행
        stop_msg = Twist()
        self.cmd_vel_publisher.publish(stop_msg)


def main(args=None):
    rclpy.init(args=args)

    node = GoToGoalController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Launch가 SIGINT를 처리해 ROS Context를 먼저 닫을 수 있다.
        if rclpy.ok():
            node.stop_robot()

        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass

        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
