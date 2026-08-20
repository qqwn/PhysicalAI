# Physical AI Study - Week 3

> ROS 2 `Twist` 명령으로 이동하고 `Odometry`를 발행하는 2차원 가상 로봇을 구현한 뒤, 현재 위치를 피드백받아 목표 좌표까지 이동시키는 제어기를 작성한 기록입니다.

## 1. 학습 목표

- 차동구동 로봇의 선속도와 각속도를 이해한다.
- `geometry_msgs/msg/Twist`로 로봇의 이동 명령을 표현한다.
- 2차원 운동학 식을 이용해 로봇의 위치와 방향을 갱신한다.
- `nav_msgs/msg/Odometry`로 위치, 자세, 속도를 발행한다.
- Euler 각의 Yaw와 Quaternion의 관계를 이해한다.
- 목표점까지의 거리와 방향 오차를 계산한다.
- 비례 제어와 속도 제한을 이용해 로봇을 목표점으로 이동시킨다.
- ROS 2 Parameter로 목표 좌표와 제어기 설정을 분리한다.
- Launch 파일로 가상 로봇과 제어기를 동시에 실행한다.

## 2. 시스템 구조

3주차에 구현한 시스템은 두 개의 ROS 2 Node가 Topic을 통해 연결된 폐루프 제어 구조다.

```text
                           /cmd_vel
GoToGoalController  ---------------------->  VirtualRobot
        ^                                      |
        |                                      |
        +--------------------------------------+
                           /odom
```

| Node | 구독 | 발행 | 역할 |
| --- | --- | --- | --- |
| `virtual_robot` | `/cmd_vel` | `/odom` | 속도 명령을 받아 위치를 계산 |
| `go_to_goal_controller` | `/odom` | `/cmd_vel` | 목표점 오차를 속도 명령으로 변환 |

제어기가 명령을 보내면 가상 로봇이 이동하고, 변한 위치가 다시 제어기로 돌아오므로 현재 상태를 반영해 명령을 계속 보정할 수 있다.

## 3. `Twist`를 이용한 이동 명령

2차원 이동 로봇에서 사용하는 값은 다음과 같다.

```text
msg.linear.x   = v      # 로봇 전방의 선속도(m/s)
msg.angular.z  = ω      # Z축 기준 각속도(rad/s)
```

- `v > 0`: 전진
- `v < 0`: 후진
- `ω > 0`: 반시계 방향 회전
- `ω < 0`: 시계 방향 회전
- `v = 0`, `ω ≠ 0`: 제자리 회전

실제 차동구동 로봇에서는 왼쪽과 오른쪽 바퀴의 각속도로부터 `v`와 `ω`가 결정된다. 이번 가상 로봇은 바퀴 단계를 추상화하고 `Twist`의 `v`, `ω`를 바로 입력받는다.

## 4. 2차원 로봇 운동학

로봇의 상태는 `x`, `y`, `theta`로 표현한다.

```text
x     += v × cos(theta) × dt
y     += v × sin(theta) × dt
theta += ω × dt
```

`virtual_robot` Node는 0.05초마다 이 식을 실행한다. `theta`는 각도가 계속 커지는 것을 방지하기 위해 다음 식으로 `-π`에서 `π` 범위로 정규화한다.

```python
theta = math.atan2(math.sin(theta), math.cos(theta))
```

## 5. Odometry 메시지

`nav_msgs/msg/Odometry`는 로봇의 위치와 속도를 표현한다.

| 필드 | 의미 |
| --- | --- |
| `header.stamp` | 메시지를 생성한 ROS 2 시간 |
| `header.frame_id` | 위치를 측정하는 기준 좌표계 `odom` |
| `child_frame_id` | 이동하는 로봇 본체 좌표계 `base_link` |
| `pose.pose.position` | 로봇의 `x`, `y`, `z` 위치 |
| `pose.pose.orientation` | Quaternion으로 표현한 자세 |
| `twist.twist` | 현재 선속도와 각속도 |

이 예제는 Roll과 Pitch가 없는 2차원 이동만 다루므로 Yaw `theta`를 다음 Quaternion으로 변환한다.

```text
orientation.z = sin(theta / 2)
orientation.w = cos(theta / 2)
```

제어기는 다음 식으로 Quaternion에서 Yaw를 다시 얻는다.

```text
theta = 2 × atan2(orientation.z, orientation.w)
```

## 6. 목표점 제어

현재 위치 `(x, y)`와 목표 위치 `(goal_x, goal_y)`로부터 위치 오차를 계산한다.

```text
dx = goal_x - x
dy = goal_y - y

distance     = hypot(dx, dy)
target_theta = atan2(dy, dx)
angle_error  = normalize(target_theta - theta)
```

제어 로직은 다음 순서로 동작한다.

1. 목표점까지의 거리와 방향 오차를 계산한다.
2. 방향 오차가 `heading_tolerance`보다 크면 제자리에서 먼저 회전한다.
3. 방향이 목표점을 향하면 거리에 비례하는 속도로 전진한다.
4. 선속도와 각속도를 각각 설정한 최대값 이하로 제한한다.
5. 목표점까지의 거리가 `goal_tolerance`보다 작으면 정지 명령을 발행한다.

```text
angular_velocity = angular_gain × angle_error
linear_velocity  = linear_gain × distance
```

현재 구현은 거리와 방향 오차에 비례하는 명령을 만드는 **P 제어**이다. 적분항과 미분항을 포함한 완전한 PID 제어기는 아니다.

## 7. ROS 2 Parameter

제어기의 목표점과 제어 설정은 Parameter로 분리했다.

| Parameter | 기본값 | 역할 |
| --- | ---: | --- |
| `goal_x` | `2.0` | 목표 X 좌표 |
| `goal_y` | `1.0` | 목표 Y 좌표 |
| `linear_gain` | `0.8` | 거리 오차에 대한 선속도 비례 이득 |
| `angular_gain` | `1.5` | 방향 오차에 대한 각속도 비례 이득 |
| `max_linear_velocity` | `0.6` | 최대 선속도 |
| `max_angular_velocity` | `1.5` | 최대 각속도 |
| `goal_tolerance` | `0.1` | 도착으로 인정할 거리 |
| `heading_tolerance` | `0.2` | 전진을 허용할 방향 오차 |

Launch 파일은 기본 목표점을 `(3.0, 2.0)`으로 재설정한다.

## 8. Launch를 이용한 다중 Node 실행

`robot_control.launch.py`는 `virtual_robot`과 `go_to_goal_controller`를 함께 실행한다.

Launch 파일을 Python 패키지와 함께 설치하기 위해 `setup.py`의 `data_files`에 `launch/*.launch.py`를 등록했다. `package.xml`에는 다음 실행 의존성을 추가했다.

```xml
<exec_depend>launch</exec_depend>
<exec_depend>launch_ros</exec_depend>
<exec_depend>ros2launch</exec_depend>
```

## 9. 패키지 파일 구조

```text
my_first_ros_py/
├── launch/
│   └── robot_control.launch.py
├── my_first_ros_py/
│   ├── virtual_robot.py
│   └── go_to_goal_controller.py
├── package.xml
└── setup.py
```

| 파일 | 역할 |
| --- | --- |
| `virtual_robot.py` | `Twist`를 구독하고 `Odometry`를 발행하는 가상 로봇 |
| `go_to_goal_controller.py` | Odometry 피드백으로 목표점 이동 명령 생성 |
| `robot_control.launch.py` | 두 Node 실행과 목표 좌표 설정 |
| `setup.py` | 실행 명령과 Launch 파일 설치 |
| `package.xml` | ROS 2 메시지와 Launch 의존성 선언 |

## 10. 빌드와 실행

컨테이너 안에서 ROS 2 환경을 활성화하고 워크스페이스를 빌드한다.

```bash
source /opt/ros/jazzy/setup.bash
cd /workspace/ros2_ws

colcon build --packages-select my_first_ros_py
source install/setup.bash
```

두 Node를 한 번에 실행한다.

```bash
ros2 launch my_first_ros_py robot_control.launch.py
```

각 Node를 따로 실행하려면 두 개의 터미널을 사용한다.

```bash
# 터미널 1
ros2 run my_first_ros_py virtual_robot
```

```bash
# 터미널 2
ros2 run my_first_ros_py go_to_goal_controller --ros-args \
  -p goal_x:=3.0 \
  -p goal_y:=2.0
```

## 11. 동작 관찰

실행 중에 다른 터미널에서 다음 명령을 사용한다.

```bash
source /opt/ros/jazzy/setup.bash
source /workspace/ros2_ws/install/setup.bash

ros2 node list
ros2 topic list
ros2 topic info /cmd_vel -v
ros2 topic info /odom -v
ros2 topic echo /cmd_vel
ros2 topic echo /odom
```

Parameter는 다음 명령으로 확인한다.

```bash
ros2 param list /go_to_goal_controller
ros2 param get /go_to_goal_controller goal_x
ros2 param get /go_to_goal_controller goal_y
```

정상적으로 실행되면 다음과 같은 흐름을 확인할 수 있다.

1. 제어기가 목표점이 `(3.0, 2.0)`임을 출력한다.
2. 로봇이 목표점 방향으로 회전한다.
3. 방향 오차가 줄어들면 전진한다.
4. 목표점에 가까워질수록 선속도가 줄어든다.
5. 목표점에서 `Goal reached`를 출력하고 정지한다.

## 12. 자주 발생하는 문제

### 실행 파일을 찾지 못함

`setup.py`의 `console_scripts`에 실행 명령을 등록했는지 확인하고 다시 빌드한다.

```bash
colcon build --packages-select my_first_ros_py
source install/setup.bash
ros2 pkg executables my_first_ros_py
```

### Launch 파일을 찾지 못함

`setup.py` `data_files`에 Launch 파일이 포함되었는지 확인하고 다시 빌드한다.

```bash
ros2 pkg prefix my_first_ros_py
find install/my_first_ros_py -name 'robot_control.launch.py'
```

### 메시지 타입을 찾지 못함

`package.xml`에 `geometry_msgs`와 `nav_msgs` 의존성이 있는지 확인한다.

### 로봇이 목표점에서 진동함

- `linear_gain`과 `angular_gain`을 낮춘다.
- `goal_tolerance`를 조금 키운다.
- 방향 오차가 큰 상태에서 선속도가 0인지 확인한다.
- 선속도와 각속도에 최대값이 적용되는지 확인한다.

## 13. 3주차 완료 체크리스트

- [ ] `Twist.linear.x`와 `Twist.angular.z`의 의미를 설명할 수 있다.
- [ ] `x`, `y`, `theta`를 시간에 따라 갱신하는 식을 설명할 수 있다.
- [ ] `Odometry` 메시지의 Pose와 Twist를 구분할 수 있다.
- [ ] `odom`과 `base_link` 좌표계의 역할을 설명할 수 있다.
- [ ] Yaw를 Quaternion으로 변환하고 다시 복원하는 식을 설명할 수 있다.
- [ ] 목표점까지의 거리와 방향 오차를 계산할 수 있다.
- [ ] P 제어와 속도 제한의 역할을 설명할 수 있다.
- [ ] ROS 2 Parameter로 목표 좌표와 제어 설정을 변경할 수 있다.
- [ ] Launch 파일로 두 Node를 함께 실행할 수 있다.
- [ ] `/cmd_vel`과 `/odom`을 관찰해 로봇의 이동 과정을 확인할 수 있다.

## 14. 학습 성과

`Twist` 속도 명령을 받아 2차원 위치와 방향을 갱신하고, 결과를 `Odometry`로 발행하는 가상 로봇을 구현했다. 또한 Odometry에서 현재 상태를 읽어 목표점까지의 거리와 방향 오차를 계산하고, 비례 제어와 속도 제한을 적용한 `Twist` 명령을 생성했다. 두 Node는 ROS 2 Topic으로 폐루프를 구성하며, Launch와 Parameter를 이용해 하나의 제어 시스템으로 실행할 수 있다.
