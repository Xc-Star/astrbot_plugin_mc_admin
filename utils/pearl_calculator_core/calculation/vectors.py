from typing import Tuple, Optional
from ..physics.world.space import Space3D
from ..physics.world.direction import Direction
from ..physics.world.layout_direction import LayoutDirection
from .inputs import Cannon
from .simulation import calculate_tnt_motion


def resolve_vectors_for_direction(cannon: Cannon, direction: Direction) -> Tuple[Space3D, Space3D, Space3D]:
    pearl_calc_pos = cannon.pearl.offset.copy()
    pearl_calc_pos.y = cannon.pearl.position.y

    blue_duper = cannon.default_blue_duper or LayoutDirection.NorthEast
    red_duper = cannon.default_red_duper or LayoutDirection.NorthWest

    blue_duper_bits = layout_direction_to_cardinal_bits(blue_duper)
    direction_bits = direction.value

    if (direction_bits & blue_duper_bits) == 0:
        blue_tnt_loc = tnt_loc_from_layout(cannon, blue_duper)

        inverted_dir = direction.invert().value
        other_bits = (~(direction_bits | blue_duper_bits)) & 0b1111
        final_bits = other_bits | inverted_dir
        red_tnt_loc = tnt_loc_from_layout(cannon, cardinal_bits_to_layout_direction(final_bits))
    else:
        red_tnt_loc = tnt_loc_from_layout(cannon, red_duper)

        red_duper_bits = layout_direction_to_cardinal_bits(red_duper)
        inverted_dir = direction.invert().value
        other_bits = (~(direction_bits | red_duper_bits)) & 0b1111
        final_bits = other_bits | inverted_dir
        blue_tnt_loc = tnt_loc_from_layout(cannon, cardinal_bits_to_layout_direction(final_bits))

    red_vec = calculate_tnt_motion(pearl_calc_pos, red_tnt_loc)
    blue_vec = calculate_tnt_motion(pearl_calc_pos, blue_tnt_loc)

    vert_vec = Space3D()
    if cannon.vertical_tnt:
        vert_vec = calculate_tnt_motion(pearl_calc_pos, cannon.vertical_tnt)

    return (red_vec, blue_vec, vert_vec)


def tnt_loc_from_layout(cannon: Cannon, dir: LayoutDirection) -> Space3D:
    mapping = {
        LayoutDirection.NorthWest: cannon.north_west_tnt,
        LayoutDirection.NorthEast: cannon.north_east_tnt,
        LayoutDirection.SouthWest: cannon.south_west_tnt,
        LayoutDirection.SouthEast: cannon.south_east_tnt,
    }
    return mapping.get(dir, Space3D())


def layout_direction_to_cardinal_bits(dir: LayoutDirection) -> int:
    mapping = {
        LayoutDirection.NorthWest: Direction.North.value | Direction.West.value,
        LayoutDirection.NorthEast: Direction.North.value | Direction.East.value,
        LayoutDirection.SouthWest: Direction.South.value | Direction.West.value,
        LayoutDirection.SouthEast: Direction.South.value | Direction.East.value,
    }
    return mapping.get(dir, 0)


def cardinal_bits_to_layout_direction(bits: int) -> LayoutDirection:
    n = Direction.North.value
    s = Direction.South.value
    w = Direction.West.value
    e = Direction.East.value

    if (bits & (n | w)) == (n | w):
        return LayoutDirection.NorthWest
    elif (bits & (n | e)) == (n | e):
        return LayoutDirection.NorthEast
    elif (bits & (s | w)) == (s | w):
        return LayoutDirection.SouthWest
    else:
        return LayoutDirection.SouthEast