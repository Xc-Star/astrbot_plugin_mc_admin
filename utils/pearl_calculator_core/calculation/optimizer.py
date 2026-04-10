from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional
from ..settings.types import CannonMode


@dataclass
class SearchParams:
    max_tnt: int
    max_vertical_tnt: Optional[int]
    search_radius: int
    has_vertical: bool
    is_valid_3d: bool
    cannon_mode: CannonMode


def generate_candidates(
    theoretical_groups: Dict[Tuple[int, int, int], List[int]],
    params: SearchParams
) -> List[Tuple[Tuple[int, int, int], List[int]]]:
    v_range = range(-1, 2) if params.has_vertical and params.is_valid_3d else range(0, 1)

    unique_candidates: Dict[Tuple[int, int, int], Set[int]] = {}

    for (center_red, center_blue, center_vert), valid_ticks in theoretical_groups.items():
        for r_offset in range(-params.search_radius, params.search_radius + 1):
            for b_offset in range(-params.search_radius, params.search_radius + 1):
                for v_offset in v_range:
                    current_red = center_red + r_offset
                    current_blue = center_blue + b_offset
                    current_vert = center_vert + v_offset

                    if current_red < 0 or current_blue < 0 or current_vert < 0:
                        continue

                    r_u32 = current_red
                    b_u32 = current_blue
                    v_u32 = current_vert

                    max_single_side = max(r_u32, b_u32)
                    if params.max_tnt > 0 and params.cannon_mode != CannonMode.Accumulation and not params.has_vertical and max_single_side > params.max_tnt:
                        continue

                    if params.max_vertical_tnt is not None and v_u32 > params.max_vertical_tnt:
                        continue

                    key = (r_u32, b_u32, v_u32)
                    if key not in unique_candidates:
                        unique_candidates[key] = set()
                    unique_candidates[key].update(valid_ticks)

    return [(key, sorted(ticks)) for key, ticks in unique_candidates.items()]
