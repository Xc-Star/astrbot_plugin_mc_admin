from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from ..physics.world.space import Space3D
from ..physics.world.layout_direction import LayoutDirection
from ..settings.types import CannonMode


@dataclass
class TNT:
    position: Space3D
    fuse: int


@dataclass
class GeneralData:
    pearl_position: Space3D
    pearl_motion: Space3D
    tnt_charges: List[TNT]


@dataclass
class Pearl:
    position: Space3D
    motion: Space3D
    offset: Space3D


@dataclass
class Cannon:
    pearl: Pearl
    red_tnt_override: Optional[Space3D] = None
    blue_tnt_override: Optional[Space3D] = None
    vertical_tnt: Optional[Space3D] = None
    mode: CannonMode = CannonMode.Standard
    north_west_tnt: Space3D = None
    north_east_tnt: Space3D = None
    south_west_tnt: Space3D = None
    south_east_tnt: Space3D = None
    default_red_duper: Optional[LayoutDirection] = None
    default_blue_duper: Optional[LayoutDirection] = None

    def __post_init__(self):
        if self.north_west_tnt is None:
            self.north_west_tnt = Space3D()
        if self.north_east_tnt is None:
            self.north_east_tnt = Space3D()
        if self.south_west_tnt is None:
            self.south_west_tnt = Space3D()
        if self.south_east_tnt is None:
            self.south_east_tnt = Space3D()