from __future__ import annotations

from dataclasses import dataclass

from ..physics.world.direction import Direction
from ..physics.world.space import Space3D


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
    pearl_trace: list[Space3D]
    pearl_motion_trace: list[Space3D]
    is_successful: bool
    tick: int
    final_motion: Space3D
    distance: float
