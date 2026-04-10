from __future__ import annotations
from enum import Enum, auto
from typing import List


class Direction(Enum):
    North = 1
    South = 2
    East = 4
    West = 8

    def invert(self) -> Direction:
        mapping = {
            Direction.North: Direction.South,
            Direction.South: Direction.North,
            Direction.West: Direction.East,
            Direction.East: Direction.West,
        }
        return mapping[self]

    @staticmethod
    def from_angle(angle: float) -> Direction:
        if -135.0 <= angle < -45.0:
            return Direction.East
        elif -45.0 <= angle < 45.0:
            return Direction.South
        elif 45.0 <= angle < 135.0:
            return Direction.West
        else:
            return Direction.North

    @staticmethod
    def from_angle_with_fallbacks(angle: float) -> List[Direction]:
        BOUNDARY_EPSILON = 10.0

        def is_near(boundary: float) -> bool:
            return abs(angle - boundary) < BOUNDARY_EPSILON

        if is_near(-45.0):
            return [Direction.South, Direction.East]
        elif is_near(45.0):
            return [Direction.West, Direction.South]
        elif is_near(135.0):
            return [Direction.North, Direction.West]
        elif is_near(-135.0):
            return [Direction.East, Direction.North]
        else:
            return [Direction.from_angle(angle)]