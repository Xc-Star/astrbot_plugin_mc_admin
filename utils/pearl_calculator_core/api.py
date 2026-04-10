from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import math
from .physics.world.space import Space3D
from .physics.world.direction import Direction
from .physics.world.layout_direction import LayoutDirection
from .physics.entities.movement import PearlVersion
from .calculation.inputs import Cannon, Pearl
from .calculation.calculation import calculate_tnt_amount
from .calculation.trace import calculate_pearl_trace, calculate_raw_trace
from .calculation.results import TNTResult, CalculationResult
from .settings.types import CannonMode


@dataclass
class Space3DInput:
    x: float
    y: float
    z: float


@dataclass
class CalculationInput:
    pearl_x: float
    pearl_y: float
    pearl_z: float
    pearl_motion_x: float
    pearl_motion_y: float
    pearl_motion_z: float
    offset_x: float
    offset_z: float
    cannon_y: float
    north_west_tnt: Space3DInput
    north_east_tnt: Space3DInput
    south_west_tnt: Space3DInput
    south_east_tnt: Space3DInput
    default_red_direction: str
    default_blue_direction: str
    destination_x: float
    destination_y: Optional[float]
    destination_z: float
    max_tnt: int
    max_ticks: int
    max_distance: float
    version: str
    vertical_tnt: Optional[Space3DInput]
    max_vertical_tnt: Optional[int]
    mode: Optional[str]


@dataclass
class PearlTraceInput:
    red_tnt: int
    blue_tnt: int
    vertical_tnt_amount: Optional[int]
    pearl_x: float
    pearl_y: float
    pearl_z: float
    pearl_motion_x: float
    pearl_motion_y: float
    pearl_motion_z: float
    offset_x: float
    offset_z: float
    cannon_y: float
    north_west_tnt: Space3DInput
    north_east_tnt: Space3DInput
    south_west_tnt: Space3DInput
    south_east_tnt: Space3DInput
    default_red_direction: str
    default_blue_direction: str
    destination_x: float
    destination_z: float
    direction: Optional[str]
    version: str
    vertical_tnt: Optional[Space3DInput]
    mode: Optional[str]


@dataclass
class TntGroupInput:
    x: float
    y: float
    z: float
    amount: int


@dataclass
class RawTraceInput:
    pearl_x: float
    pearl_y: float
    pearl_z: float
    pearl_motion_x: float
    pearl_motion_y: float
    pearl_motion_z: float
    tnt_groups: List[TntGroupInput]
    version: str


def parse_version(s: str) -> PearlVersion:
    mapping = {
        "Legacy": PearlVersion.Legacy,
        "Post1205": PearlVersion.Post1205,
        "Post1212": PearlVersion.Post1212,
    }
    if s not in mapping:
        raise ValueError(f"Invalid pearl version: {s}")
    return mapping[s]


def parse_layout_direction(s: str) -> Optional[LayoutDirection]:
    mapping = {
        "NorthWest": LayoutDirection.NorthWest,
        "NorthEast": LayoutDirection.NorthEast,
        "SouthWest": LayoutDirection.SouthWest,
        "SouthEast": LayoutDirection.SouthEast,
    }
    return mapping.get(s)


def direction_from_layout(layout: LayoutDirection) -> Direction:
    mapping = {
        LayoutDirection.NorthWest: Direction.North,
        LayoutDirection.NorthEast: Direction.East,
        LayoutDirection.SouthWest: Direction.West,
        LayoutDirection.SouthEast: Direction.South,
    }
    return mapping[layout]


def build_cannon(
    px: float, py: float, pz: float,
    pmx: float, pmy: float, pmz: float,
    ox: float, oz: float, cy: float,
    nw: Space3DInput, ne: Space3DInput,
    sw: Space3DInput, se: Space3DInput,
    red_dir: str, blue_dir: str,
    vert: Optional[Space3DInput],
    mode_str: Optional[str]
) -> Cannon:
    y_offset = cy - math.floor(py)

    default_red_direction = parse_layout_direction(red_dir)
    default_blue_direction = parse_layout_direction(blue_dir)

    mode = CannonMode.Accumulation if mode_str == "Accumulation" else CannonMode.Standard

    vertical_tnt = None
    if vert:
        vertical_tnt = Space3D(vert.x, vert.y + y_offset, vert.z)

    nw_pos = Space3D(nw.x, nw.y + y_offset, nw.z)
    ne_pos = Space3D(ne.x, ne.y + y_offset, ne.z)
    sw_pos = Space3D(sw.x, sw.y + y_offset, sw.z)
    se_pos = Space3D(se.x, se.y + y_offset, se.z)

    return Cannon(
        pearl=Pearl(
            position=Space3D(px, py + y_offset, pz),
            motion=Space3D(pmx, pmy, pmz),
            offset=Space3D(ox, 0.0, oz)
        ),
        vertical_tnt=vertical_tnt,
        red_tnt_override=None,
        blue_tnt_override=None,
        mode=mode,
        north_west_tnt=nw_pos,
        north_east_tnt=ne_pos,
        south_west_tnt=sw_pos,
        south_east_tnt=se_pos,
        default_red_duper=default_red_direction,
        default_blue_duper=default_blue_direction
    )


import math


def calculate_tnt_amount_api(input: CalculationInput) -> List[TNTResult]:
    version = parse_version(input.version)
    cannon = build_cannon(
        input.pearl_x, input.pearl_y, input.pearl_z,
        input.pearl_motion_x, input.pearl_motion_y, input.pearl_motion_z,
        input.offset_x, input.offset_z, input.cannon_y,
        input.north_west_tnt, input.north_east_tnt,
        input.south_west_tnt, input.south_east_tnt,
        input.default_red_direction, input.default_blue_direction,
        input.vertical_tnt, input.mode
    )
    destination = Space3D(
        input.destination_x,
        input.destination_y or 0.0,
        input.destination_z
    )

    return calculate_tnt_amount(
        cannon, destination,
        input.max_tnt, input.max_vertical_tnt,
        input.max_ticks, input.max_distance,
        version
    )


def calculate_pearl_trace_api(input: PearlTraceInput) -> Optional[CalculationResult]:
    version = parse_version(input.version)
    cannon = build_cannon(
        input.pearl_x, input.pearl_y, input.pearl_z,
        input.pearl_motion_x, input.pearl_motion_y, input.pearl_motion_z,
        input.offset_x, input.offset_z, input.cannon_y,
        input.north_west_tnt, input.north_east_tnt,
        input.south_west_tnt, input.south_east_tnt,
        input.default_red_direction, input.default_blue_direction,
        input.vertical_tnt, input.mode
    )

    default_red = parse_layout_direction(input.default_red_direction)
    if not default_red:
        raise ValueError("Invalid red direction")

    flight_direction = None
    if input.direction:
        dir_mapping = {
            "North": Direction.North,
            "South": Direction.South,
            "West": Direction.West,
            "East": Direction.East,
        }
        flight_direction = dir_mapping.get(input.direction, direction_from_layout(default_red))
    else:
        flight_direction = direction_from_layout(default_red)

    return calculate_pearl_trace(
        cannon,
        input.red_tnt, input.blue_tnt,
        input.vertical_tnt_amount or 0,
        flight_direction,
        10000,
        [],
        version
    )


def calculate_raw_trace_api(input: RawTraceInput) -> Optional[CalculationResult]:
    version = parse_version(input.version)

    pearl_pos = Space3D(input.pearl_x, input.pearl_y, input.pearl_z)
    pearl_motion = Space3D(input.pearl_motion_x, input.pearl_motion_y, input.pearl_motion_z)

    tnt_charges = [(Space3D(g.x, g.y, g.z), g.amount) for g in input.tnt_groups]

    return calculate_raw_trace(
        pearl_pos, pearl_motion, tnt_charges,
        10000, [], version
    )