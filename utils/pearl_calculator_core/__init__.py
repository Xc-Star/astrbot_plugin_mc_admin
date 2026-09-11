"""
PearlCalculatorCore - Python port of PearlCalculatorRS core library

A high-performance Minecraft vector pearl cannon calculator.
"""

from .api import (
    CalculationInput,
    PearlTraceInput,
    RawTraceInput,
    Space3DInput,
    TntGroupInput,
    calculate_pearl_trace_api,
    calculate_raw_trace_api,
    calculate_tnt_amount_api,
)
from .calculation import (
    calculate_pearl_trace,
    calculate_raw_trace,
    calculate_tnt_amount,
)
from .calculation.inputs import TNT, Cannon, GeneralData, Pearl
from .calculation.results import CalculationResult, TNTResult
from .physics import AABBBox, Direction, LayoutDirection, PearlVersion, Space3D
from .physics.constants.constants import *
from .settings import CannonMode, CannonSettings

__version__ = "2.2.0"
__all__ = [
    "Space3D",
    "Direction",
    "LayoutDirection",
    "PearlVersion",
    "AABBBox",
    "calculate_tnt_amount",
    "calculate_pearl_trace",
    "calculate_raw_trace",
    "Cannon",
    "Pearl",
    "GeneralData",
    "TNT",
    "TNTResult",
    "CalculationResult",
    "CannonMode",
    "CannonSettings",
    "CalculationInput",
    "PearlTraceInput",
    "RawTraceInput",
    "Space3DInput",
    "TntGroupInput",
    "calculate_tnt_amount_api",
    "calculate_pearl_trace_api",
    "calculate_raw_trace_api",
]
