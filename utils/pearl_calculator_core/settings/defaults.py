from ..physics.world.space import Space3D
from .types import AppSettings, CannonSettings, CannonMode, Surface2D, PearlInfo


def default_app_settings() -> AppSettings:
    return AppSettings(cannon_settings=[default_cannon_settings()])


def default_cannon_settings() -> CannonSettings:
    return CannonSettings(
        max_tnt=0,
        red_tnt=None,
        blue_tnt=None,
        vertical_tnt=None,
        mode=CannonMode.Standard,
        default_red_direction=None,
        default_blue_direction=None,
        north_west_tnt=Space3D(),
        north_east_tnt=Space3D(),
        south_west_tnt=Space3D(),
        south_east_tnt=Space3D(),
        offset=Surface2D(0.0, 0.0),
        pearl=PearlInfo(Space3D(), Space3D())
    )


def default_general_data():
    from ..calculation.inputs import GeneralData
    return GeneralData(
        pearl_position=Space3D(0.5, 4.0625, 0.5),
        pearl_motion=Space3D(),
        tnt_charges=[]
    )