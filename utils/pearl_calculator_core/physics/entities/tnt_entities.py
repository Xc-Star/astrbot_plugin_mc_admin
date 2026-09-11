from __future__ import annotations

from dataclasses import dataclass

from ..aabb.aabb_box import AABBBox
from ..constants.constants import TNT_HEIGHT, TNT_RADIUS
from ..world.space import Space3D
from .entities import EntityData


@dataclass
class TNTEntity:
    data: EntityData
    fuse: int

    @classmethod
    def create(cls, position: Space3D, fuse: int) -> TNTEntity:
        bounding_box = AABBBox(
            position.x - TNT_RADIUS,
            position.y,
            position.z - TNT_RADIUS,
            position.x + TNT_RADIUS,
            position.y + TNT_HEIGHT,
            position.z + TNT_RADIUS
        )
        data = EntityData(position=position, motion=Space3D(), bounding_box=bounding_box)
        return cls(data=data, fuse=fuse)
