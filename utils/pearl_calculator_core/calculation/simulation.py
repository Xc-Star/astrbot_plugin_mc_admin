from __future__ import annotations
import math
from typing import List, Optional, Tuple
from dataclasses import dataclass
from ..physics.world.space import Space3D
from ..physics.aabb.aabb_box import AABBBox
from ..physics.constants.constants import (
    FLOAT_PRECISION_EPSILON, PEARL_EXPLOSION_Y_FACTOR, PEARL_HEIGHT,
    TNT_ENTITY_Y_OFFSET, TNT_EXPLOSION_RADIUS, PEARL_DRAG_MULTIPLIER,
    PEARL_GRAVITY_ACCELERATION
)
from ..physics.entities.movement import PearlVersion, MovementLegacy, MovementPost1205, MovementPost1212
from ..physics.entities.pearl_entities import PearlEntity
from ..physics.entities.tnt_entities import TNTEntity
from .inputs import GeneralData
from .results import CalculationResult


@dataclass
class SimResult:
    tick: int
    position: Space3D
    motion: Space3D
    distance: float


_MOVEMENT_MAP = {
    PearlVersion.Legacy: MovementLegacy,
    PearlVersion.Post1205: MovementPost1205,
    PearlVersion.Post1212: MovementPost1212,
}

_NO_COLLISION_FACTOR_CACHE: dict[PearlVersion, list[tuple[float, float, float, float]]] = {
    PearlVersion.Legacy: [(0.0, 1.0, 0.0, 0.0)],
    PearlVersion.Post1205: [(0.0, 1.0, 0.0, 0.0)],
    PearlVersion.Post1212: [(0.0, 1.0, 0.0, 0.0)],
}


def run(
    data: GeneralData,
    destination: Optional[Space3D],
    max_ticks: int,
    world_collisions: List[AABBBox],
    offset: Optional[Space3D],
    version: PearlVersion
) -> Optional[CalculationResult]:
    movement = _MOVEMENT_MAP[version]
    return run_internal(movement, data, destination, max_ticks, world_collisions, offset)


def run_internal(
    movement,
    data: GeneralData,
    destination: Optional[Space3D],
    max_ticks: int,
    world_collisions: List[AABBBox],
    offset: Optional[Space3D]
) -> Optional[CalculationResult]:
    if not world_collisions:
        return _run_without_collisions(data, destination, max_ticks, offset, movement is MovementPost1212)

    pearl = PearlEntity.create(data.pearl_position, data.pearl_motion)
    tnt_entities = [TNTEntity.create(tnt.position, tnt.fuse) for tnt in data.tnt_charges]

    traces: List[Space3D] = [pearl.data.position.copy()]
    motion_traces: List[Space3D] = [pearl.data.motion.copy()]

    for tick in range(max_ticks):
        for tnt in tnt_entities:
            if tnt.fuse == tick:
                pearl.data.motion += calculate_tnt_motion(pearl.data.position, tnt.data.position)

        movement.run_tick_sequence(pearl, world_collisions)

        traces.append(pearl.data.position.copy())
        motion_traces.append(pearl.data.motion.copy())

    final_landing_pos = pearl.data.position

    distance_to_dest = 0.0
    is_success = False
    if destination:
        distance_to_dest = final_landing_pos.distance_2d(destination)
        is_success = distance_to_dest <= 0.25

    final_traces = _deduplicate(traces)
    final_motion_traces = _deduplicate(motion_traces)

    if offset:
        final_landing_pos = final_landing_pos + offset
        final_traces = [pos + offset for pos in final_traces]

    return CalculationResult(
        landing_position=final_landing_pos,
        pearl_trace=final_traces,
        pearl_motion_trace=final_motion_traces,
        is_successful=is_success,
        tick=max_ticks,
        final_motion=pearl.data.motion,
        distance=distance_to_dest
    )


def scan_trajectory(
    data: GeneralData,
    destination: Space3D,
    max_tick: int,
    valid_ticks: List[bool],
    world_collisions: List[AABBBox],
    offset: Space3D,
    version: PearlVersion,
    max_distance_sq: float,
    check_3d: bool
) -> List[SimResult]:
    movement = _MOVEMENT_MAP[version]
    return scan_internal(
        movement, data, destination, max_tick, valid_ticks,
        world_collisions, offset, max_distance_sq, check_3d
    )


def find_best_hit_for_ticks(
    data: GeneralData,
    destination: Space3D,
    ticks: List[int],
    offset: Space3D,
    version: PearlVersion,
    max_distance_sq: float,
    check_3d: bool
) -> Optional[SimResult]:
    if not ticks:
        return None

    if not data.tnt_charges:
        return _find_best_hit_without_collisions(
            data, destination, ticks, offset, version, max_distance_sq, check_3d
        )

    max_tick = ticks[-1]
    valid_ticks = [False] * (max_tick + 1)
    for tick in ticks:
        if tick <= max_tick:
            valid_ticks[tick] = True
    results = _scan_without_collisions(
        data, destination, max_tick, valid_ticks, offset, max_distance_sq,
        check_3d, version is PearlVersion.Post1212
    )
    if not results:
        return None
    return min(results, key=lambda item: (item.distance, item.tick))


def scan_internal(
    movement,
    data: GeneralData,
    destination: Space3D,
    max_tick: int,
    valid_ticks: List[bool],
    world_collisions: List[AABBBox],
    offset: Space3D,
    max_distance_sq: float,
    check_3d: bool
) -> List[SimResult]:
    if not world_collisions:
        return _scan_without_collisions(
            data, destination, max_tick, valid_ticks, offset,
            max_distance_sq, check_3d, movement is MovementPost1212
        )

    results: List[SimResult] = []
    pearl = PearlEntity.create(data.pearl_position, data.pearl_motion)
    tnt_entities = [TNTEntity.create(tnt.position, tnt.fuse) for tnt in data.tnt_charges]

    for tick in range(1, max_tick + 1):
        for tnt in tnt_entities:
            if tnt.fuse == tick - 1:
                pearl.data.motion += calculate_tnt_motion(pearl.data.position, tnt.data.position)

        movement.run_tick_sequence(pearl, world_collisions)

        current_pos = pearl.data.position + offset

        if tick < len(valid_ticks) and valid_ticks[tick]:
            dist_sq = current_pos.distance_sq(destination) if check_3d else current_pos.distance_2d_sq(destination)
            if dist_sq <= max_distance_sq:
                results.append(SimResult(
                    tick=tick,
                    position=current_pos,
                    motion=pearl.data.motion.copy(),
                    distance=math.sqrt(dist_sq)
                ))

        if pearl.data.motion.length_sq() < FLOAT_PRECISION_EPSILON:
            break

    return results


def calculate_tnt_motion(pearl_pos: Space3D, tnt_pos: Space3D) -> Space3D:
    tnt_pos_adjusted = Space3D(tnt_pos.x, tnt_pos.y + TNT_ENTITY_Y_OFFSET, tnt_pos.z)

    distance_vec = pearl_pos - tnt_pos_adjusted
    distance_scalar = distance_vec.length()

    if distance_scalar >= TNT_EXPLOSION_RADIUS:
        return Space3D()

    explosion_vec = Space3D(
        distance_vec.x,
        pearl_pos.y + (PEARL_EXPLOSION_Y_FACTOR * PEARL_HEIGHT) - tnt_pos_adjusted.y,
        distance_vec.z
    )

    explosion_vec_len = explosion_vec.length()
    if abs(explosion_vec_len) < FLOAT_PRECISION_EPSILON:
        return Space3D()

    explosion_vec = explosion_vec / explosion_vec_len
    explosion_strength = 1.0 - (distance_scalar / TNT_EXPLOSION_RADIUS)

    return explosion_vec * explosion_strength


def _deduplicate(lst: List[Space3D]) -> List[Space3D]:
    result: List[Space3D] = []
    for item in lst:
        if not result or item != result[-1]:
            result.append(item)
    return result


def _advance_motion(x: float, y: float, z: float, post1212: bool) -> Tuple[float, float, float, float, float, float]:
    if post1212:
        y -= PEARL_GRAVITY_ACCELERATION
        x *= PEARL_DRAG_MULTIPLIER
        y *= PEARL_DRAG_MULTIPLIER
        z *= PEARL_DRAG_MULTIPLIER
        return x, y, z, x, y, z

    dx = x
    dy = y
    dz = z
    x *= PEARL_DRAG_MULTIPLIER
    y = (y * PEARL_DRAG_MULTIPLIER) - PEARL_GRAVITY_ACCELERATION
    z *= PEARL_DRAG_MULTIPLIER
    return x, y, z, dx, dy, dz


def _group_tnt_charges(tnt_charges) -> dict:
    grouped = {}
    for tnt in tnt_charges:
        grouped.setdefault(tnt.fuse, []).append(tnt.position)
    return grouped


def _apply_tnt_charges(
    charges,
    pos_x: float,
    pos_y: float,
    pos_z: float,
    motion_x: float,
    motion_y: float,
    motion_z: float
) -> Tuple[float, float, float]:
    pearl_pos = Space3D(pos_x, pos_y, pos_z)
    for tnt_pos in charges:
        delta = calculate_tnt_motion(pearl_pos, tnt_pos)
        motion_x += delta.x
        motion_y += delta.y
        motion_z += delta.z
    return motion_x, motion_y, motion_z


def _run_without_collisions(
    data: GeneralData,
    destination: Optional[Space3D],
    max_ticks: int,
    offset: Optional[Space3D],
    post1212: bool
) -> CalculationResult:
    pos_x = data.pearl_position.x
    pos_y = data.pearl_position.y
    pos_z = data.pearl_position.z
    motion_x = data.pearl_motion.x
    motion_y = data.pearl_motion.y
    motion_z = data.pearl_motion.z

    traces: List[Space3D] = [Space3D(pos_x, pos_y, pos_z)]
    motion_traces: List[Space3D] = [Space3D(motion_x, motion_y, motion_z)]
    if not data.tnt_charges:
        if post1212:
            for _ in range(max_ticks):
                motion_y = (motion_y - PEARL_GRAVITY_ACCELERATION) * PEARL_DRAG_MULTIPLIER
                motion_x *= PEARL_DRAG_MULTIPLIER
                motion_z *= PEARL_DRAG_MULTIPLIER
                pos_x += motion_x
                pos_y += motion_y
                pos_z += motion_z
                traces.append(Space3D(pos_x, pos_y, pos_z))
                motion_traces.append(Space3D(motion_x, motion_y, motion_z))
        else:
            for _ in range(max_ticks):
                pos_x += motion_x
                pos_y += motion_y
                pos_z += motion_z
                motion_x *= PEARL_DRAG_MULTIPLIER
                motion_y = (motion_y * PEARL_DRAG_MULTIPLIER) - PEARL_GRAVITY_ACCELERATION
                motion_z *= PEARL_DRAG_MULTIPLIER
                traces.append(Space3D(pos_x, pos_y, pos_z))
                motion_traces.append(Space3D(motion_x, motion_y, motion_z))
    else:
        charges_by_tick = _group_tnt_charges(data.tnt_charges)
        for tick in range(max_ticks):
            charges = charges_by_tick.get(tick)
            if charges:
                motion_x, motion_y, motion_z = _apply_tnt_charges(
                    charges, pos_x, pos_y, pos_z, motion_x, motion_y, motion_z
                )
            motion_x, motion_y, motion_z, dx, dy, dz = _advance_motion(motion_x, motion_y, motion_z, post1212)
            pos_x += dx
            pos_y += dy
            pos_z += dz
            traces.append(Space3D(pos_x, pos_y, pos_z))
            motion_traces.append(Space3D(motion_x, motion_y, motion_z))

    final_landing_pos = Space3D(pos_x, pos_y, pos_z)
    distance_to_dest = 0.0
    is_success = False
    if destination:
        dx = pos_x - destination.x
        dz = pos_z - destination.z
        distance_to_dest = math.sqrt(dx * dx + dz * dz)
        is_success = distance_to_dest <= 0.25

    final_traces = _deduplicate(traces)
    final_motion_traces = _deduplicate(motion_traces)

    if offset:
        ox = offset.x
        oy = offset.y
        oz = offset.z
        final_landing_pos = Space3D(pos_x + ox, pos_y + oy, pos_z + oz)
        final_traces = [Space3D(pos.x + ox, pos.y + oy, pos.z + oz) for pos in final_traces]

    return CalculationResult(
        landing_position=final_landing_pos,
        pearl_trace=final_traces,
        pearl_motion_trace=final_motion_traces,
        is_successful=is_success,
        tick=max_ticks,
        final_motion=Space3D(motion_x, motion_y, motion_z),
        distance=distance_to_dest
    )


def _scan_without_collisions(
    data: GeneralData,
    destination: Space3D,
    max_tick: int,
    valid_ticks: List[bool],
    offset: Space3D,
    max_distance_sq: float,
    check_3d: bool,
    post1212: bool
) -> List[SimResult]:
    pos_x = data.pearl_position.x
    pos_y = data.pearl_position.y
    pos_z = data.pearl_position.z
    motion_x = data.pearl_motion.x
    motion_y = data.pearl_motion.y
    motion_z = data.pearl_motion.z
    off_x = offset.x
    off_y = offset.y
    off_z = offset.z
    dest_x = destination.x
    dest_y = destination.y
    dest_z = destination.z

    results: List[SimResult] = []

    if not data.tnt_charges:
        if post1212:
            for tick in range(1, max_tick + 1):
                motion_y = (motion_y - PEARL_GRAVITY_ACCELERATION) * PEARL_DRAG_MULTIPLIER
                motion_x *= PEARL_DRAG_MULTIPLIER
                motion_z *= PEARL_DRAG_MULTIPLIER
                pos_x += motion_x
                pos_y += motion_y
                pos_z += motion_z

                if valid_ticks[tick]:
                    cur_x = pos_x + off_x
                    cur_y = pos_y + off_y
                    cur_z = pos_z + off_z
                    dx = cur_x - dest_x
                    dz = cur_z - dest_z
                    if check_3d:
                        dy = cur_y - dest_y
                        dist_sq = dx * dx + dy * dy + dz * dz
                    else:
                        dist_sq = dx * dx + dz * dz

                    if dist_sq <= max_distance_sq:
                        results.append(SimResult(
                            tick=tick,
                            position=Space3D(cur_x, cur_y, cur_z),
                            motion=Space3D(motion_x, motion_y, motion_z),
                            distance=math.sqrt(dist_sq)
                        ))

                if (motion_x * motion_x) + (motion_y * motion_y) + (motion_z * motion_z) < FLOAT_PRECISION_EPSILON:
                    break
        else:
            for tick in range(1, max_tick + 1):
                pos_x += motion_x
                pos_y += motion_y
                pos_z += motion_z
                motion_x *= PEARL_DRAG_MULTIPLIER
                motion_y = (motion_y * PEARL_DRAG_MULTIPLIER) - PEARL_GRAVITY_ACCELERATION
                motion_z *= PEARL_DRAG_MULTIPLIER

                if valid_ticks[tick]:
                    cur_x = pos_x + off_x
                    cur_y = pos_y + off_y
                    cur_z = pos_z + off_z
                    dx = cur_x - dest_x
                    dz = cur_z - dest_z
                    if check_3d:
                        dy = cur_y - dest_y
                        dist_sq = dx * dx + dy * dy + dz * dz
                    else:
                        dist_sq = dx * dx + dz * dz

                    if dist_sq <= max_distance_sq:
                        results.append(SimResult(
                            tick=tick,
                            position=Space3D(cur_x, cur_y, cur_z),
                            motion=Space3D(motion_x, motion_y, motion_z),
                            distance=math.sqrt(dist_sq)
                        ))

                if (motion_x * motion_x) + (motion_y * motion_y) + (motion_z * motion_z) < FLOAT_PRECISION_EPSILON:
                    break
    else:
        charges_by_tick = _group_tnt_charges(data.tnt_charges)
        for tick in range(1, max_tick + 1):
            charges = charges_by_tick.get(tick - 1)
            if charges:
                motion_x, motion_y, motion_z = _apply_tnt_charges(
                    charges, pos_x, pos_y, pos_z, motion_x, motion_y, motion_z
                )
            motion_x, motion_y, motion_z, dx, dy, dz = _advance_motion(motion_x, motion_y, motion_z, post1212)
            pos_x += dx
            pos_y += dy
            pos_z += dz

            if valid_ticks[tick]:
                cur_x = pos_x + off_x
                cur_y = pos_y + off_y
                cur_z = pos_z + off_z
                dx = cur_x - dest_x
                dz = cur_z - dest_z
                if check_3d:
                    dy = cur_y - dest_y
                    dist_sq = dx * dx + dy * dy + dz * dz
                else:
                    dist_sq = dx * dx + dz * dz

                if dist_sq <= max_distance_sq:
                    results.append(SimResult(
                        tick=tick,
                        position=Space3D(cur_x, cur_y, cur_z),
                        motion=Space3D(motion_x, motion_y, motion_z),
                        distance=math.sqrt(dist_sq)
                    ))

            if (motion_x * motion_x) + (motion_y * motion_y) + (motion_z * motion_z) < FLOAT_PRECISION_EPSILON:
                break

    return results


def _find_best_hit_without_collisions(
    data: GeneralData,
    destination: Space3D,
    ticks: List[int],
    offset: Space3D,
    version: PearlVersion,
    max_distance_sq: float,
    check_3d: bool
) -> Optional[SimResult]:
    pos_x = data.pearl_position.x
    pos_y = data.pearl_position.y
    pos_z = data.pearl_position.z
    motion_x = data.pearl_motion.x
    motion_y = data.pearl_motion.y
    motion_z = data.pearl_motion.z
    off_x = offset.x
    off_y = offset.y
    off_z = offset.z
    dest_x = destination.x
    dest_y = destination.y
    dest_z = destination.z

    best_result: Optional[SimResult] = None
    no_collision_factors = _ensure_no_collision_factors(version, ticks[-1])

    for tick in ticks:
        pos_factor, vel_factor, grav_factor, vel_y_gravity = no_collision_factors[tick]

        cur_x = pos_x + (motion_x * pos_factor) + off_x
        cur_z = pos_z + (motion_z * pos_factor) + off_z
        cur_y = pos_y + (motion_y * pos_factor) - grav_factor + off_y

        dx = cur_x - dest_x
        dz = cur_z - dest_z
        if check_3d:
            dy = cur_y - dest_y
            dist_sq = dx * dx + dy * dy + dz * dz
        else:
            dist_sq = dx * dx + dz * dz

        if dist_sq > max_distance_sq:
            continue

        result = SimResult(
            tick=tick,
            position=Space3D(cur_x, cur_y, cur_z),
            motion=Space3D(
                motion_x * vel_factor,
                (motion_y * vel_factor) - vel_y_gravity,
                motion_z * vel_factor
            ),
            distance=math.sqrt(dist_sq)
        )

        if best_result is None or result.distance < best_result.distance or (
            abs(result.distance - best_result.distance) < FLOAT_PRECISION_EPSILON
            and result.tick < best_result.tick
        ):
            best_result = result

    return best_result


def _ensure_no_collision_factors(
    version: PearlVersion,
    tick: int
) -> list[tuple[float, float, float, float]]:
    cache = _NO_COLLISION_FACTOR_CACHE[version]
    if tick < len(cache):
        return cache

    drag = PEARL_DRAG_MULTIPLIER
    gravity = PEARL_GRAVITY_ACCELERATION
    one_minus_drag = 1.0 - drag

    if version is PearlVersion.Post1212:
        drag_gravity_factor = drag * gravity / one_minus_drag
        while len(cache) <= tick:
            current_tick = len(cache)
            vel_factor = drag ** current_tick
            geom_sum = (1.0 - vel_factor) / one_minus_drag
            pos_factor = drag * geom_sum
            cache.append((
                pos_factor,
                vel_factor,
                drag_gravity_factor * (current_tick - pos_factor),
                drag_gravity_factor * (1.0 - vel_factor)
            ))
    else:
        gravity_factor = gravity / one_minus_drag
        while len(cache) <= tick:
            current_tick = len(cache)
            vel_factor = drag ** current_tick
            geom_sum = (1.0 - vel_factor) / one_minus_drag
            cache.append((
                geom_sum,
                vel_factor,
                gravity_factor * (current_tick - geom_sum),
                gravity_factor * (1.0 - vel_factor)
            ))

    return cache
