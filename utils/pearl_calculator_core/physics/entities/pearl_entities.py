from __future__ import annotations
from dataclasses import dataclass
from ..world.space import Space3D
from ..aabb.aabb_box import AABBBox
from ..constants.constants import PEARL_HEIGHT, PEARL_RADIUS
from .entities import EntityData


@dataclass
class PearlEntity:
    data: EntityData

    @classmethod
    def create(cls, position: Space3D, motion: Space3D) -> PearlEntity:
        pos_copy = position.copy()
        motion_copy = motion.copy()
        bounding_box = AABBBox(
            pos_copy.x - PEARL_RADIUS,
            pos_copy.y,
            pos_copy.z - PEARL_RADIUS,
            pos_copy.x + PEARL_RADIUS,
            pos_copy.y + PEARL_HEIGHT,
            pos_copy.z + PEARL_RADIUS
        )
        data = EntityData(
            position=pos_copy,
            motion=motion_copy,
            bounding_box=bounding_box,
            is_gravity=True
        )
        return cls(data=data)