from __future__ import annotations
from dataclasses import dataclass


@dataclass
class AABBBox:
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    @classmethod
    def create(cls, min_x: float, min_y: float, min_z: float, max_x: float, max_y: float, max_z: float) -> AABBBox:
        return cls(min_x, min_y, min_z, max_x, max_y, max_z)

    @classmethod
    def default(cls) -> AABBBox:
        return cls(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    def offset(self, x: float, y: float, z: float) -> AABBBox:
        return AABBBox(
            self.min_x + x,
            self.min_y + y,
            self.min_z + z,
            self.max_x + x,
            self.max_y + y,
            self.max_z + z
        )

    def y_offset(self, other: AABBBox, offset_y: float) -> float:
        if other.max_x <= self.min_x or other.min_x >= self.max_x:
            return offset_y
        if other.max_z <= self.min_z or other.min_z >= self.max_z:
            return offset_y
        if offset_y > 0.0 and other.max_y <= self.min_y:
            d = self.min_y - other.max_y
            if d < offset_y:
                offset_y = d
        if offset_y < 0.0 and other.min_y >= self.max_y:
            d = self.max_y - other.min_y
            if d > offset_y:
                offset_y = d
        return offset_y

    def x_offset(self, other: AABBBox, offset_x: float) -> float:
        if other.max_y <= self.min_y or other.min_y >= self.max_y:
            return offset_x
        if other.max_z <= self.min_z or other.min_z >= self.max_z:
            return offset_x
        if offset_x > 0.0 and other.max_x <= self.min_x:
            d = self.min_x - other.max_x
            if d < offset_x:
                offset_x = d
        if offset_x < 0.0 and other.min_x >= self.max_x:
            d = self.max_x - other.min_x
            if d > offset_x:
                offset_x = d
        return offset_x

    def z_offset(self, other: AABBBox, offset_z: float) -> float:
        if other.max_x <= self.min_x or other.min_x >= self.max_x:
            return offset_z
        if other.max_y <= self.min_y or other.min_y >= self.max_y:
            return offset_z
        if offset_z > 0.0 and other.max_z <= self.min_z:
            d = self.min_z - other.max_z
            if d < offset_z:
                offset_z = d
        if offset_z < 0.0 and other.min_z >= self.max_z:
            d = self.max_z - other.min_z
            if d > offset_z:
                offset_z = d
        return offset_z