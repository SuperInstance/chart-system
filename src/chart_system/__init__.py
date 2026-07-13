"""
Chart System — Polyformal navigation for Working Animal Architecture.

Four chart configurations that cross-reference the same problem space.
The overlap is consensus. The divergence is discovery. The negative space
is where the future is.
"""

from chart_system.charts import (
    ChartFisherman,
    ChartSailor,
    ChartTourist,
    ChartNative,
    ChartProfile,
    ChartOutput,
    Observation,
)
from chart_system.referencer import ChartReferencer, ReferencerResult
from chart_system.configuration import (
    ChartConfiguration,
    FISHERMAN_CONFIGURATION,
    SAILOR_CONFIGURATION,
    TOURIST_CONFIGURATION,
    NATIVE_CONFIGURATION,
    get_configuration,
)

__version__ = "0.1.0"

__all__ = [
    # Charts
    "ChartFisherman",
    "ChartSailor",
    "ChartTourist",
    "ChartNative",
    "ChartProfile",
    "ChartOutput",
    "Observation",
    # Referencer
    "ChartReferencer",
    "ReferencerResult",
    # Divergence
    "DivergenceAnalyzer",
    "DivergenceType",
    # Configurations
    "ChartConfiguration",
    "FISHERMAN_CONFIGURATION",
    "SAILOR_CONFIGURATION",
    "TOURIST_CONFIGURATION",
    "NATIVE_CONFIGURATION",
    "get_configuration",
]
