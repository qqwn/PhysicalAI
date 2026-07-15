#ROS 2를 Python에서 사용하기 위한 핵심 라이브러리인 rcply를 가져옴
import rclpy

#ROS 2의 기본 실행 단위인 Node클래스를 가져온다
from rclpy.node import Node

#ROS 2 기본 메시지 타입 중 String 메시지를 가져오며 문자열 데이터를 Topic으로 보낼 때 사용
from std_msgs.msg import String

#Node를 상속받기 때문에 이 클래스는 ROS 2 노드로 동작할 수 있다. 
class SimplePublisher(Node):
	#객체 생성시 자동 실행되는 초기화 함수, SimplePublisher를 만들면 이 함수가 기본 실행
	def __init__(self):
		#부모 클래스인 Node의 초기화 함수를 실행 문자열의 내용은 ROS 2 노드의 이름
		#또한, 이 노드는 ros2 시스템 안에서 /simple_publisher 로 인식
		super().__init__('simple_publisher')
		
		#String 으로 메시지를 보내며, Topic의 이름은 sensor_text, 10은 QoS 큐 size
		self.publisher_ = self.create_publisher(String, 'sensor_text',10)
		
		#timer를 생성. 1.0초 마다 publish_message 실행
		self.timer = self.create_timer(1.0, self.publish_message)
		
		#메시지 번호를 세기 위한 변수
		self.count = 0
	
	#타이머에 의해 1초마다 실행되는 함수
	def publish_message(self):
		#String 타입의 객체 생성
		msg = String() 
		msg.data = f'virtual sensor data: {self.count}'
		
		#/sensor_text Topic에 msg를 보냄.
		self.publisher_.publish(msg)
		
		#터미널에 로그를 출력
		self.get_logger().info(f'Publishing: {msg.data}')
		self.count +=1
		
def main(args=None):
	#ros 2 python 클라이언트를 초기화
	#ros 2 노드를 만들기 전에 반드시 실행, 파이썬에서 ros2 기능을 사용할 준비를 하라는 의미
	rclpy.init(args=args)
	
	node = SimplePublisher()

	#노드를 계속 실행 상태로 유지, 없으면 프로그램 바로 종료.
	rclpy.spin(node)

	#터미널에서 ctrl + c 로 종료하게 되면 이후 자원 정리를 위한 코드
	node.destroy_node()
	
	#ros 2 python 클라이언트 종료
	rclpy.shutdown()
	
#해당 파이썬 파일이 직접 실행 될 경우 __name__ = '__main__'이 되고 main() 함수 실행	
if __name__ == '__main__':
	main()
