import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SimpleSubscriber(Node):

    def __init__(self):
        super().__init__('simple_subscriber')
        self.subscription = self.create_subscription(
            String,
            'sensor_text',
            self.listener_callback,
            10,
        )

    def listener_callback(self, msg):
        self.get_logger().info(f'I received: {msg.data}')


def main(args=None):
    rclpy.init(args=args)
    node = SimpleSubscriber()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
