"""Chart configurations linking chart types to cognitive budget allocations.

Each chart type corresponds to a different γ allocation strategy under the
Conservation Law of Intelligence (γ + H = C). These configurations make the
relationship between chart archetypes and cognitive economics explicit.

The four charts divide the cognitive budget C differently:
  - Fisherman: high γ on ecological detail → low η for systemic thinking
  - Sailor: high γ on systemic flows → low η for local detail
  - Tourist: moderate γ on surface salience → high η for depth
  - Native: γ concentrated on absence/negative space → unique η profile
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .charts import ChartType, ChartProfile


@dataclass
class ChartConfiguration:
    """A chart type paired with its cognitive budget allocation.

    This formalizes how each chart archetype allocates its cognitive
    capacity C across committed attention (γ) and entropy (η).

    Attributes:
        chart_type: The archetype this configuration applies to.
        capacity: Total cognitive capacity C for this chart.
        gamma_allocation: How γ is distributed across signal categories.
            Each key is a sensor/signal category, each value is the
            fraction of C allocated to it. Sum should be ≤ 1.0.
        description: Human-readable explanation of this allocation.
    """

    chart_type: ChartType
    capacity: float = 100.0
    gamma_allocation: dict[str, float] = field(default_factory=dict)
    description: str = ""

    @property
    def total_gamma(self) -> float:
        """Total allocated attention across all categories."""
        return sum(self.gamma_allocation.values()) * self.capacity

    @property
    def total_gamma_ratio(self) -> float:
        """Fraction of C that is allocated (γ/C)."""
        return sum(self.gamma_allocation.values())

    @property
    def eta(self) -> float:
        """Unallocated cognitive potential."""
        return self.capacity - self.total_gamma

    @property
    def eta_ratio(self) -> float:
        """Fraction of C that is entropy (η/C)."""
        return 1.0 - self.total_gamma_ratio

    def is_thin(self) -> bool:
        """True when this chart runs thin (γ/C < 0.3)."""
        return self.total_gamma_ratio < 0.3

    def is_thick(self) -> bool:
        """True when this chart runs thick (γ/C > 0.7)."""
        return self.total_gamma_ratio > 0.7

    def allocation_for(self, signal: str) -> float:
        """Get the γ allocation for a specific signal category.

        Returns 0.0 if the signal is not explicitly allocated.
        """
        if signal in self.gamma_allocation:
            return self.gamma_allocation[signal]
        for pattern, weight in self.gamma_allocation.items():
            if pattern.endswith(":*"):
                prefix = pattern[:-2]
                if signal.startswith(prefix + ":") or signal == prefix:
                    return weight
            elif pattern.endswith("*"):
                if signal.startswith(pattern[:-1]):
                    return weight
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "chart_type": self.chart_type.value,
            "capacity": self.capacity,
            "gamma_allocation": dict(self.gamma_allocation),
            "total_gamma": self.total_gamma,
            "eta": self.eta,
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# Default configurations for each chart type
# ---------------------------------------------------------------------------

FISHERMAN_CONFIGURATION = ChartConfiguration(
    chart_type=ChartType.FISHERMAN,
    capacity=100.0,
    gamma_allocation={
        "abundance": 0.12,
        "bottom_structure": 0.11,
        "substrate": 0.10,
        "temperature": 0.09,
        "salinity": 0.08,
        "tidal_current": 0.10,
        "seasonal_pattern": 0.09,
        "migration_timing": 0.08,
        "ecological:*": 0.10,
        "species_count": 0.08,
    },
    description=(
        "Fisherman: γ concentrated on ecological detail. "
        "Sees the reef at the cost of the ocean."
    ),
)

SAILOR_CONFIGURATION = ChartConfiguration(
    chart_type=ChartType.SAILOR,
    capacity=100.0,
    gamma_allocation={
        "current": 0.12,
        "wind": 0.11,
        "wave_height": 0.10,
        "passage_safety": 0.11,
        "depth": 0.09,
        "hazard": 0.12,
        "fuel_efficiency": 0.08,
        "route_distance": 0.07,
        "systemic:*": 0.10,
    },
    description=(
        "Sailor: γ concentrated on systemic flows. "
        "Sees the ocean at the cost of the reef."
    ),
)

TOURIST_CONFIGURATION = ChartConfiguration(
    chart_type=ChartType.TOURIST,
    capacity=100.0,
    gamma_allocation={
        "scenic_value": 0.12,
        "landmark": 0.11,
        "accessibility": 0.10,
        "narrative:*": 0.09,
        "novelty": 0.10,
        "photogenic": 0.08,
        "story_worthy": 0.07,
    },
    description=(
        "Tourist: γ on surface salience. Lots of η left over — "
        "operationally shallow but narratively rich."
    ),
)

NATIVE_CONFIGURATION = ChartConfiguration(
    chart_type=ChartType.NATIVE,
    capacity=100.0,
    gamma_allocation={
        "absence:*": 0.14,
        "baseline_shift": 0.12,
        "missing_pattern": 0.12,
        "silence_quality": 0.10,
        "precursor_signal": 0.10,
        "meta:*": 0.08,
        "water_color_shift": 0.08,
        "behavioral_anomaly": 0.06,
    },
    description=(
        "Native: γ on negative space and absence. "
        "Sees what isn't there — the complement of the other three."
    ),
)

# Registry for easy lookup
DEFAULT_CONFIGURATIONS: dict[ChartType, ChartConfiguration] = {
    ChartType.FISHERMAN: FISHERMAN_CONFIGURATION,
    ChartType.SAILOR: SAILOR_CONFIGURATION,
    ChartType.TOURIST: TOURIST_CONFIGURATION,
    ChartType.NATIVE: NATIVE_CONFIGURATION,
}


def get_configuration(chart_type: ChartType) -> ChartConfiguration:
    """Get the default ChartConfiguration for a chart type."""
    return DEFAULT_CONFIGURATIONS[chart_type]
