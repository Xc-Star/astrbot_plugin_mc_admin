"""
PearlCalculatorCore - Python port of PearlCalculatorRS core library

A high-performance Minecraft vector pearl cannon calculator.
"""

from .physics import Space3D, Direction, LayoutDirection, PearlVersion, AABBBox
from .physics.constants.constants import *
from .calculation import calculate_tnt_amount, calculate_pearl_trace, calculate_raw_trace
from .calculation.inputs import Cannon, Pearl, GeneralData, TNT
from .calculation.results import TNTResult, CalculationResult
from .settings import CannonMode, CannonSettings
from .api import (
    CalculationInput,
    PearlTraceInput,
    RawTraceInput,
    Space3DInput,
    TntGroupInput,
    calculate_tnt_amount_api,
    calculate_pearl_trace_api,
    calculate_raw_trace_api,
)

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