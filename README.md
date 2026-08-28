# Physical AI Study - Week 2

> macOS와 Docker 환경에서 ROS 2 Jazzy의 핵심 통신 구조를 익히고, Python으로 Publisher, Subscriber, Service를 실습한 기록입니다.

> 다음 학습 기록: [3주차 - 로봇 운동학과 목표점 이동 제어](WEEK3.md) · [4주차 - Digital Twin 시뮬레이션](WEEK4.md) · [5주차 - LiDAR Perception](WEEK5.md)

## 1. 이번 주 학습 목표

- macOS에서 ROS 2 개발 환경이 구성되는 원리를 이해한다.
- Docker 이미지와 컨테이너, Ubuntu, ROS 2의 관계를 구분한다.
- ROS 2의 핵심 구성 요소인 Node, Topic, Publisher, Subscriber, Service를 이해한다.
- `rclpy`를 사용해 Python ROS 2 패키지와 노드를 직접 작성한다.
- Java와 Python의 객체지향 문법을 비교하며 ROS 2 예제 코드를 해석한다.
- 소스 코드를 macOS에 보존하면서 Docker 컨테이너에서 빌드하고 실행한다.

## 2. 전체 개발 환경 구조

```text
macOS
  └─ Colima
      └─ Linux 가상 머신
          └─ Docker Engine
              └─ ros:jazzy-ros-base 컨테이너
                  ├─ Ubuntu 기반 사용자 공간
                  ├─ ROS 2 Jazzy
                  └─ /workspace ← macOS 프로젝트 폴더와 연결
```

각 구성 요소의 역할은 다음과 같다.

| 구성 요소 | 역할 |
| --- | --- |
| macOS | 실제 랩탑에서 실행되는 Host OS |
| Colima | macOS에서 Docker Engine이 동작할 Linux VM을 관리 |
| Docker | 격리된 실행 환경인 컨테이너를 생성하고 관리 |
| Ubuntu | ROS 이미지의 기반이 되는 Linux 배포판 |
| ROS 2 Jazzy | 로봇의 여러 프로그램이 통신하도록 돕는 미들웨어 및 개발 프레임워크 |
| `rclpy` | Python에서 ROS 2 기능을 사용할 수 있게 해주는 클라이언트 라이브러리 |

Ubuntu는 라이브러리가 아니라 운영체제 계열의 Linux 배포판이다. 또한 ROS 2는 이름에 OS가 들어가지만 운영체제가 아니다. Node 간 통신, 메시지 전달, 장치 제어 등에 필요한 기능을 제공하는 로봇 소프트웨어 프레임워크에 가깝다.

### Docker 이미지와 컨테이너

- **이미지(Image)**: 컨테이너를 만들기 위한 읽기 전용 실행 환경 설계도
- **컨테이너(Container)**: 이미지를 바탕으로 실제 생성되고 실행되는 격리 환경

`ros:jazzy-ros-base` 이미지는 Ubuntu 기반 환경과 ROS 2 Jazzy의 기본 패키지를 포함한다. 이미지를 내려받는 것만으로 Ubuntu VM 전체를 직접 설치하는 것은 아니지만, 해당 이미지로 만든 컨테이너 안에서는 Ubuntu 기반의 파일 시스템과 명령어를 사용할 수 있다.

### Docker와 Conda의 차이

| 구분 | Docker | Conda |
| --- | --- | --- |
| 격리 범위 | OS 사용자 공간, 시스템 패키지, 라이브러리, 실행 환경 | 주로 Python과 네이티브 라이브러리 |
| 주요 목적 | 동일한 실행 환경 재현 | Python 패키지 및 버전 관리 |
| ROS 2 실습 적합성 | Ubuntu 기준 ROS 2 환경을 재현하기 쉬움 | macOS에서 ROS 2 전체 환경을 구성하기에는 제약이 있음 |

이 프로젝트에서는 macOS와 Ubuntu의 차이를 줄이고 ROS 2 공식 패키지를 편하게 사용하기 위해 Docker 방식을 사용한다.

## 3. Colima와 Docker 실행 확인

Docker 명령이 아래와 같은 오류를 출력한다면 Docker CLI가 연결할 Docker Engine이 실행되지 않은 상태일 가능성이 높다.

```text
failed to connect to the docker API at unix:///Users/.../.colima/default/docker.sock
```

Colima를 시작한 뒤 Docker가 정상 동작하는지 확인한다.

```bash
colima start
docker run hello-world
```

각 명령의 의미는 다음과 같다.

- `colima start`: Docker Engine이 동작할 Linux VM을 시작한다.
- `docker run hello-world`: 테스트 이미지를 받아 컨테이너를 실행한다.
- 정상 메시지가 출력되면 Docker CLI, Docker Engine, 이미지 다운로드, 컨테이너 실행 과정이 모두 동작한 것이다.

상태를 추가로 확인할 때는 다음 명령을 사용할 수 있다.

```bash
colima status
docker context show
docker info
```

## 4. ROS 2 Jazzy 컨테이너 실행

프로젝트 소스가 컨테이너 삭제 여부와 관계없이 macOS에 남도록 현재 프로젝트 폴더를 `/workspace`에 연결한다.

```bash
docker pull ros:jazzy-ros-base

docker run -it --name ros2-jazzy \
  -v "$HOME/code/2026 하계 모각소/physical-ai-ros2:/workspace" \
  ros:jazzy-ros-base bash
```

### 명령어 옵션 해석

| 항목 | 의미 |
| --- | --- |
| `docker pull` | Docker Hub에서 이미지를 내려받음 |
| `docker run` | 이미지로 새 컨테이너를 생성하고 실행 |
| `-i` | 표준 입력을 열어 둠 |
| `-t` | 터미널을 할당함 |
| `--name ros2-jazzy` | 컨테이너 이름을 `ros2-jazzy`로 지정 |
| `-v HOST:CONTAINER` | macOS 폴더와 컨테이너 폴더를 연결 |
| `ros:jazzy-ros-base` | 사용할 이미지 이름과 태그 |
| `bash` | 컨테이너가 시작되면 Bash 셸을 실행 |

경로에 공백이나 한글이 포함되어 있으므로 `-v`의 경로 전체를 큰따옴표로 감싸야 한다. 줄을 나눌 때는 역슬래시(`\`) 뒤에 공백을 넣지 않는다.

컨테이너를 종료한 뒤 다시 사용할 때는 새 컨테이너를 만들지 않고 기존 컨테이너를 시작한다.

```bash
docker start -ai ros2-jazzy
```

이미 실행 중인 컨테이너에 새 터미널로 접속할 때는 다음 명령을 사용한다.

```bash
docker exec -it ros2-jazzy bash
```

`docker exec`는 새 컨테이너를 생성하지 않는다. 실행 중인 `ros2-jazzy` 컨테이너 안에서 Bash 프로세스를 하나 더 실행한다.

### `--rm`과 데이터 보존

`docker run`에 `--rm`을 붙이면 컨테이너 종료 시 컨테이너 자체와 내부 변경 사항이 삭제된다. `--rm`을 생략하면 종료된 컨테이너는 Docker 저장소에 남아 다시 시작할 수 있다.

다만 프로젝트 소스는 컨테이너 내부에만 저장하지 않고 bind mount로 연결된 `/workspace`에 작성하는 것이 안전하다.

```text
macOS 프로젝트 폴더  ↔  컨테이너의 /workspace
```

VS Code에서는 macOS의 프로젝트 폴더를 편집하고, ROS 2 빌드와 실행은 컨테이너 터미널에서 수행한다. 컨테이너 내부 데이터는 Docker와 Colima가 관리하는 Linux VM의 저장소에 보관되므로 일반 Finder 폴더처럼 직접 수정하지 않는다.

컨테이너 목록은 다음 명령으로 확인할 수 있다.

```bash
docker ps       # 현재 실행 중인 컨테이너
docker ps -a    # 종료된 컨테이너를 포함한 전체 목록
```

## 5. ROS 2 환경 활성화

컨테이너 터미널을 새로 열 때마다 ROS 2 환경 설정을 현재 셸에 적용한다.

```bash
source /opt/ros/jazzy/setup.bash
```

`source`는 별도 프로세스를 실행하는 명령이 아니라, 지정한 스크립트의 환경 변수와 설정을 현재 터미널에 적용한다. 이 과정을 거쳐야 `ros2` 명령과 ROS 2 패키지를 올바르게 찾을 수 있다.

워크스페이스를 빌드한 후에는 프로젝트 패키지도 찾을 수 있도록 다음 파일을 추가로 적용한다.

```bash
source /workspace/ros2_ws/install/setup.bash
```

정리하면 적용 순서는 다음과 같다.

```bash
source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
```

첫 번째는 기본 ROS 2 Jazzy 환경이고, 두 번째는 직접 만든 워크스페이스의 환경이다.

## 6. ROS 2 배포판 이름 이해하기

ROS 2는 버전마다 고유한 배포판 이름을 사용한다. 이 프로젝트에서 사용하는 배포판은 **Jazzy Jalisco**이며, `jazzy`는 배포판을 식별하는 이름이다.

다음 표현은 서로 다른 범주의 이름이다.

- `ROS 2 Core`: Node, Topic, Service, Action 등 ROS 2의 핵심 개념을 뜻하는 학습 범위
- `Jazzy Jalisco`: ROS 2 배포판 이름
- `ros-base`: GUI 도구를 최소화하고 핵심 ROS 기능을 포함한 Docker 이미지 유형
- `ros:jazzy-ros-base`: Jazzy 배포판의 `ros-base` 이미지를 지정하는 Docker 이미지 태그

따라서 `Core`, `Jazzy`, `ros-base`는 같은 종류의 버전명이 아니다.

## 7. 기본 Talker와 Listener 실행

Python 데모 노드가 없다면 컨테이너 안에서 설치한다.

```bash
apt update
apt install -y ros-jazzy-demo-nodes-py
```

첫 번째 터미널에서 Talker를 실행한다.

```bash
source /opt/ros/jazzy/setup.bash
ros2 run demo_nodes_py talker
```

두 번째 터미널에서 같은 컨테이너에 접속해 Listener를 실행한다.

```bash
docker exec -it ros2-jazzy bash
source /opt/ros/jazzy/setup.bash
ros2 run demo_nodes_py listener
```

통신 흐름은 다음과 같다.

```text
Talker Node
  └─ Publisher
      └─ /chatter Topic
          └─ Subscriber
              └─ Listener Node
```

- Talker는 `/chatter` Topic에 메시지를 발행한다.
- Listener는 `/chatter` Topic을 구독한다.
- 두 노드는 서로를 직접 호출하지 않고 Topic을 매개로 비동기 통신한다.
- Talker의 `Publishing...`과 Listener의 `I heard...`가 계속 출력되면 통신이 정상이다.

## 8. ROS 2 그래프 관찰

Talker와 Listener가 실행 중일 때 세 번째 터미널에서 다음 명령을 사용한다.

```bash
ros2 node list
ros2 topic list
ros2 topic echo /chatter
ros2 topic info /chatter
ros2 interface show std_msgs/msg/String
```

| 명령 | 확인할 수 있는 내용 |
| --- | --- |
| `ros2 node list` | 현재 실행 중인 Node 목록 |
| `ros2 topic list` | 현재 생성된 Topic 목록 |
| `ros2 topic echo /chatter` | `/chatter`로 전달되는 실제 메시지 |
| `ros2 topic info /chatter` | 메시지 타입과 Publisher/Subscriber 수 |
| `ros2 interface show ...` | 메시지 인터페이스의 필드 구조 |

여기서 **Node**는 ROS 2에서 특정 역할을 수행하는 실행 단위이며, **Topic**은 여러 Node가 메시지를 주고받는 이름 있는 통신 채널이다.

## 9. Python ROS 2 패키지 생성

워크스페이스의 `src` 폴더에서 패키지를 생성한다.

```bash
cd /workspace/ros2_ws/src

ros2 pkg create \
  --build-type ament_python \
  my_first_ros_py \
  --dependencies rclpy std_msgs
```

이 명령은 `my_first_ros_py`라는 Python 기반 ROS 2 패키지의 기본 구조를 생성한다.

| 항목 | 의미 |
| --- | --- |
| `ros2 pkg create` | 새 ROS 2 패키지 생성 |
| `--build-type ament_python` | Python 패키지용 빌드 방식을 사용 |
| `my_first_ros_py` | 패키지 이름 |
| `--dependencies` | 패키지가 사용하는 ROS 2 의존성 선언 |
| `rclpy` | Python ROS 2 API |
| `std_msgs` | `String` 등 기본 메시지 타입 패키지 |

생성되는 주요 구조는 다음과 같다.

```text
ros2_ws/
└─ src/
   └─ my_first_ros_py/
      ├─ package.xml
      ├─ setup.py
      ├─ setup.cfg
      ├─ resource/
      ├─ test/
      └─ my_first_ros_py/
         ├─ __init__.py
         ├─ simple_publisher.py
         └─ simple_subscriber.py
```

- 바깥쪽 `my_first_ros_py`: ROS 2 패키지 루트
- 안쪽 `my_first_ros_py`: Python 모듈 폴더
- `package.xml`: 패키지 정보와 ROS 의존성
- `setup.py`: Python 패키지 설치 정보와 실행 명령 등록
- `__init__.py`: 해당 디렉터리를 Python 패키지로 인식하게 하는 파일

## 10. 직접 만든 Publisher

```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SimplePublisher(Node):
    def __init__(self):
        super().__init__('simple_publisher')

        self.publisher_ = self.create_publisher(
            String,
            'sensor_text',
            10,
        )
        self.timer = self.create_timer(1.0, self.publish_message)
        self.count = 0

    def publish_message(self):
        msg = String()
        msg.data = f'virtual sensor data: {self.count}'

        self.publisher_.publish(msg)
        self.get_logger().info(f'Publishing: {msg.data}')
        self.count += 1


def main(args=None):
    rclpy.init(args=args)
    node = SimplePublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

### 핵심 코드 해석

- `class SimplePublisher(Node)`: `Node`를 상속해 ROS 2 Node 기능을 사용할 수 있게 한다.
- `super().__init__('simple_publisher')`: 부모 클래스인 `Node`를 초기화하고 Node 이름을 지정한다.
- `create_publisher(String, 'sensor_text', 10)`: `String` 메시지를 `/sensor_text` Topic에 발행하는 Publisher를 만든다.
- `create_timer(1.0, self.publish_message)`: 1초마다 `publish_message`를 실행하도록 Timer를 등록한다.
- `rclpy.spin(node)`: Node가 종료되지 않고 Timer와 통신 이벤트를 계속 처리하게 한다.
- `destroy_node()`와 `shutdown()`: Node와 ROS 2 Python 실행 환경의 자원을 정리한다.

숫자 `10`은 일반적으로 QoS의 history depth를 뜻한다. 수신 측이 잠시 메시지를 처리하지 못할 때 보관할 최근 메시지의 최대 개수와 관련된다.

## 11. 직접 만든 Subscriber

```python
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
```

`listener_callback`은 코드에서 직접 호출하지 않는다. `create_subscription`의 세 번째 인자로 콜백 함수를 등록하고, `/sensor_text`에 새 메시지가 도착하면 ROS 2 실행기가 자동으로 `listener_callback(msg)`를 호출한다.

```text
메시지 도착
  → ROS 2가 수신 이벤트 감지
  → spin()이 이벤트 처리
  → listener_callback(msg) 실행
  → 수신 로그 출력
```

따라서 `rclpy.spin(node)`이 실행되고 있어야 메시지 수신과 콜백 처리가 계속 이루어진다.

## 12. Python 객체를 Java 관점에서 이해하기

### `self`와 `this`

Python의 `self`는 Java의 `this`와 거의 같은 역할을 한다. 둘 다 현재 생성된 객체 자신을 가리킨다.

```python
self.count = 0
```

```java
this.count = 0;
```

차이점은 Python의 인스턴스 메서드가 첫 번째 매개변수로 `self`를 명시한다는 점이다. `self`는 예약어가 아니라 관례적인 이름이지만, 특별한 이유가 없다면 반드시 이 관례를 따른다.

### 필드 선언 방식

Java는 클래스 본문에 필드를 미리 선언한다.

```java
private int count;

public SimplePublisher() {
    this.count = 0;
}
```

Python은 보통 `__init__` 안에서 `self.count = 0`처럼 값을 처음 대입하는 순간 인스턴스 속성이 만들어진다.

```python
def __init__(self):
    self.count = 0
```

`publisher_`, `timer`, `count`는 모두 `SimplePublisher` 객체가 가진 인스턴스 속성으로 볼 수 있다.

### 상속과 부모 메서드

```python
class SimplePublisher(Node):
    def __init__(self):
        super().__init__('simple_publisher')
```

위 코드는 Java의 다음 구조와 비슷하다.

```java
class SimplePublisher extends Node {
    public SimplePublisher() {
        super("simple_publisher");
    }
}
```

`create_publisher`, `create_subscription`, `create_timer`, `get_logger`는 직접 만든 메서드가 아니라 부모 클래스인 `rclpy.node.Node`가 제공하는 메서드다. `SimplePublisher`와 `SimpleSubscriber`는 `Node`를 상속했기 때문에 `self.create_publisher(...)`처럼 호출할 수 있다.

## 13. `__name__`과 던더 메서드

앞뒤에 밑줄 두 개가 붙은 이름을 **던더(dunder, double underscore)**라고 부른다. Python이 특별한 동작을 연결해 둔 약속된 이름이며, Java의 일반적인 예약어와는 다르다.

자주 접한 던더는 다음과 같다.

| 이름 | 의미 |
| --- | --- |
| `__init__` | 객체 생성 후 인스턴스 상태를 초기화 |
| `__name__` | 현재 모듈의 이름 |
| `__main__` | Python 파일이 직접 실행될 때의 `__name__` 값 |
| `__str__` | 객체를 사용자 친화적인 문자열로 변환 |
| `__repr__` | 객체를 개발자 관점의 문자열로 표현 |
| `__len__` | `len(object)` 동작 정의 |
| `__eq__` | `==` 비교 동작 정의 |
| `__iter__` | 객체의 반복 동작 정의 |

다음 조건문은 파일을 직접 실행할 때만 `main()`을 호출한다.

```python
if __name__ == '__main__':
    main()
```

직접 실행한 경우:

```bash
python3 simple_publisher.py
```

```python
__name__ == '__main__'
```

다른 파일에서 가져온 경우:

```python
from my_first_ros_py.simple_publisher import SimplePublisher
```

```python
__name__ == 'my_first_ros_py.simple_publisher'
```

이 조건이 없으면 클래스를 import하는 순간 `main()`까지 실행되어 Node가 생성되고 `spin()`이 터미널을 점유할 수 있다. 해당 조건은 클래스와 함수는 재사용할 수 있게 하면서 프로그램 시작 코드는 직접 실행 시에만 동작하도록 분리한다.

## 14. `setup.py`에 실행 명령 등록

ROS 2가 Python 파일의 `main()`을 실행할 수 있도록 `setup.py`의 `console_scripts`에 등록한다.

```python
entry_points={
    'console_scripts': [
        'simple_publisher = my_first_ros_py.simple_publisher:main',
        'simple_subscriber = my_first_ros_py.simple_subscriber:main',
    ],
},
```

아래 한 줄을 분해하면 다음과 같다.

```text
simple_publisher = my_first_ros_py.simple_publisher:main
└─ 실행 명령 이름   └─ Python 모듈 경로             └─ 호출할 함수
```

등록 후 워크스페이스를 다시 빌드해야 변경 사항이 반영된다.

## 15. 빌드 및 실행

컨테이너 안에서 워크스페이스 루트로 이동해 빌드한다.

```bash
cd /workspace/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

첫 번째 터미널에서 Publisher를 실행한다.

```bash
ros2 run my_first_ros_py simple_publisher
```

두 번째 터미널에서 Subscriber를 실행한다.

```bash
docker exec -it ros2-jazzy bash
source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash
ros2 run my_first_ros_py simple_subscriber
```

예상 결과는 다음과 같다.

```text
Publisher: Publishing: virtual sensor data: 0
Subscriber: I received: virtual sensor data: 0
```

소스 코드를 수정하면 다시 `colcon build`를 실행하고 `install/setup.bash`를 적용한 뒤 노드를 재실행한다.

## 16. Topic과 Service 비교

| 구분 | Topic | Service |
| --- | --- | --- |
| 통신 방식 | 지속적인 단방향 데이터 스트림 | 한 번의 요청과 한 번의 응답 |
| 관계 | Publisher → Subscriber | Client → Server → Client |
| 적합한 예 | 센서 데이터, 카메라 영상, 로봇 상태 | 계산 요청, 설정 변경, 특정 작업 요청 |
| 응답 | 발행자에게 직접 응답하지 않음 | 요청마다 응답을 반환 |

센서 값처럼 계속 흐르는 정보는 Topic이 적합하고, 두 수를 더해 결과를 돌려받는 것처럼 명확한 요청과 응답이 필요한 작업은 Service가 적합하다.

## 17. AddTwoInts Service 실습

서버 터미널에서 예제 Service Server를 실행한다.

```bash
ros2 run demo_nodes_py add_two_ints_server
```

다른 터미널에서 Service를 확인하고 요청한다.

```bash
ros2 service list
ros2 service type /add_two_ints
ros2 interface show example_interfaces/srv/AddTwoInts

ros2 service call \
  /add_two_ints \
  example_interfaces/srv/AddTwoInts \
  "{a: 3, b: 5}"
```

요청과 응답 구조는 다음과 같다.

```text
Client                         Server
  ├─ Request: a=3, b=5  ───────→ │
  │                              ├─ 3 + 5 계산
  └─ Response: sum=8      ←──────┘
```

Client 터미널에는 일반적으로 다음과 같은 응답이 표시된다.

```text
sum: 8
```

Server 터미널에서는 예제 구현에 따라 `a: 3, b: 5` 요청을 받았다는 로그를 확인할 수 있다.

### Node 이름과 Service 이름 구분

`add_two_ints_server`는 실행한 **Node의 이름**이고, `/add_two_ints`는 Client가 호출하는 **Service의 이름**이다.

```text
Node: /add_two_ints_server
Service: /add_two_ints
```

`ros2 service list`에 다음과 같은 이름이 보일 수도 있다.

```text
/add_two_ints_server/get_parameters
/add_two_ints_server/list_parameters
/add_two_ints_server/set_parameters
```

이들은 `/add_two_ints`의 하위 Service가 아니다. ROS 2 Node가 Parameter를 조회하거나 변경할 수 있도록 자동으로 제공하는 별도의 Service다. `/`로 구분된 이름은 계층형 객체 관계라기보다 이름 충돌을 줄이고 역할을 구분하는 namespace에 가깝다.

## 18. 자주 발생한 문제와 해결 방법

### Docker API 연결 실패

```text
failed to connect to the docker API ... colima ... docker.sock
```

원인: Colima 또는 Docker Engine이 실행되지 않았거나 Docker context가 실행되지 않은 Colima를 가리키고 있다.

```bash
colima start
docker context show
docker run hello-world
```

### `invalid reference format`

원인: `docker run` 명령에서 줄바꿈용 역슬래시의 위치가 잘못되었거나, 공백이 포함된 volume 경로를 올바르게 묶지 않은 경우가 많다.

```bash
docker run -it --name ros2-jazzy \
  -v "$HOME/code/2026 하계 모각소/physical-ai-ros2:/workspace" \
  ros:jazzy-ros-base bash
```

### `ros2 run`에서 패키지나 실행 파일을 찾지 못함

확인 순서:

```bash
cd /workspace/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
ros2 pkg executables my_first_ros_py
```

`setup.py`의 `console_scripts` 오타 여부도 확인한다.

### Subscriber 종료 시 오류

메서드 이름은 `destory_node()`가 아니라 `destroy_node()`다.

```python
node.destroy_node()
rclpy.shutdown()
```

### Topic 메시지를 받지 못함

- Publisher와 Subscriber의 Topic 이름이 정확히 같은지 확인한다.
- 두 노드가 같은 메시지 타입을 사용하는지 확인한다.
- 두 터미널 모두 ROS 2 환경을 `source`했는지 확인한다.
- 직접 만든 패키지라면 두 터미널 모두 워크스페이스의 `install/setup.bash`를 적용했는지 확인한다.
- `ros2 topic info /sensor_text`로 Publisher와 Subscriber 수를 확인한다.
- `ros2 topic echo /sensor_text`로 실제 메시지가 발행되는지 확인한다.

## 19. 2주차 완료 체크리스트

- [ ] Ubuntu, ROS 2, Docker, Colima의 역할을 서로 구분해 설명할 수 있다.
- [ ] Docker 이미지와 컨테이너의 차이를 설명할 수 있다.
- [ ] bind mount를 사용해 macOS 소스를 컨테이너의 `/workspace`에 연결할 수 있다.
- [ ] Talker와 Listener를 서로 다른 터미널에서 실행할 수 있다.
- [ ] `ros2 node list`, `ros2 topic list`, `ros2 topic echo`로 ROS 그래프를 관찰할 수 있다.
- [ ] `ament_python` 패키지 구조와 `setup.py`의 역할을 설명할 수 있다.
- [ ] Python으로 Publisher와 Subscriber Node를 작성할 수 있다.
- [ ] Timer callback과 Subscriber callback이 언제 실행되는지 설명할 수 있다.
- [ ] Python의 `self`, 상속, `__init__`, `__name__`을 Java와 비교해 설명할 수 있다.
- [ ] Topic과 Service의 통신 목적 차이를 설명할 수 있다.
- [ ] Service Server를 실행하고 CLI에서 요청과 응답을 확인할 수 있다.

## 20. 이번 주 학습 성과

Docker 기반 Ubuntu·ROS 2 Jazzy 개발 환경을 구성하고, ROS 2의 분산 통신 모델을 실습했다. 기본 Talker/Listener 분석에서 출발해 `rclpy` 기반 Publisher와 Subscriber를 직접 구현했으며, Node·Topic·Service·Callback·QoS의 역할을 코드 수준에서 확인했다. 또한 Java와 Python의 객체 모델을 비교해 ROS 2 Python 코드의 상속, 인스턴스 속성, 실행 진입점 구조를 이해하고, bind mount를 통해 컨테이너와 로컬 개발 환경을 안정적으로 연결했다.

## 21. 다음 학습 방향

다음 단계에서는 문자열 기반 가상 센서 데이터를 실제 로봇 데이터 구조에 가까운 메시지로 확장한다.

1. 사용자 정의 Message와 Service 인터페이스 작성
2. Launch 파일을 이용한 여러 Node 동시 실행
3. Parameter를 이용한 센서 주기와 설정값 변경
4. Action의 Goal, Feedback, Result 구조 실습
5. Turtlesim 또는 시뮬레이터에서 `/cmd_vel` 기반 이동 제어
6. `ros2 bag`을 이용한 Topic 데이터 기록과 재생
