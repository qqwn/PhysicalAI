"""Pure functions for filtering and grouping two-dimensional LiDAR scans."""

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ScanPoint:
    """One valid LiDAR sample represented in polar and Cartesian form."""

    index: int
    angle: float
    distance: float
    x: float
    y: float


@dataclass(frozen=True)
class ObstacleCluster:
    """A contiguous group of LiDAR samples belonging to one obstacle."""

    points: tuple[ScanPoint, ...]

    @property
    def nearest_point(self):
        """Return the point in the cluster closest to the sensor."""
        return min(self.points, key=lambda point: point.distance)

    @property
    def nearest_distance(self):
        """Return the shortest measured distance in the cluster."""
        return self.nearest_point.distance

    @property
    def center_x(self):
        """Return the arithmetic mean of the cluster's x coordinates."""
        return sum(point.x for point in self.points) / len(self.points)

    @property
    def center_y(self):
        """Return the arithmetic mean of the cluster's y coordinates."""
        return sum(point.y for point in self.points) / len(self.points)

    @property
    def center_angle(self):
        """Return the bearing from the sensor to the cluster center."""
        return math.atan2(self.center_y, self.center_x)

    @property
    def width(self):
        """Estimate obstacle width from the cluster endpoints."""
        first = self.points[0]
        last = self.points[-1]
        return math.hypot(last.x - first.x, last.y - first.y)


def is_valid_range(distance, range_min, range_max):
    """Return whether a distance is finite and within the sensor limits."""
    return (
        math.isfinite(distance)
        and range_min <= distance <= range_max
    )


def scan_to_points(
    ranges: Sequence[float],
    angle_min,
    angle_increment,
    range_min,
    range_max,
):
    """Convert valid LaserScan ranges into ScanPoint objects."""
    points = []

    for index, distance in enumerate(ranges):
        if not is_valid_range(distance, range_min, range_max):
            continue

        angle = angle_min + index * angle_increment
        points.append(
            ScanPoint(
                index=index,
                angle=angle,
                distance=distance,
                x=distance * math.cos(angle),
                y=distance * math.sin(angle),
            )
        )

    return points


def points_in_sector(points, minimum_angle, maximum_angle):
    """Return points whose bearing lies inside an inclusive angle sector."""
    if minimum_angle > maximum_angle:
        raise ValueError('minimum_angle must not exceed maximum_angle')

    tolerance = 1e-12
    return [
        point for point in points
        if (
            minimum_angle - tolerance
            <= point.angle
            <= maximum_angle + tolerance
        )
    ]


def nearest_distance(points):
    """Return the shortest point distance or infinity when empty."""
    if not points:
        return math.inf

    return min(point.distance for point in points)


def classify_distance(distance, warning_distance, danger_distance):
    """Classify a distance as CLEAR, WARNING, or DANGER."""
    if danger_distance <= 0.0:
        raise ValueError('danger_distance must be positive')
    if warning_distance < danger_distance:
        raise ValueError(
            'warning_distance must be greater than or equal to '
            'danger_distance'
        )

    if distance <= danger_distance:
        return 'DANGER'
    if distance <= warning_distance:
        return 'WARNING'
    return 'CLEAR'


def _point_gap(first, second):
    return math.hypot(second.x - first.x, second.y - first.y)


def cluster_points(points, cluster_gap, minimum_points):
    """Group contiguous scan points using Cartesian separation."""
    if cluster_gap <= 0.0:
        raise ValueError('cluster_gap must be positive')
    if minimum_points < 1:
        raise ValueError('minimum_points must be at least one')

    clusters = []
    current = []

    def finish_cluster():
        if len(current) >= minimum_points:
            clusters.append(ObstacleCluster(tuple(current)))

    for point in points:
        if not current:
            current.append(point)
            continue

        previous = current[-1]
        indices_are_adjacent = point.index == previous.index + 1
        points_are_close = _point_gap(previous, point) <= cluster_gap

        if indices_are_adjacent and points_are_close:
            current.append(point)
            continue

        finish_cluster()
        current = [point]

    finish_cluster()
    return clusters


def direction_from_angle(angle, center_tolerance):
    """Convert an obstacle bearing into LEFT, FRONT, or RIGHT."""
    if center_tolerance < 0.0:
        raise ValueError('center_tolerance must not be negative')
    if angle > center_tolerance:
        return 'LEFT'
    if angle < -center_tolerance:
        return 'RIGHT'
    return 'FRONT'
