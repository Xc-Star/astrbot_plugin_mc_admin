from __future__ import annotations
from enum import Enum
from typing import Tuple, TYPE_CHECKING
from ..constants.constants import PEARL_DRAG_MULTIPLIER, PEARL_GRAVITY_ACCELERATION
from ..aabb.aabb_box import AABBBox

if TYPE_CHECKING:
    from .pearl_entities import PearlEntity


class PearlVersion(Enum):
    Legacy = "Legacy"
    Post1205 = "Post1205"
    Post1212 = "Post1212"

    def apply_grav_drag_tick(self, velocity: float, gravity: float, drag: float) -> float:
        if self in (PearlVersion.Legacy, PearlVersion.Post1205):
            return (velocity * drag) + gravity
        else:
            return (velocity + gravity) * drag

    def get_projection_multiplier(self, drag: float) -> float:
        if self in (PearlVersion.Legacy, PearlVersion.Post1205):
            return 1.0
        else:
            return drag

    def apply_motion_tick(self, velocity: float, drag: float) -> Tuple[float, float]:
        if self in (PearlVersion.Legacy, PearlVersion.Post1205):
            displacement = velocity
            new_velocity = velocity * drag
            return (new_velocity, displacement)
        else:
            new_velocity = velocity * drag
            displacement = new_velocity
            return (new_velocity, displacement)


class PearlMovement:
    @staticmethod
    def run_tick_sequence(pearl: PearlEntity, world_collisions: list) -> None:
        raise NotImplementedError


class MovementLegacy(PearlMovement):
    @staticmethod
    def run_tick_sequence(pearl: PearlEntity, world_collisions: list) -> None:
        pearl.data.move_entity(
            pearl.data.motion.x,
            pearl.data.motion.y,
            pearl.data.motion.z,
            world_collisions
        )

        mx = float(pearl.data.motion.x) * PEARL_DRAG_MULTIPLIER
        my = float(pearl.data.motion.y) * PEARL_DRAG_MULTIPLIER
        mz = float(pearl.data.motion.z) * PEARL_DRAG_MULTIPLIER

        if pearl.data.is_gravity:
            my -= PEARL_GRAVITY_ACCELERATION

        pearl.data.motion.x = mx
        pearl.data.motion.y = my
        pearl.data.motion.z = mz


class MovementPost1205(PearlMovement):
    @staticmethod
    def run_tick_sequence(pearl: PearlEntity, world_collisions: list) -> None:
        pearl.data.move_entity(
            pearl.data.motion.x,
            pearl.data.motion.y,
            pearl.data.motion.z,
            world_collisions
        )

        pearl.data.motion *= PEARL_DRAG_MULTIPLIER
        if pearl.data.is_gravity:
            pearl.data.motion.y -= PEARL_GRAVITY_ACCELERATION


class MovementPost1212(PearlMovement):
    @staticmethod
    def run_tick_sequence(pearl: PearlEntity, world_collisions: list) -> None:
        if pearl.data.is_gravity:
            pearl.data.motion.y -= PEARL_GRAVITY_ACCELERATION
        pearl.data.motion *= PEARL_DRAG_MULTIPLIER

        pearl.data.move_entity(
            pearl.data.motion.x,
            pearl.data.motion.y,
            pearl.data.motion.z,
            world_collisions
        )