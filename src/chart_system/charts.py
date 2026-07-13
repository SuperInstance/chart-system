"""
Chart configurations and observation model.

Each chart is a way of seeing. The same data passes through four different
attention configurations, each optimized for a different agenda. The charts
are not layered — they are parallel projections of the same problem space.

The four charts correspond to four ways of attending to an ocean:
  - Fisherman: ecological detail, bottom structure, local patterns
  - Sailor: systemic flows, weather patterns, navigational structure
  - Tourist: surface features, landmarks, narrative salience
  - Native: negative space, absence patterns, what others don't see
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------


class ChartType(str, Enum):
    """The four chart archetypes."""

    FISHERMAN = "fisherman"
    SAILOR = "sailor"
    TOURIST = "tourist"
    NATIVE = "native"


@dataclass
class Observation:
    """
    A single observation in the shared data layer.

    All charts receive the same observations. What differs is how each chart
    weights, filters, and interprets them.

    Attributes:
        location: Identifier for the region or coordinate being observed.
        signal: The type of measurement or signal (e.g. "abundance", "current").
        value: Normalized signal value [0, 1].
        confidence: How reliable this observation is [0, 1].
        expected: If True, this is a record of something that was expected
            but not found — a negative observation. This is the primary
            input for Chart-Native.
        metadata: Additional context.
    """

    location: str
    signal: str
    value: float
    confidence: float = 1.0
    expected: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartProfile:
    """
    Configuration that defines a chart's way of seeing.

    Each profile encodes a specific attention allocation — the γ/H budget
    from the Conservation Law of Intelligence (γ + H = C). Different profiles
    allocate the same fixed budget differently, producing different strengths
    and different blind spots.

    Attributes:
        chart_type: Which archetype this profile implements.
        sensor_weights: How much attention to give each signal category.
            Signals not listed get weight 0 (invisible to this chart).
        opcode_priority: Ordered processing operations the chart favors.
        horizon: Temporal reach — "short", "medium", "long", "very_long".
        abstraction_depth: How many layers of abstraction to traverse.
        description: Human-readable summary of this chart's agenda.
    """

    chart_type: ChartType
    sensor_weights: dict[str, float]
    opcode_priority: list[str]
    horizon: str
    abstraction_depth: int
    description: str


@dataclass
class ChartOutput:
    """
    The output of running a single chart over a set of observations.

    Each chart produces:
      - positive_observations: what it sees (with chart-specific weighting)
      - negative_observations: what it expected but didn't find
      - chart_type: which chart produced this output
      - coverage: the set of signals this chart actually attended to
      - blind_spots: signals this chart is known to ignore
    """

    chart_type: ChartType
    positive_observations: list[Observation] = field(default_factory=list)
    negative_observations: list[Observation] = field(default_factory=list)
    coverage: set[str] = field(default_factory=set)
    blind_spots: set[str] = field(default_factory=set)

    def signals_at(self, location: str) -> dict[str, float]:
        """Return a mapping of signal → weighted value at a location."""
        result: dict[str, float] = {}
        for obs in self.positive_observations:
            if obs.location == location:
                result[obs.signal] = obs.value
        return result

    def absent_signals_at(self, location: str) -> list[str]:
        """Return signals that were expected but missing at a location."""
        return [
            obs.signal
            for obs in self.negative_observations
            if obs.location == location
        ]


# ---------------------------------------------------------------------------
# Chart base
# ---------------------------------------------------------------------------


class Chart:
    """
    Base class for all charts.

    A Chart holds a ChartProfile and knows how to process raw observations
    through that profile's lens — filtering, weighting, and generating
    both positive findings and negative observations (expected-but-absent).
    """

    profile: ChartProfile

    def plot(self, observations: list[Observation]) -> ChartOutput:
        """
        Process raw observations through this chart's lens.

        This is the core operation: the same data passes through the chart's
        attention configuration and emerges as a chart-specific reading.

        Steps:
          1. Filter observations to those this chart can see (sensor weights).
          2. Apply chart-specific value weighting.
          3. Detect expected signals that are absent (negative observations).
          4. Record coverage and blind spots.
        """
        output = ChartOutput(
            chart_type=self.profile.chart_type,
            coverage=set(self.profile.sensor_weights.keys()),
            blind_spots=set(),
        )

        # Phase 1: Positive observations — filter and weight
        for obs in observations:
            weight = self._signal_weight(obs.signal)
            if weight > 0:
                weighted = Observation(
                    location=obs.location,
                    signal=obs.signal,
                    value=obs.value * weight,
                    confidence=obs.confidence * weight,
                    expected=obs.expected,
                    metadata={**obs.metadata, "chart": self.profile.chart_type.value},
                )
                output.positive_observations.append(weighted)

        # Phase 2: Negative observations — what did we expect but not see?
        seen_signals_by_location: dict[str, set[str]] = {}
        for obs in output.positive_observations:
            seen_signals_by_location.setdefault(obs.location, set()).add(obs.signal)

        all_locations = {obs.location for obs in observations}
        for location in all_locations:
            seen = seen_signals_by_location.get(location, set())
            for expected_signal, weight in self.profile.sensor_weights.items():
                if weight > 0 and expected_signal not in seen:
                    output.negative_observations.append(
                        Observation(
                            location=location,
                            signal=expected_signal,
                            value=0.0,
                            confidence=weight,
                            expected=False,
                            metadata={
                                "chart": self.profile.chart_type.value,
                                "note": "expected but absent",
                            },
                        )
                    )

        # Phase 3: Record blind spots — signals this chart structurally ignores
        all_signals = {obs.signal for obs in observations}
        output.blind_spots = all_signals - set(self.profile.sensor_weights.keys())

        return output

    def _signal_weight(self, signal: str) -> float:
        """
        Resolve a signal name to its weight for this chart.

        Signals can match either directly ("abundance" → 0.9) or via
        prefix categories ("ecological:*" matches "ecological:temperature").
        """
        if signal in self.profile.sensor_weights:
            return self.profile.sensor_weights[signal]
        for pattern, weight in self.profile.sensor_weights.items():
            if pattern.endswith(":*"):
                prefix = pattern[:-2]
                if signal.startswith(prefix + ":") or signal == prefix:
                    return weight
            elif pattern.endswith("*"):
                if signal.startswith(pattern[:-1]):
                    return weight
        return 0.0


# ---------------------------------------------------------------------------
# The four charts
# ---------------------------------------------------------------------------


class ChartFisherman(Chart):
    """
    🐟 The Fisherman's Chart — ecological detail, bottom structure.

    High resolution on local ecology: where the fish are, why they're there,
    when they'll move, what they're eating. The texture of the ecosystem at
    the level where life actually happens.

    Blind to: systemic trade routes overhead, surface narratives, the shape
    of what isn't there.
    """

    profile = ChartProfile(
        chart_type=ChartType.FISHERMAN,
        sensor_weights={
            "abundance": 0.95,
            "bottom_structure": 0.90,
            "substrate": 0.85,
            "temperature": 0.80,
            "salinity": 0.70,
            "tidal_current": 0.85,
            "seasonal_pattern": 0.80,
            "migration_timing": 0.75,
            "ecological:*": 0.85,
            "species_count": 0.80,
            "juvenile_presence": 0.90,
            "feed_activity": 0.75,
        },
        opcode_priority=[
            "PATTERN_MATCH",
            "TEMPORAL_CORRELATE",
            "LOCAL_COMPARE",
        ],
        horizon="short",
        abstraction_depth=2,
        description=(
            "Ecological detail chart. Sees local patterns, seasonal cycles, "
            "and bottom structure. High specificity, low abstraction."
        ),
    )


class ChartSailor(Chart):
    """
    ⛵ The Sailor's Chart — systemic flows, weather patterns, safe passages.

    The ocean as a transportation network. Currents, prevailing winds, hazard
    bearings, navigational structure. The systemic patterns governing movement.

    Blind to: the fish under the hull, the story behind the landmark, the
    absence patterns that signal future change.
    """

    profile = ChartProfile(
        chart_type=ChartType.SAILOR,
        sensor_weights={
            "current": 0.95,
            "wind": 0.90,
            "wave_height": 0.85,
            "passage_safety": 0.90,
            "depth": 0.80,
            "hazard": 0.95,
            "fuel_efficiency": 0.75,
            "route_distance": 0.70,
            "systemic:*": 0.85,
            "weather_pattern": 0.85,
            "visibility": 0.70,
            "pressure_gradient": 0.80,
        },
        opcode_priority=[
            "FLOW_MODEL",
            "PATH_PLAN",
            "RISK_ASSESS",
        ],
        horizon="long",
        abstraction_depth=5,
        description=(
            "Systemic flow chart. Sees global structure, navigational safety, "
            "and weather patterns. High abstraction, coarse local detail."
        ),
    )


class ChartTourist(Chart):
    """
    📸 The Tourist's Chart — surface features, landmarks, narratives.

    The ocean as an experience. What to look at, what to tell people about,
    what makes this place different. The surface the other charts treat as
    transparent.

    Blind to: everything below the surface — both ecology and navigational
    structure. Most likely to be operationally wrong but socially right.
    """

    profile = ChartProfile(
        chart_type=ChartType.TOURIST,
        sensor_weights={
            "scenic_value": 0.95,
            "landmark": 0.90,
            "accessibility": 0.85,
            "narrative:*": 0.80,
            "novelty": 0.85,
            "photogenic": 0.80,
            "story_worthy": 0.75,
            "wildlife_visible": 0.70,
            "crowd_density": 0.65,
            "amenity": 0.60,
        },
        opcode_priority=[
            "NARRATIVE_STRUCT",
            "SALIENCE_DETECT",
            "NOVELTY_SCORE",
        ],
        horizon="medium",
        abstraction_depth=1,
        description=(
            "Surface feature chart. Sees landmarks, narratives, and scenic "
            "value. High salience detection, low depth."
        ),
    )


class ChartNative(Chart):
    """
    🌑 The Native's Chart — negative space, absence patterns, meta-observation.

    What the other three charts don't see. Absence of expected signals,
    relationships between absences, liminal signals. The Tlingit chart that
    marks the water color when fish are fasting — seeing precursors before
    anyone else knows there's a problem.

    Does not duplicate other charts' coverage. Its entire budget goes to
    the negative space. It primarily consumes the negative observations
    of the other charts, plus its own positive observations about absence.
    """

    profile = ChartProfile(
        chart_type=ChartType.NATIVE,
        sensor_weights={
            "absence:*": 0.95,
            "baseline_shift": 0.90,
            "missing_pattern": 0.90,
            "silence_quality": 0.85,
            "precursor_signal": 0.85,
            "meta:*": 0.80,
            "water_color_shift": 0.80,
            "behavioral_anomaly": 0.75,
            "seasonal_displacement": 0.80,
            "expected_absent": 0.95,
        },
        opcode_priority=[
            "ABSENCE_DETECT",
            "BASELINE_COMPARE",
            "CROSS_CHART_META",
        ],
        horizon="very_long",
        abstraction_depth=3,
        description=(
            "Negative space chart. Sees absence, precursors, and meta-patterns. "
            "Defined by complementarity to the other three charts."
        ),
    )
