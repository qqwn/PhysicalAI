import math

from my_first_ros_py.lidar_processing import classify_distance
from my_first_ros_py.lidar_processing import cluster_points
from my_first_ros_py.lidar_processing import direction_from_angle
from my_first_ros_py.lidar_processing import nearest_distance
from my_first_ros_py.lidar_processing import points_in_sector
from my_first_ros_py.lidar_processing import scan_to_points
import pytest


def test_scan_to_points_filters_invalid_ranges():
    ranges = [math.inf, math.nan, 0.05, 1.0, 9.0]

    points = scan_to_points(
        ranges,
        angle_min=-0.2,
        angle_increment=0.1,
        range_min=0.12,
        range_max=8.0,
    )

    assert len(points) == 1
    assert points[0].index == 3
    assert points[0].angle == pytest.approx(0.1)
    assert points[0].distance == pytest.approx(1.0)


def test_sector_and_nearest_distance():
    points = scan_to_points(
        [2.0, 1.0, 0.5, 1.5, 3.0],
        angle_min=-0.2,
        angle_increment=0.1,
        range_min=0.1,
        range_max=8.0,
    )

    front = points_in_sector(points, -0.1, 0.1)

    assert [point.index for point in front] == [1, 2, 3]
    assert nearest_distance(front) == pytest.approx(0.5)
    assert math.isinf(nearest_distance([]))


@pytest.mark.parametrize(
    ('distance', 'expected'),
    [
        (1.1, 'CLEAR'),
        (1.0, 'WARNING'),
        (0.7, 'WARNING'),
        (0.5, 'DANGER'),
        (0.2, 'DANGER'),
    ],
)
def test_classify_distance_boundaries(distance, expected):
    assert classify_distance(distance, 1.0, 0.5) == expected


def test_cluster_points_separates_range_discontinuity():
    points = scan_to_points(
        [1.0, 1.0, 1.0, 2.0, 2.0, 2.0],
        angle_min=-0.05,
        angle_increment=0.02,
        range_min=0.1,
        range_max=8.0,
    )

    clusters = cluster_points(
        points,
        cluster_gap=0.15,
        minimum_points=3,
    )

    assert len(clusters) == 2
    assert len(clusters[0].points) == 3
    assert len(clusters[1].points) == 3
    assert clusters[0].nearest_distance == pytest.approx(1.0)


def test_cluster_points_drops_small_clusters():
    points = scan_to_points(
        [1.0, math.inf, 1.0, 1.0],
        angle_min=0.0,
        angle_increment=0.01,
        range_min=0.1,
        range_max=8.0,
    )

    clusters = cluster_points(
        points,
        cluster_gap=0.15,
        minimum_points=3,
    )

    assert clusters == []


def test_cluster_cartesian_properties():
    points = scan_to_points(
        [1.0, 1.0, 1.0],
        angle_min=-0.1,
        angle_increment=0.1,
        range_min=0.1,
        range_max=8.0,
    )
    cluster = cluster_points(points, 0.2, 3)[0]

    assert cluster.center_x == pytest.approx(0.996669, abs=1e-6)
    assert cluster.center_y == pytest.approx(0.0, abs=1e-9)
    assert cluster.width == pytest.approx(0.199667, abs=1e-6)


@pytest.mark.parametrize(
    ('angle', 'expected'),
    [
        (0.3, 'LEFT'),
        (0.0, 'FRONT'),
        (-0.3, 'RIGHT'),
    ],
)
def test_direction_from_angle(angle, expected):
    assert direction_from_angle(angle, 0.1) == expected
