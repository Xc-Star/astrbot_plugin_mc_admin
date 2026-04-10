import math
from typing import Dict, List, Tuple, Optional
from ..physics.world.space import Space3D
from ..physics.world.direction import Direction
from ..physics.constants.constants import (
    FLOAT_PRECISION_EPSILON, PEARL_DRAG_MULTIPLIER, PEARL_GRAVITY_ACCELERATION
)
from ..physics.entities.movement import PearlVersion
from .inputs import Cannon
from .results import TNTResult


def solve_theoretical_tnt(
    red_vec: Space3D,
    blue_vec: Space3D,
    vert_vec: Space3D,
    start_pos: Space3D,
    start_motion: Space3D,
    destination: Space3D,
    max_ticks: int,
    version: PearlVersion
) -> Dict[Tuple[int, int, int], List[int]]:
    true_distance = destination - start_pos

    groups: Dict[Tuple[int, int, int], List[int]] = {}
    drag_multiplier = PEARL_DRAG_MULTIPLIER
    denominator_constant = 1.0 - drag_multiplier

    denominator = red_vec.z * blue_vec.x - blue_vec.z * red_vec.x
    is_3d_solve = vert_vec.length_sq() > FLOAT_PRECISION_EPSILON

    if not is_3d_solve and abs(denominator) < FLOAT_PRECISION_EPSILON:
        return {}

    gravity = -PEARL_GRAVITY_ACCELERATION
    sim_grav_vel = 0.0
    sim_grav_pos = 0.0

    sim_motion_vel = start_motion.copy()
    sim_motion_pos = Space3D()

    for tick in range(1, max_ticks + 1):
        sim_grav_vel = version.apply_grav_drag_tick(sim_grav_vel, gravity, drag_multiplier)
        sim_grav_pos += sim_grav_vel

        new_vx, dx = version.apply_motion_tick(sim_motion_vel.x, drag_multiplier)
        new_vy, dy = version.apply_motion_tick(sim_motion_vel.y, drag_multiplier)
        new_vz, dz = version.apply_motion_tick(sim_motion_vel.z, drag_multiplier)
        sim_motion_vel = Space3D(new_vx, new_vy, new_vz)
        sim_motion_pos += Space3D(dx, dy, dz)

        compensated_distance = true_distance.copy()
        compensated_distance.y -= sim_grav_pos + sim_motion_pos.y
        compensated_distance.x -= sim_motion_pos.x
        compensated_distance.z -= sim_motion_pos.z

        numerator = 1.0 - math.pow(drag_multiplier, tick)
        divider = version.get_projection_multiplier(drag_multiplier) * numerator / denominator_constant

        if is_3d_solve:
            target_motion = compensated_distance / divider
            result = solve_tnt_system_3d(red_vec, blue_vec, vert_vec, target_motion)
            if result:
                r, b, v = result
                cr = round(r)
                cb = round(b)
                cv = round(v)
                if cr >= 0 and cb >= 0 and cv >= 0:
                    key = (cr, cb, cv)
                    if key not in groups:
                        groups[key] = []
                    groups[key].append(tick)
        else:
            true_red = (compensated_distance.z * blue_vec.x - compensated_distance.x * blue_vec.z) / denominator
            true_blue = (compensated_distance.x - true_red * red_vec.x) / blue_vec.x

            ideal_red = round(true_red / divider)
            ideal_blue = round(true_blue / divider)

            if ideal_red >= 0 and ideal_blue >= 0:
                key = (ideal_red, ideal_blue, 0)
                if key not in groups:
                    groups[key] = []
                groups[key].append(tick)

    return groups


def solve_tnt_system_3d(
    red: Space3D,
    blue: Space3D,
    vert: Space3D,
    target: Space3D
) -> Optional[Tuple[float, float, float]]:
    det = red.dot(blue.cross(vert))

    if abs(det) < FLOAT_PRECISION_EPSILON:
        return None

    dr = target.dot(blue.cross(vert))
    db = red.dot(target.cross(vert))
    dv = red.dot(blue.cross(target))

    return (dr / det, db / det, dv / det)