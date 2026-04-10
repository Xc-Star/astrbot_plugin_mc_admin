from __future__ import annotations
from dataclasses import dataclass
from typing import List
from ..physics.world.space import Space3D
from ..physics.world.direction import Direction


@dataclass
class TNTResult:
    distance: float
    tick: int
    blue: int
    red: int
    vertical: int
    yaw: float
    pitch: float
    total: int
    pearl_end_pos: Space3D
    pearl_end_motion: Space3D
    direction: Direction


@dataclass
class CalculationResult:
    landing_position: Space3D
    pearl_trace: List[Space3D]
    pearl_motion_trace: List[Space3D]
    is_successful: bool
    tick: int
    final_motion: Space3D
    distance: float