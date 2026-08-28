# Physical AI Study - Week 5

> Gazebo GPU LiDAR의 `LaserScan`을 ROS 2에서 읽고, 유효한 거리값을 좌표로 변환한 뒤 전방 장애물의 거리, 방향과 위험 단계를 판단하는 Perception 모듈을 구현한 기록이다.

> 이전 학습 기록: [4주차 - Digital Twin 시뮬레이션](WEEK4.md)

## 1. 학습 목표

- `sensor_msgs/msg/LaserScan`의 구조를 이해한다.
- 거리 배열의 인덱스로 각도를 계산한다.
- 유효하지 않은 거리값을 제거한다.
- 극좌표 거리값을 2차원 Cartesian 좌표로 변환한다.
- 전체 Scan에서 전방 관심 영역을 선택한다.
- 인접한 측정점을 하나의 장애물로 묶는다.
- 가장 가까운 장애물의 거리와 방향을 판정한다.
- 계산 함수와 ROS 2 Node를 분리해 단위 테스트한다.
- 결과 Topic과 RViz Marker로 인식 결과를 확인한다.

## 2. Perception 데이터 흐름

```text
Gazebo World의 장애물
  → GPU LiDAR
  → Gazebo /scan
  → ros_gz_bridge
  → ROS 2 /scan
  → lidar_obstacle_detector
       ├─ 유효값 필터링
       ├─ 각도·좌표 계산
       ├─ 전방 영역 선택
       ├─ 장애물 Clustering
       └─ 거리·방향·위험 단계 판정
  → 결과 Topic과 RViz Marker
```

## 3. LaserScan 메시지

`LaserScan`의 주요 필드는 다음과 같다.

| 필드 | 의미 |
| --- | --- |
| `angle_min` | 첫 번째 거리값의 각도 |
| `angle_max` | Scan의 마지막 범위 각도 |
| `angle_increment` | 측정값 사이의 각도 간격 |
| `range_min` | 유효한 최소 측정 거리 |
| `range_max` | 유효한 최대 측정 거리 |
| `ranges` | 각 방향에서 측정한 거리 배열 |

`ranges[i]`의 각도는 다음 식으로 계산한다.

```text
angle(i) = angle_min + i × angle_increment
```

Python 배열은 0부터 시작하므로 첫 번째 값의 인덱스는 0이다. 현재 LiDAR는 약 1° 간격으로 360개 방향을 측정하지만 계산할 때는 간격을 고정하지 않고 메시지의 `angle_increment`를 사용한다.

## 4. 유효한 거리값

현재 센서의 측정 범위는 0.12m에서 8.0m이다. 다음 조건을 모두 만족하는 값만 계산에 사용한다.

```python
math.isfinite(distance) and range_min <= distance <= range_max
```

| 값 | 처리 | 의미 |
| --- | --- | --- |
| `inf` | 제외 | 측정 범위 안에서 물체를 찾지 못함 |
| `NaN` | 제외 | 정상적으로 계산되지 않은 값 |
| 0.12m 미만 | 제외 | 최소 측정 거리보다 가까움 |
| 8.0m 초과 | 제외 | 최대 측정 거리보다 멂 |
| 0.12m~8.0m | 사용 | 유효한 거리 측정값 |

## 5. 극좌표에서 Cartesian 좌표로 변환

LiDAR 거리 `r`과 각도 `θ`로부터 로봇 기준의 점 좌표를 계산한다.

```text
x = r × cos(θ)
y = r × sin(θ)
```

ROS 로봇 좌표계에서 `+x`는 전방, `+y`는 좌측, `-y`는 우측이다. 각 측정값을 XY 점으로 변환하면 측정점 사이의 실제 거리를 계산하고 RViz에 표시할 수 있다.

## 6. 전방 관심 영역

센서는 360° 전체를 측정하지만 현재 장애물 감지 노드는 `front_half_angle_deg: 30.0`을 사용한다.

```text
-30° ≤ angle ≤ +30°
```

따라서 로봇 정면의 총 60° 영역만 전방 장애물 판정에 사용한다. 센서의 측정 범위는 유지하면서 YAML Parameter만 변경해 감지 영역을 조정할 수 있다.

## 7. 장애물 Clustering

유효한 점 하나만으로 장애물을 판정하면 센서 노이즈에 민감해진다. 현재 구현은 다음 조건을 만족하는 인접 측정점을 하나의 장애물 Cluster로 묶는다.

- 원래 Scan 배열에서도 인덱스가 연속되어야 한다.
- 두 점 사이 Cartesian 거리가 `cluster_gap` 이하여야 한다.
- 최소 `minimum_cluster_points`개의 점이 모여야 한다.

현재 설정은 다음과 같다.

```yaml
cluster_gap: 0.15
minimum_cluster_points: 3
```

유효한 점 하나가 존재하더라도 세 개 이상의 연속된 점이 모이지 않으면 거리값은 유효하지만 장애물로 최종 인정하지 않는다.

## 8. 거리와 상태 판정

가장 가까운 Cluster에서 LiDAR와 가장 가까운 점의 거리를 사용한다.

| 거리 | 상태 |
| --- | --- |
| 0.5m 이하 | `DANGER` |
| 0.5m 초과 1.0m 이하 | `WARNING` |
| 1.0m 초과 | `CLEAR` |
| 인식된 Cluster 없음 | `CLEAR`, 거리 `inf` |

`CLEAR`는 물체가 전혀 없다는 뜻이 아니라 1m 안에 위험한 물체가 없다는 뜻이다. 물체가 전혀 없는 경우는 거리값 `inf`를 함께 확인해야 한다.

## 9. 방향 판정

Cluster 중심의 평균 XY 좌표로 중심 각도를 계산한다.

```text
center_angle = atan2(center_y, center_x)
```

현재 `center_tolerance_deg`는 10°이다.

| 중심 각도 | 방향 |
| --- | --- |
| +10°보다 큼 | `LEFT` |
| -10°보다 작음 | `RIGHT` |
| -10°~+10° | `FRONT` |
| 감지된 장애물 없음 | `NONE` |

## 10. 계산 함수와 ROS 2 Node 분리

`lidar_processing.py`에는 ROS 2 통신 없이 숫자 계산만 수행하는 순수 함수를 배치했다.

- `is_valid_range`: 거리 유효성 검사
- `scan_to_points`: 배열을 각도와 XY 점으로 변환
- `points_in_sector`: 관심 각도 영역 선택
- `cluster_points`: 인접 측정점 Clustering
- `classify_distance`: 위험 단계 판정
- `direction_from_angle`: 장애물 방향 판정

`lidar_obstacle_detector.py`는 ROS 2 통신을 담당한다.

- `/scan` 구독
- YAML Parameter 읽기
- 계산 함수 호출
- TF를 이용한 점 좌표 변환
- 결과 Topic과 Marker 발행

이 구조에서는 Gazebo가 없어도 가짜 `ranges` 배열을 계산 함수에 직접 넣어 결과를 시험할 수 있다. 계산 로직은 빠른 단위 테스트로 검증하고, Gazebo와 Bridge 연결은 별도의 통합 테스트로 검증한다.

## 11. 발행 Topic

| Topic | 메시지 | 의미 |
| --- | --- | --- |
| `/obstacle_detected` | `Bool` | 경고 범위 안의 장애물 존재 여부 |
| `/obstacle_status` | `String` | `CLEAR`, `WARNING`, `DANGER` |
| `/obstacle_direction` | `String` | `LEFT`, `FRONT`, `RIGHT`, `NONE` |
| `/nearest_obstacle_distance` | `Float32` | 가장 가까운 장애물 거리 |
| `/nearest_obstacle_point` | `PointStamped` | 가장 가까운 점의 좌표 |
| `/obstacle_markers` | `MarkerArray` | RViz 장애물 시각화 |

가장 가까운 점은 가능한 경우 `lidar_link`에서 `base_link`로 TF 변환한 뒤 발행한다. Marker는 Warning을 노란색, Danger를 빨간색으로 표시한다.

## 12. 주요 Parameter

`config/perception.yaml`에서 다음 값을 변경할 수 있다.

| Parameter | 기본값 | 역할 |
| --- | ---: | --- |
| `scan_topic` | `/scan` | 입력 LaserScan Topic |
| `output_frame` | `base_link` | 최근접 점 출력 좌표계 |
| `front_half_angle_deg` | 30° | 전방 검사 영역의 절반 각도 |
| `warning_distance` | 1.0m | Warning 기준 거리 |
| `danger_distance` | 0.5m | Danger 기준 거리 |
| `cluster_gap` | 0.15m | 같은 Cluster로 묶을 점 간격 |
| `minimum_cluster_points` | 3 | Cluster의 최소 점 개수 |
| `center_tolerance_deg` | 10° | FRONT로 분류할 중심 각도 범위 |

## 13. 빌드와 실행

```bash
source /opt/ros/jazzy/setup.bash
cd /workspace/ros2_ws
colcon build --packages-select my_first_ros_py
source install/setup.bash

ros2 launch my_first_ros_py perception.launch.py \
  run_controller:=false \
  use_rviz:=true
```

결과를 확인한다.

```bash
ros2 topic echo /scan --once
ros2 topic echo /obstacle_status
ros2 topic echo /obstacle_direction
ros2 topic echo /nearest_obstacle_distance
```

계산 함수의 단위 테스트를 실행한다.

```bash
cd /workspace/ros2_ws/src/my_first_ros_py
python3 -m pytest test/test_lidar_processing.py -q
```

## 14. 완료 결과

- `/scan`의 360개 거리값을 각도와 XY 좌표로 변환했다.
- `inf`, `NaN`, 측정 범위 밖의 값을 제거했다.
- 전방 ±30° 영역에서 연속된 측정점을 장애물로 묶었다.
- 가장 가까운 장애물의 거리, 방향과 위험 단계를 Topic으로 발행했다.
- 최근접 점과 장애물 Cluster를 RViz에서 시각화했다.
- 계산 로직을 ROS 2 Node에서 분리하고 단위 테스트 13개로 검증했다.
- Gazebo 통합 실행에서 `CLEAR`, `WARNING`, `DANGER` 전환을 확인했다.
