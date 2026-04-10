from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
from ..physics.world.space import Space3D
from ..physics.world.layout_direction import LayoutDirection


class CannonMode(Enum):
    Standard = "Standard"
    Accumulation = "Accumulation"


@dataclass
class Surface2D:
    x: float
    z: float


@dataclass
class PearlInfo:
    motion: Space3D
    position: Space3D


@dataclass
class CannonSettings:
    max_tnt: int = 0
    red_tnt: Optional[Space3D] = None
    blue_tnt: Optional[Space3D] = None
    vertical_tnt: Optional[Space3D] = None
    mode: CannonMode = CannonMode.Standard
    default_red_direction: Optional[LayoutDirection] = None
    default_blue_direction: Optional[LayoutDirection] = None
    north_west_tnt: Space3D = None
    north_east_tnt: Space3D = None
    south_west_tnt: Space3D = None
    south_east_tnt: Space3D = None
    offset: Surface2D = None
    pearl: PearlInfo = None

    def __post_init__(self):
        if self.north_west_tnt is None:
            self.north_west_tnt = Space3D()
        if self.north_east_tnt is None:
            self.north_east_tnt = Space3D()
        if self.south_west_tnt is None:
            self.south_west_tnt = Space3D()
        if self.south_east_tnt is None:
            self.south_east_tnt = Space3D()
        if self.offset is None:
            self.offset = Surface2D(0.0, 0.0)
        if self.pearl is None:
            self.pearl = PearlInfo(Space3D(), Space3D())


@dataclass
class AppSettings:
    cannon_settings: List[CannonSettings]