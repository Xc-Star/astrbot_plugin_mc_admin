from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from ..world.space import Space3D
from ..aabb.aabb_box import AABBBox


@dataclass
class EntityData:
    position: Space3D
    motion: Space3D
    bounding_box: AABBBox
    on_ground: bool = False
    is_collided_horizontally: bool = False
    is_collided_vertically: bool = False
    is_gravity: bool = False

    def move_entity(self, xa: float, ya: float, za: float, world_collisions: List[AABBBox]) -> None:
        original_xa = xa
        original_ya = ya
        original_za = za

        bb = self.bounding_box
        for aabb in world_collisions:
            ya = aabb.y_offset(bb, ya)
        bb = bb.offset(0.0, ya, 0.0)

        for aabb in world_collisions:
            xa = aabb.x_offset(bb, xa)
        bb = bb.offset(xa, 0.0, 0.0)

        for aabb in world_collisions:
            za = aabb.z_offset(bb, za)

        self.bounding_box = bb.offset(0.0, 0.0, za)

        self.position.x = (self.bounding_box.min_x + self.bounding_box.max_x) / 2.0
        self.position.y = self.bounding_box.min_y
        self.position.z = (self.bounding_box.min_z + self.bounding_box.max_z) / 2.0

        self.is_collided_horizontally = original_xa != xa or original_za != za
        self.is_collided_vertically = original_ya != ya
        self.on_ground = original_ya != ya and original_ya < 0.0

        if original_xa != xa:
            self.motion.x = 0.0
        if original_ya != ya:
            self.motion.y = 0.0
        if original_za != za:
            self.motion.z = 0.0