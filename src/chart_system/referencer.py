"""
Chart Referencer — the synthesis layer.

The Chart Referencer cross-references all four charts and produces three
outputs:

1. Consensus Map  — where all charts agree → high-confidence knowledge
2. Divergence Map  — where charts disagree → classified disagreements
3. Discovery Signal — when Chart-Native flags absence the others can't explain

The Referencer does NOT produce a "fifth chart." That would defeat the purpose.
It produces relationships *between* charts — the interchart differential.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chart_system.charts import (
    ChartNative,
    ChartOutput,
    ChartType,
    Observation,
)


@dataclass
class ConsensusRegion:
    """
    A region where charts converge on the same reading.

    Attributes:
        location: The spatial/nodal identifier.
        signals: Signals that multiple charts agree on.
        agreement_score: How strongly the charts agree [0, 1].
        contributing_charts: Which charts contributed to this consensus.
        interpretation: Human-readable summary.
    """

    location: str
    signals: list[str]
    agreement_score: float
    contributing_charts: list[ChartType]
    interpretation: str = ""


@dataclass
class DivergenceRegion:
    """
    A region where charts disagree or complement each other.

    Attributes:
        location: The spatial/nodal identifier.
        signal: The signal in question.
        divergence_type: "constructive", "contradictory", or "complementary".
        chart_readings: Per-chart reading of this signal.
        interpretation: Human-readable summary of the divergence.
    """

    location: str
    signal: str
    divergence_type: str
    chart_readings: dict[str, float]
    interpretation: str = ""


@dataclass
class DiscoverySignal:
    """
    The system's most valuable output.

    A Discovery Signal fires when Chart-Native flags an absence pattern that
    the other three charts cannot explain. This is the Tlingit chart seeing
    precursors before anyone else knows there's a problem.

    Attributes:
        location: Where the unexplained absence was detected.
        absent_signal: What is missing.
        native_confidence: Chart-Native's confidence in the absence pattern.
        explanation_attempts: What the other charts say (usually nothing).
        severity: "info", "watch", "warning", "critical"
    """

    location: str
    absent_signal: str
    native_confidence: float
    explanation_attempts: dict[ChartType, str]
    severity: str = "info"


@dataclass
class ReferencerResult:
    """The complete output of a Chart Referencer run."""

    consensus: list[ConsensusRegion] = field(default_factory=list)
    divergence: list[DivergenceRegion] = field(default_factory=list)
    discovery: list[DiscoverySignal] = field(default_factory=list)
    chart_count: int = 0
    locations_covered: set[str] = field(default_factory=set)

    def summary(self) -> str:
        """Human-readable summary of the referencer's findings."""
        lines = [
            f"Chart Referencer Results ({self.chart_count} charts)",
            f"  Consensus regions: {len(self.consensus)}",
            f"  Divergence regions: {len(self.divergence)}",
            f"  Discovery signals: {len(self.discovery)}",
            f"  Locations covered: {len(self.locations_covered)}",
        ]
        if self.discovery:
            lines.append("\n  🌑 Discovery Signals (unexplained absence):")
            for d in self.discovery:
                lines.append(
                    f"    [{d.severity.upper()}] {d.location}: "
                    f"{d.absent_signal} (confidence: {d.native_confidence:.0%})"
                )
        return "\n".join(lines)


class ChartReferencer:
    """
    Cross-references multiple chart outputs.

    Usage::

        referencer = ChartReferencer()
        result = referencer.run([fisherman_out, sailor_out, tourist_out, native_out])
        print(result.summary())
    """

    # Minimum number of charts that must agree for consensus
    consensus_threshold: int = 3

    # Minimum confidence for a discovery signal
    discovery_threshold: float = 0.5

    def run(self, chart_outputs: list[ChartOutput]) -> ReferencerResult:
        """
        Run cross-referencing across all chart outputs.

        This is the main entry point. Pass in the outputs from all four charts
        and get back consensus, divergence, and discovery signals.

        Args:
            chart_outputs: List of ChartOutput from running each chart.

        Returns:
            ReferencerResult with three sections: consensus, divergence, discovery.
        """
        result = ReferencerResult(chart_count=len(chart_outputs))

        # Collect all locations across all charts
        all_locations: set[str] = set()
        for co in chart_outputs:
            for obs in co.positive_observations + co.negative_observations:
                all_locations.add(obs.location)
        result.locations_covered = all_locations

        # Process each location
        for location in all_locations:
            self._process_location(location, chart_outputs, result)

        return result

    def _process_location(
        self,
        location: str,
        chart_outputs: list[ChartOutput],
        result: ReferencerResult,
    ) -> None:
        """Cross-reference all charts at a single location."""

        # Gather what each chart sees at this location
        # signal → {chart_type → value}
        signal_readings: dict[str, dict[ChartType, float]] = {}

        for co in chart_outputs:
            for obs in co.positive_observations:
                if obs.location == location and obs.confidence > 0:
                    signal_readings.setdefault(obs.signal, {})[co.chart_type] = obs.value

        # Also track absences each chart noted
        # signal → {chart_type → confidence}
        absence_readings: dict[str, dict[ChartType, float]] = {}

        for co in chart_outputs:
            for obs in co.negative_observations:
                if obs.location == location:
                    absence_readings.setdefault(obs.signal, {})[co.chart_type] = (
                        obs.confidence
                    )

        # --- Consensus Detection ---
        # A signal has consensus if ≥ threshold charts agree it's present
        # with compatible values (within tolerance).
        for signal, readings in signal_readings.items():
            if len(readings) >= self.consensus_threshold:
                values = list(readings.values())
                spread = max(values) - min(values) if values else 1.0
                # Spread < 0.3 means rough agreement on magnitude
                if spread < 0.3:
                    agreement = 1.0 - spread
                    result.consensus.append(
                        ConsensusRegion(
                            location=location,
                            signals=[signal],
                            agreement_score=agreement,
                            contributing_charts=list(readings.keys()),
                            interpretation=(
                                f"{len(readings)} charts agree on '{signal}' "
                                f"at {location} (values cluster around "
                                f"{sum(values)/len(values):.2f})"
                            ),
                        )
                    )

        # --- Divergence Detection ---
        all_signals = set(signal_readings.keys()) | set(absence_readings.keys())
        for signal in all_signals:
            readings = signal_readings.get(signal, {})
            absences = absence_readings.get(signal, {})

            # Need at least 2 charts with opinions (positive or absent)
            total = set(readings.keys()) | set(absences.keys())
            if len(total) < 2:
                continue

            # If already in consensus, skip
            if signal in signal_readings and len(readings) >= self.consensus_threshold:
                values = list(readings.values())
                if max(values) - min(values) < 0.3:
                    continue

            # Classify divergence
            div_type = self._classify_divergence(signal, readings, absences)

            # Build the chart_readings dict
            chart_readings: dict[str, float] = {}
            for ct, val in readings.items():
                chart_readings[ct.value] = val
            for ct, conf in absences.items():
                chart_readings[ct.value] = 0.0  # absent = 0

            result.divergence.append(
                DivergenceRegion(
                    location=location,
                    signal=signal,
                    divergence_type=div_type,
                    chart_readings=chart_readings,
                    interpretation=self._divergence_interpretation(
                        div_type, signal, readings, absences
                    ),
                )
            )

        # --- Discovery Signal Detection ---
        # When Chart-Native sees something the others can't explain
        native_output = None
        for co in chart_outputs:
            if co.chart_type == ChartType.NATIVE:
                native_output = co
                break

        if native_output:
            other_outputs = [co for co in chart_outputs if co.chart_type != ChartType.NATIVE]

            for obs in native_output.positive_observations:
                if obs.location != location:
                    continue
                if obs.confidence < self.discovery_threshold:
                    continue

                # Can any other chart explain this?
                explained = False
                explanations: dict[ChartType, str] = {}
                for co in other_outputs:
                    other_signals = co.signals_at(location)
                    if obs.signal in other_signals:
                        explained = True
                        explanations[co.chart_type] = (
                            f"matched with value {other_signals[obs.signal]:.2f}"
                        )
                    else:
                        explanations[co.chart_type] = "no coverage"

                if not explained:
                    # Determine severity from confidence
                    if obs.confidence > 0.85:
                        severity = "critical"
                    elif obs.confidence > 0.7:
                        severity = "warning"
                    elif obs.confidence > 0.5:
                        severity = "watch"
                    else:
                        severity = "info"

                    result.discovery.append(
                        DiscoverySignal(
                            location=location,
                            absent_signal=obs.signal,
                            native_confidence=obs.confidence,
                            explanation_attempts=explanations,
                            severity=severity,
                        )
                    )

    def _classify_divergence(
        self,
        signal: str,
        readings: dict[ChartType, float],
        absences: dict[ChartType, float],
    ) -> str:
        """
        Classify a divergence as constructive, contradictory, or complementary.

        - Constructive: one chart sees something, others have no opinion.
          The observation extends existing models without conflict.
        - Contradictory: two charts make incompatible claims about the same signal.
          One model may be wrong, or conditions are changing.
        - Complementary: charts see different aspects of the same phenomenon.
          Neither wrong, both incomplete.
        """
        # If one chart has a positive reading and another explicitly flagged
        # this signal as absent → contradictory
        if readings and absences:
            # Check if any chart that has the signal is contradicted by one that doesn't
            positive_charts = set(readings.keys())
            absent_charts = set(absences.keys())
            if positive_charts & absent_charts:
                return "contradictory"
            if positive_charts and absent_charts:
                # Different charts see presence vs absence
                return "contradictory"

        # If multiple charts have readings with large spread → complementary
        if len(readings) >= 2:
            values = list(readings.values())
            spread = max(values) - min(values)
            if spread >= 0.3:
                return "complementary"

        # One chart sees something, others have no opinion → constructive
        if len(readings) == 1 and len(absences) >= 1:
            return "constructive"

        # Default: constructive (one chart's unique observation)
        return "constructive"

    def _divergence_interpretation(
        self,
        div_type: str,
        signal: str,
        readings: dict[ChartType, float],
        absences: dict[ChartType, float],
    ) -> str:
        """Generate a human-readable interpretation of a divergence."""
        chart_names = [ct.value for ct in readings.keys()] + [
            ct.value for ct in absences.keys()
        ]
        if div_type == "constructive":
            return (
                f"Constructive: one chart detects '{signal}' while others "
                f"have no opinion. Observation extends existing models."
            )
        elif div_type == "contradictory":
            return (
                f"Contradictory: charts disagree on '{signal}'. "
                f"One may be wrong, or conditions are changing faster "
                f"than models can track."
            )
        elif div_type == "complementary":
            return (
                f"Complementary: charts see different aspects of '{signal}'. "
                f"Neither wrong, both incomplete. Different true descriptions "
                f"of the same phenomenon."
            )
        return f"Unclassified divergence on '{signal}'."
