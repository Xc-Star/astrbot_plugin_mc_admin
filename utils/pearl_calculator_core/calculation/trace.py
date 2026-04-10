import math
from typing import List, Optional, Tuple
from ..physics.world.space import Space3D
from ..physics.world.direction import Direction
from ..physics.aabb.aabb_box import AABBBox
from ..physics.constants.constants import FLOAT_PRECISION_EPSILON
from ..physics.entities.movement import PearlVersion
from .inputs import Cannon, GeneralData
from .results import TNTResult, CalculationResult
from .simulation import find_best_hit_for_ticks, run
from .vectors import resolve_vectors_for_direction


def validate_candidates(
    candidates: List[Tuple[Tuple[int, int, int], List[int]]],
    red_vec: Space3D,
    blue_vec: Space3D,
    vert_vec: Space3D,
    pearl_position: Space3D,
    pearl_motion: Space3D,
    pearl_offset: Space3D,
    destination: Space3D,
    max_distance_sq: float,
    version: PearlVersion,
    calculation_direction: Direction
) -> List[TNTResult]:
    start_abs_x = pearl_position.x + pearl_offset.x
    start_abs_y = pearl_position.y + pearl_offset.y
    start_abs_z = pearl_position.z + pearl_offset.z
    check_3d = vert_vec.length_sq() > FLOAT_PRECISION_EPSILON

    raw_results: List[TNTResult] = []

    red_x = red_vec.x
    red_y = red_vec.y
    red_z = red_vec.z
    blue_x = blue_vec.x
    blue_y = blue_vec.y
    blue_z = blue_vec.z
    vert_x = vert_vec.x
    vert_y = vert_vec.y
    vert_z = vert_vec.z
    pearl_motion_x = pearl_motion.x
    pearl_motion_y = pearl_motion.y
    pearl_motion_z = pearl_motion.z

    for (r_u32, b_u32, v_u32), ticks in candidates:
        if not ticks:
            continue

        total = r_u32 + b_u32 + v_u32

        data = GeneralData(
            pearl_position=pearl_position,
            pearl_motion=Space3D(
                pearl_motion_x + (red_x * r_u32) + (blue_x * b_u32) + (vert_x * v_u32),
                pearl_motion_y + (red_y * r_u32) + (blue_y * b_u32) + (vert_y * v_u32),
                pearl_motion_z + (red_z * r_u32) + (blue_z * b_u32) + (vert_z * v_u32)
            ),
            tnt_charges=[]
        )

        best_hit = find_best_hit_for_ticks(
            data, destination, ticks, pearl_offset, version, max_distance_sq, check_3d
        )

        if best_hit:
            flight_x = best_hit.position.x - start_abs_x
            flight_y = best_hit.position.y - start_abs_y
            flight_z = best_hit.position.z - start_abs_z
            h_dist = math.sqrt((flight_x * flight_x) + (flight_z * flight_z))
            yaw = math.atan2(-flight_x, flight_z) * 180.0 / math.pi
            pitch = math.atan2(-flight_y, h_dist) * 180.0 / math.pi

            raw_results.append(TNTResult(
                distance=best_hit.distance,
                tick=best_hit.tick,
                blue=b_u32,
                red=r_u32,
                vertical=v_u32,
                total=total,
                pearl_end_pos=best_hit.position,
                pearl_end_motion=best_hit.motion,
                direction=calculation_direction,
                yaw=yaw,
                pitch=pitch
            ))

    return sorted(raw_results, key=lambda x: (x.tick, x.distance))


def calculate_pearl_trace(
    cannon: Cannon,
    red_tnt: int,
    blue_tnt: int,
    vertical_tnt: int,
    direction: Direction,
    max_ticks: int,
    world_collisions: List[AABBBox],
    version: PearlVersion
) -> Optional[CalculationResult]:
    red_vec, blue_vec, vert_vec = resolve_vectors_for_direction(cannon, direction)
    
    total_tnt_motion = (red_vec * red_tnt) + (blue_vec * blue_tnt) + (vert_vec * vertical_tnt)
    final_motion = cannon.pearl.motion + total_tnt_motion

    return run_trace_internal(
        cannon.pearl.position,
        final_motion,
        cannon.pearl.offset,
        max_ticks,
        world_collisions,
        version
    )


def calculate_raw_trace(
    pearl_position: Space3D,
    pearl_motion: Space3D,
    tnt_charges: List[Tuple[Space3D, int]],
    max_ticks: int,
    world_collisions: List[AABBBox],
    version: PearlVersion
) -> Optional[CalculationResult]:
    from .simulation import calculate_tnt_motion

    total_explosion_motion = Space3D()
    for tnt_pos, count in tnt_charges:
        if count > 0:
            total_explosion_motion += calculate_tnt_motion(pearl_position, tnt_pos) * count

    return run_trace_internal(
        pearl_position,
        pearl_motion + total_explosion_motion,
        None,
        max_ticks,
        world_collisions,
        version
    )


def run_trace_internal(
    position: Space3D,
    motion: Space3D,
    offset: Optional[Space3D],
    max_ticks: int,
    world_collisions: List[AABBBox],
    version: PearlVersion
) -> Optional[CalculationResult]:
    data = GeneralData(
        pearl_position=position,
        pearl_motion=motion,
        tnt_charges=[]
    )

    return run(data, None, max_ticks, world_collisions, offset, version)
