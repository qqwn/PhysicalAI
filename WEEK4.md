# Physical AI Study - Week 4

> Gazebo Sim에 차동구동 로봇과 센서를 배치하고 ROS 2와 연결하여, 현실의 로봇을 소프트웨어에서 재현하는 Digital Twin 환경을 구성한 기록이다.

> 이전 학습 기록: [3주차 - 로봇 운동학과 목표점 이동 제어](WEEK3.md)

## 1. 학습 목표

- Gazebo Sim과 Gazebo World의 역할을 이해한다.
- URDF와 Xacro로 로봇의 링크와 조인트를 표현한다.
- 차동구동 플러그인으로 실제 물리 기반 이동을 구현한다.
- `ros_gz_bridge`로 Gazebo Transport와 ROS 2 Topic을 연결한다.
- LiDAR, IMU, Joint State 센서를 로봇 모델에 추가한다.
- TF 트리와 `robot_state_publisher`의 역할을 이해한다.
- Launch 파일 하나로 World, 로봇, Bridge, 제어기, RViz를 통합 실행한다.

## 2. Digital Twin 전체 구조

```text
Gazebo World
  ├─ 바닥·벽·장애물·조명·중력
  └─ Physical AI Robot
       ├─ Differential Drive
       ├─ GPU LiDAR
       ├─ IMU
       └─ Joint State Publisher
             ↕ Gazebo Transport
        ros_gz_bridge
             ↕ ROS 2 Topic
  Controller · Perception · RViz
```

가상 머신은 Gazebo가 실행되는 Linux 컴퓨터 환경이다. Gazebo World는 가상 머신이 아니라 로봇이 활동하는 가상 물리 실험장이다.

## 3. Gazebo World

`worlds/physical_ai_world.sdf`에는 다음 환경이 정의되어 있다.

- 8m × 8m 크기의 이동 영역과 네 방향 벽
- 중력과 물리 엔진
- 태양광과 배경 색상
- 두 개의 직육면체 장애물
- 한 개의 원기둥 장애물
- GPU LiDAR와 IMU 계산에 필요한 Sensor System

World의 물체에는 시각적 형상인 `visual`과 물리 충돌에 사용하는 `collision`이 함께 정의된다. 로봇과 장애물의 충돌 판정은 `collision`을 기준으로 이루어진다.

## 4. URDF와 Xacro 로봇 모델

`urdf/physical_ai_robot.urdf.xacro`는 로봇을 다음 요소로 구성한다.

| 요소 | 역할 |
| --- | --- |
| `base_footprint` | 지면에 투영된 로봇 기준 좌표계 |
| `base_link` | 로봇 본체 좌표계와 몸체 형상 |
| `left_wheel_link` | 왼쪽 바퀴 |
| `right_wheel_link` | 오른쪽 바퀴 |
| `caster_link` | 로봇 균형을 유지하는 보조 바퀴 |
| `lidar_link` | 2D LiDAR의 위치와 방향 |
| `imu_link` | IMU의 위치와 방향 |

`link`는 로봇의 물리적인 부품을 나타내고 `joint`는 Link 사이의 연결 관계와 움직임을 나타낸다. 바퀴 Joint는 연속 회전하는 `continuous` 형식이고, 센서 Joint는 본체에 고정되는 `fixed` 형식이다.

Xacro Property와 Macro를 사용해 로봇 크기, 질량, 관성 계산과 좌우 바퀴의 반복 구조를 재사용할 수 있도록 구성했다.

## 5. 차동구동과 Odometry

Gazebo의 Differential Drive 플러그인이 `/cmd_vel`을 받아 실제 바퀴 Joint에 속도를 적용한다.

```text
ROS 2 /cmd_vel
  → Bridge
  → Gazebo Differential Drive
  → 왼쪽·오른쪽 바퀴 회전
  → 물리 엔진에서 로봇 이동
  → Gazebo /odom, /tf
  → Bridge
  → ROS 2 /odom, /tf
```

3주차의 `virtual_robot`은 운동학 식으로 위치를 직접 갱신했지만, 4주차에서는 Gazebo가 질량, 마찰, 충돌과 바퀴 회전을 반영해 위치를 계산한다.

## 6. ROS-Gazebo Bridge

ROS 2와 Gazebo는 서로 다른 통신 체계와 메시지 형식을 사용한다. `config/gazebo_bridge.yaml`은 두 시스템 사이에서 다음 Topic을 변환한다.

| ROS 2 Topic | 방향 | 역할 |
| --- | --- | --- |
| `/clock` | Gazebo → ROS 2 | 시뮬레이션 시간 |
| `/cmd_vel` | ROS 2 → Gazebo | 로봇 속도 명령 |
| `/odom` | Gazebo → ROS 2 | 로봇 위치와 속도 |
| `/tf` | Gazebo → ROS 2 | 이동 좌표계 관계 |
| `/scan` | Gazebo → ROS 2 | LiDAR 거리 배열 |
| `/imu` | Gazebo → ROS 2 | 가속도와 각속도 |
| `/joint_states` | Gazebo → ROS 2 | 바퀴 Joint 상태 |

Bridge가 없으면 Gazebo Topic과 ROS 2 Topic의 이름이 같더라도 서로 다른 미들웨어와 메시지 형식을 사용하므로 ROS 2 Node가 Gazebo 데이터를 직접 받을 수 없다.

## 7. LiDAR와 IMU

GPU LiDAR는 수평 `-π`에서 `+π`까지 총 360°를 360개 Sample로 측정한다. 최소 측정 거리는 0.12m, 최대 측정 거리는 8m이며 10Hz로 `/scan`을 생성한다.

`gpu_lidar`는 World가 GPU를 가진다는 뜻이 아니다. Gazebo가 실행되는 컴퓨터의 그래픽 렌더링 기능을 이용해 World 안의 물체와 가상 광선의 교차점을 병렬 계산하는 센서 형식이다.

IMU는 50Hz로 다음 데이터를 `/imu`에 제공한다.

- 선형 가속도
- 각속도
- 자세 Orientation

## 8. Joint State와 TF

`/joint_states`는 왼쪽과 오른쪽 바퀴 Joint의 이름, 위치, 속도를 전달한다. `robot_state_publisher`는 URDF의 Joint 구조와 `/joint_states`를 결합하여 바퀴를 포함한 로봇 전체 TF를 발행한다.

```text
odom
└─ base_footprint
   └─ base_link
      ├─ left_wheel_link
      ├─ right_wheel_link
      ├─ caster_link
      ├─ lidar_link
      └─ imu_link
```

`/tf`는 시간에 따라 변하는 좌표 관계이고 `/tf_static`은 고정된 센서 장착 관계를 전달한다. 이 연결 덕분에 RViz가 로봇의 바퀴 회전과 센서 위치를 올바르게 표시할 수 있다.

## 9. 통합 Launch

`launch/digital_twin.launch.py`는 다음 작업을 한 번에 수행한다.

1. Gazebo World를 실행한다.
2. Xacro를 URDF 문자열로 변환한다.
3. `robot_state_publisher`를 실행한다.
4. `ros_gz_bridge`를 실행한다.
5. World 준비 후 로봇을 Spawn한다.
6. 선택적으로 목표점 제어기를 실행한다.
7. 선택적으로 RViz를 실행한다.

주요 Launch Argument는 다음과 같다.

| Argument | 기본값 | 역할 |
| --- | --- | --- |
| `robot_x`, `robot_y`, `robot_z` | `0, 0, 0.2` | 로봇 생성 위치 |
| `goal_x`, `goal_y` | `2, 0` | 목표점 제어기의 목표 위치 |
| `run_controller` | `true` | 목표점 제어기 실행 여부 |
| `use_rviz` | `false` | RViz 실행 여부 |
| `verbosity` | `3` | Gazebo 로그 수준 |

## 10. 빌드와 실행

```bash
source /opt/ros/jazzy/setup.bash
cd /workspace/ros2_ws
colcon build --packages-select my_first_ros_py
source install/setup.bash

ros2 launch my_first_ros_py digital_twin.launch.py \
  run_controller:=false \
  use_rviz:=true
```

직접 이동 명령을 발행할 때는 다음 명령을 사용한다.

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.3}, angular: {z: 0.0}}"
```

센서와 좌표계를 확인한다.

```bash
ros2 topic echo /scan --once
ros2 topic echo /imu --once
ros2 topic echo /joint_states --once
ros2 run tf2_ros tf2_echo odom lidar_link
```

## 11. 완료 결과

- Gazebo World에 차동구동 로봇을 Spawn했다.
- `/cmd_vel`로 실제 바퀴 Joint가 회전하고 로봇이 이동함을 확인했다.
- `/odom`, `/tf`, `/scan`, `/imu`, `/joint_states`가 ROS 2로 전달됨을 확인했다.
- 바퀴 회전 시 `/joint_states` 위치값이 변화함을 확인했다.
- RViz에서 Robot Model, TF, LaserScan, Odometry를 표시했다.
- 하나의 Launch 파일로 전체 Digital Twin을 재현할 수 있도록 구성했다.
