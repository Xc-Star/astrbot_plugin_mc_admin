from __future__ import annotations

from ..physics.constants.constants import FLOAT_PRECISION_EPSILON
from ..physics.entities.movement import PearlVersion
from ..physics.world.direction import Direction
from ..physics.world.space import Space3D
from .inputs import Cannon
from .optimizer import SearchParams, generate_candidates
from .results import TNTResult
from .solver import solve_theoretical_tnt
from .trace import validate_candidates
from .vectors import resolve_vectors_for_direction


def calculate_tnt_amount(
    cannon: Cannon,
    destination: Space3D,
    max_tnt: int,
    max_vertical_tnt: int | None,
    max_ticks: int,
    max_distance: float,
    version: PearlVersion
) -> list[TNTResult]:
    pearl_start_absolute_pos = cannon.pearl.position + cannon.pearl.offset
    true_distance = destination - pearl_start_absolute_pos

    if true_distance.length_sq() < FLOAT_PRECISION_EPSILON:
        return []

    yaw = pearl_start_absolute_pos.angle_to_yaw(destination)
    flight_directions = Direction.from_angle_with_fallbacks(yaw)

    max_distance_sq = max_distance * max_distance
    all_results: list[TNTResult] = []

    for flight_direction in flight_directions:
        red_vec, blue_vec, vert_vec = resolve_vectors_for_direction(cannon, flight_direction)

        theoretical_groups = solve_theoretical_tnt(
            red_vec, blue_vec, vert_vec,
            pearl_start_absolute_pos,
            cannon.pearl.motion,
            destination,
            max_ticks,
            version
        )

        is_valid_3d = vert_vec.length_sq() > FLOAT_PRECISION_EPSILON

        search_params = SearchParams(
            max_tnt=max_tnt,
            max_vertical_tnt=max_vertical_tnt,
            search_radius=5,
            has_vertical=cannon.vertical_tnt is not None,
            is_valid_3d=is_valid_3d,
            cannon_mode=cannon.mode
        )

        candidates = generate_candidates(theoretical_groups, search_params)

        results = validate_candidates(
            candidates,
            red_vec, blue_vec, vert_vec,
            cannon.pearl.position,
            cannon.pearl.motion,
            cannon.pearl.offset,
            destination,
            max_distance_sq,
            version,
            flight_direction
        )

        all_results.extend(results)

    return all_results
