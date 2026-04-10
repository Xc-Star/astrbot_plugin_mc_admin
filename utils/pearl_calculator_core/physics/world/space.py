from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

@dataclass
class Space3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Space3D) -> Space3D:
        return Space3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Space3D) -> Space3D:
        return Space3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Space3D:
        return Space3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def __truediv__(self, scalar: float) -> Space3D:
        return Space3D(self.x / scalar, self.y / scalar, self.z / scalar)

    def __iadd__(self, other: Space3D) -> Space3D:
        self.x += other.x
        self.y += other.y
        self.z += other.z
        return self

    def __imul__(self, scalar: float) -> Space3D:
        self.x *= scalar
        self.y *= scalar
        self.z *= scalar
        return self

    def __itruediv__(self, scalar: float) -> Space3D:
        self.x /= scalar
        self.y /= scalar
        self.z /= scalar
        return self

    def distance(self, other: Space3D) -> float:
        return math.sqrt(self.distance_sq(other))

    def distance_sq(self, other: Space3D) -> float:
        return (self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2

    def length(self) -> float:
        return math.sqrt(self.length_sq())

    def length_sq(self) -> float:
        return self.x ** 2 + self.y ** 2 + self.z ** 2

    def distance_2d(self, other: Space3D) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.z - other.z) ** 2)

    def distance_2d_sq(self, other: Space3D) -> float:
        return (self.x - other.x) ** 2 + (self.z - other.z) ** 2

    def angle_to_yaw(self, other: Space3D) -> float:
        delta_x = other.x - self.x
        delta_z = other.z - self.z
        return to_degrees(math.atan2(-delta_x, delta_z))

    def dot(self, other: Space3D) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Space3D) -> Space3D:
        return Space3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def copy(self) -> Space3D:
        return Space3D(self.x, self.y, self.z)


def to_radians(degrees: float) -> float:
    return degrees * math.pi / 180.0

def to_degrees(radians: float) -> float:
    return radians * 180.0 / math.pi