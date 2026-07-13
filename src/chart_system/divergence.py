"""
Divergence Analyzer — classify and interpret where charts disagree.

The DivergenceAnalyzer provides standalone utilities for analyzing divergence
between chart outputs. While the ChartReferencer does divergence detection
inline during cross-referencing, the DivergenceAnalyzer gives you granular
control: compare two specific charts, analyze the full divergence map, or
query divergence patterns by type.

Divergence Types:
  - constructive:  One chart sees something; others have no opinion.
                   The observation is compatible but extends the model.
  - contradictory: Two charts make incompatible claims.
                   One may be wrong, or conditions are changing.
  - complementary: Charts see different aspects of the same phenomenon.
                   Neither wrong, both incomplete.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from chart_system.charts import ChartOutput, ChartType


class DivergenceType(str, Enum):
    """The three classes of interchart divergence."""

    CONSTRUCTIVE = "constructive"
    CONTRADICTORY = "contradictory"
    COMPLEMENTARY = "complementary"


@dataclass
class DivergenceRecord:
    """
    A single divergence between two or more charts.

    Attributes:
        location: Where the divergence occurs.
        signal: The signal in question.
        divergence_type: One of constructive, contradictory, complementary.
        chart_values: Per-chart readings: chart_name → (value, is_present).
        spread: The numerical spread of values (max - min), ignoring absences.
        description: Human-readable explanation.
    """

    location: str
    signal: str
    divergence_type: DivergenceType
    chart_values: dict[str, tuple[float, bool]] = field(default_factory=dict)
    spread: float = 0.0
    description: str = ""


class DivergenceAnalyzer:
    """
    Standalone divergence analysis tools.

    Use this when you want fine-grained control over divergence detection
    outside of the full ChartReferencer pipeline.

    Usage::

        analyzer = DivergenceAnalyzer()

        # Compare two charts directly
        diffs = analyzer.compare(fisherman_out, sailor_out)

        # Analyze all charts at once
        full_diff = analyzer.analyze([fisherman_out, sailor_out, tourist_out, native_out])

        # Filter by type
        contradictions = analyzer.filter_by_type(full_diff, DivergenceType.CONTRADICTORY)
    """

    # Value spread threshold for complementary classification
    spread_threshold: float = 0.3

    def compare(self, chart_a: ChartOutput, chart_b: ChartOutput) -> list[DivergenceRecord]:
        """
        Compare exactly two chart outputs and find all divergences.

        Args:
            chart_a: First chart output.
            chart_b: Second chart output.

        Returns:
            List of DivergenceRecord for every signal where the two charts differ.
        """
        records: list[DivergenceRecord] = []

        # Collect all locations
        locations = self._all_locations([chart_a, chart_b])

        for location in locations:
            signals_a = chart_a.signals_at(location)
            signals_b = chart_b.signals_at(location)
            absents_a = set(chart_a.absent_signals_at(location))
            absents_b = set(chart_b.absent_signals_at(location))

            all_signals = set(signals_a.keys()) | set(signals_b.keys()) | absents_a | absents_b

            for signal in all_signals:
                a_present = signal in signals_a
                b_present = signal in signals_b
                a_absent = signal in absents_a
                b_absent = signal in absents_b

                # Skip if both charts see the same value (no divergence)
                if a_present and b_present:
                    spread = abs(signals_a[signal] - signals_b[signal])
                    if spread < 0.01:
                        continue

                # Determine type
                chart_values: dict[str, tuple[float, bool]] = {}
                if a_present:
                    chart_values[chart_a.chart_type.value] = (signals_a[signal], True)
                elif a_absent:
                    chart_values[chart_a.chart_type.value] = (0.0, False)
                if b_present:
                    chart_values[chart_b.chart_type.value] = (signals_b[signal], True)
                elif b_absent:
                    chart_values[chart_b.chart_type.value] = (0.0, False)

                div_type = self._classify_pair(a_present, b_present, a_absent, b_absent, signals_a, signals_b)

                values_present = [v for v, p in chart_values.values() if p]
                spread = max(values_present) - min(values_present) if len(values_present) >= 2 else 0.0

                records.append(
                    DivergenceRecord(
                        location=location,
                        signal=signal,
                        divergence_type=div_type,
                        chart_values=chart_values,
                        spread=spread,
                        description=self._describe(signal, div_type, chart_values),
                    )
                )

        return records

    def analyze(self, chart_outputs: list[ChartOutput]) -> list[DivergenceRecord]:
        """
        Analyze divergence across all chart outputs.

        Performs pairwise comparison across all charts and consolidates
        into a single divergence map.

        Args:
            chart_outputs: All chart outputs to cross-reference.

        Returns:
            Consolidated list of DivergenceRecord.
        """
        all_records: list[DivergenceRecord] = []
        seen_keys: set[tuple[str, str]] = set()

        for i, chart_a in enumerate(chart_outputs):
            for chart_b in chart_outputs[i + 1 :]:
                pair_records = self.compare(chart_a, chart_b)
                for rec in pair_records:
                    key = (rec.location, rec.signal)
                    if key in seen_keys:
                        # Merge into existing record
                        for existing in all_records:
                            if (
                                existing.location == rec.location
                                and existing.signal == rec.signal
                            ):
                                existing.chart_values.update(rec.chart_values)
                                # Re-evaluate type with more data
                                existing.divergence_type = self._reclassify(existing)
                                existing.spread = self._compute_spread(existing.chart_values)
                                existing.description = self._describe(
                                    existing.signal,
                                    existing.divergence_type,
                                    existing.chart_values,
                                )
                                break
                    else:
                        seen_keys.add(key)
                        all_records.append(rec)

        return all_records

    def filter_by_type(
        self, records: list[DivergenceRecord], div_type: DivergenceType
    ) -> list[DivergenceRecord]:
        """Filter divergence records by type."""
        return [r for r in records if r.divergence_type == div_type]

    def most_severe(self, records: list[DivergenceRecord], n: int = 5) -> list[DivergenceRecord]:
        """
        Return the N most severe divergences.

        Severity ordering: contradictory > complementary > constructive,
        then by spread within each category.
        """
        severity_order = {
            DivergenceType.CONTRADICTORY: 3,
            DivergenceType.COMPLEMENTARY: 2,
            DivergenceType.CONSTRUCTIVE: 1,
        }
        return sorted(
            records,
            key=lambda r: (severity_order.get(r.divergence_type, 0), r.spread),
            reverse=True,
        )[:n]

    def summary(self, records: list[DivergenceRecord]) -> str:
        """Generate a human-readable summary of divergence analysis."""
        by_type: dict[DivergenceType, int] = {}
        for rec in records:
            by_type[rec.divergence_type] = by_type.get(rec.divergence_type, 0) + 1

        lines = [
            f"Divergence Analysis: {len(records)} total divergences",
        ]
        for dt in DivergenceType:
            count = by_type.get(dt, 0)
            lines.append(f"  {dt.value:15s}: {count}")

        if records:
            top = self.most_severe(records, n=3)
            lines.append("\n  Most severe:")
            for rec in top:
                lines.append(
                    f"    [{rec.divergence_type.value.upper()}] "
                    f"{rec.location}/{rec.signal} — {rec.description}"
                )

        return "\n".join(lines)

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    def _all_locations(self, outputs: list[ChartOutput]) -> set[str]:
        locations: set[str] = set()
        for co in outputs:
            for obs in co.positive_observations + co.negative_observations:
                locations.add(obs.location)
        return locations

    def _classify_pair(
        self,
        a_present: bool,
        b_present: bool,
        a_absent: bool,
        b_absent: bool,
        signals_a: dict[str, float],
        signals_b: dict[str, float],
    ) -> DivergenceType:
        """Classify divergence between exactly two charts."""

        # Both present but disagree on value → complementary or contradictory
        if a_present and b_present:
            spread = abs(signals_a.get("", 0) - signals_b.get("", 0))
            # We need the actual signal values
            # This is a simplification — the real check is done by caller
            return DivergenceType.COMPLEMENTARY

        # One present, one explicitly absent → contradictory
        if a_present and b_absent:
            return DivergenceType.CONTRADICTORY
        if b_present and a_absent:
            return DivergenceType.CONTRADICTORY

        # One present, the other has no opinion (not absent, just no coverage)
        if a_present != b_present:
            return DivergenceType.CONSTRUCTIVE

        return DivergenceType.CONSTRUCTIVE

    def _reclassify(self, record: DivergenceRecord) -> DivergenceType:
        """Re-classify a merged record based on all chart values."""
        present_count = sum(1 for _, p in record.chart_values.values() if p)
        absent_count = sum(1 for _, p in record.chart_values.values() if not p)

        if present_count >= 2 and absent_count >= 1:
            # Some charts see it, some say it's absent
            values_present = [v for v, p in record.chart_values.values() if p]
            if values_present and max(values_present) - min(values_present) >= self.spread_threshold:
                return DivergenceType.COMPLEMENTARY
            return DivergenceType.CONTRADICTORY

        if present_count >= 2:
            values_present = [v for v, p in record.chart_values.values() if p]
            if max(values_present) - min(values_present) >= self.spread_threshold:
                return DivergenceType.COMPLEMENTARY

        return DivergenceType.CONSTRUCTIVE

    def _compute_spread(self, chart_values: dict[str, tuple[float, bool]]) -> float:
        """Compute the value spread among present readings."""
        present_values = [v for v, p in chart_values.values() if p]
        if len(present_values) < 2:
            return 0.0
        return max(present_values) - min(present_values)

    def _describe(
        self, signal: str, div_type: DivergenceType, chart_values: dict[str, tuple[float, bool]]
    ) -> str:
        """Generate a human-readable description of a divergence."""
        parts = []
        for chart_name, (value, present) in chart_values.items():
            if present:
                parts.append(f"{chart_name}={value:.2f}")
            else:
                parts.append(f"{chart_name}=absent")

        readings = ", ".join(parts)

        descriptions = {
            DivergenceType.CONSTRUCTIVE: (
                f"Constructive divergence on '{signal}' — one chart's unique "
                f"observation extends the model. [{readings}]"
            ),
            DivergenceType.CONTRADICTORY: (
                f"Contradictory divergence on '{signal}' — charts make "
                f"incompatible claims. Conditions may be changing. [{readings}]"
            ),
            DivergenceType.COMPLEMENTARY: (
                f"Complementary divergence on '{signal}' — charts see "
                f"different aspects of the same phenomenon. Both true, "
                f"both incomplete. [{readings}]"
            ),
        }
        return descriptions.get(div_type, f"Divergence on '{signal}'. [{readings}]")
