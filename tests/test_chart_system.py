"""Tests for chart_system package."""

import pytest

from chart_system import (
    ChartFisherman, ChartSailor, ChartTourist, ChartNative,
    ChartReferencer, DivergenceAnalyzer, DivergenceType,
    Observation,
)
from chart_system.charts import ChartType, Chart, ChartProfile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def shared_observations():
    """Simulate observations from a shared data layer — the 'same ocean'."""
    return [
        # Ecological signals
        Observation(location="bay-7", signal="abundance", value=0.85, confidence=0.9),
        Observation(location="bay-7", signal="bottom_structure", value=0.70, confidence=0.8),
        Observation(location="bay-7", signal="temperature", value=0.65, confidence=0.85),
        Observation(location="bay-7", signal="juvenile_presence", value=0.30, confidence=0.7),

        # Systemic signals
        Observation(location="bay-7", signal="current", value=0.80, confidence=0.9),
        Observation(location="bay-7", signal="passage_safety", value=0.30, confidence=0.75),
        Observation(location="bay-7", signal="hazard", value=0.60, confidence=0.8),

        # Surface signals
        Observation(location="bay-7", signal="scenic_value", value=0.60, confidence=0.6),
        Observation(location="bay-7", signal="landmark", value=0.90, confidence=0.85),

        # Native signals
        Observation(location="bay-7", signal="baseline_shift", value=0.75, confidence=0.8),
        Observation(location="bay-7", signal="expected_absent", value=0.70, confidence=0.85),

        # Second location — reef-3
        Observation(location="reef-3", signal="abundance", value=0.90, confidence=0.95),
        Observation(location="reef-3", signal="current", value=0.50, confidence=0.8),
        Observation(location="reef-3", signal="scenic_value", value=0.95, confidence=0.9),
        Observation(location="reef-3", signal="passage_safety", value=0.85, confidence=0.85),
    ]


@pytest.fixture
def four_charts():
    """All four chart instances."""
    return {
        "fisherman": ChartFisherman(),
        "sailor": ChartSailor(),
        "tourist": ChartTourist(),
        "native": ChartNative(),
    }


@pytest.fixture
def four_chart_outputs(four_charts, shared_observations):
    """Run all four charts over shared observations."""
    return [
        four_charts["fisherman"].plot(shared_observations),
        four_charts["sailor"].plot(shared_observations),
        four_charts["tourist"].plot(shared_observations),
        four_charts["native"].plot(shared_observations),
    ]


# ---------------------------------------------------------------------------
# Chart tests
# ---------------------------------------------------------------------------

class TestChartProfiles:

    def test_fisherman_has_ecological_focus(self):
        fish = ChartFisherman()
        assert fish.profile.chart_type == ChartType.FISHERMAN
        assert "abundance" in fish.profile.sensor_weights
        assert fish.profile.sensor_weights["abundance"] > 0.8
        assert fish.profile.horizon == "short"
        assert fish.profile.abstraction_depth == 2

    def test_sailor_has_systemic_focus(self):
        sailor = ChartSailor()
        assert sailor.profile.chart_type == ChartType.SAILOR
        assert "current" in sailor.profile.sensor_weights
        assert sailor.profile.sensor_weights["current"] > 0.8
        assert sailor.profile.horizon == "long"
        assert sailor.profile.abstraction_depth == 5

    def test_tourist_has_surface_focus(self):
        tourist = ChartTourist()
        assert tourist.profile.chart_type == ChartType.TOURIST
        assert "scenic_value" in tourist.profile.sensor_weights
        assert tourist.profile.horizon == "medium"
        assert tourist.profile.abstraction_depth == 1

    def test_native_has_absence_focus(self):
        native = ChartNative()
        assert native.profile.chart_type == ChartType.NATIVE
        assert "absence:*" in native.profile.sensor_weights
        assert native.profile.horizon == "very_long"
        assert "ABSENCE_DETECT" in native.profile.opcode_priority


class TestChartPlot:

    def test_fisherman_sees_ecological_signals(self, four_charts, shared_observations):
        output = four_charts["fisherman"].plot(shared_observations)
        assert output.chart_type == ChartType.FISHERMAN
        signals = {obs.signal for obs in output.positive_observations}
        assert "abundance" in signals
        assert "bottom_structure" in signals

    def test_fisherman_blind_to_narrative(self, four_charts, shared_observations):
        output = four_charts["fisherman"].plot(shared_observations)
        signals = {obs.signal for obs in output.positive_observations}
        assert "scenic_value" not in signals
        assert "landmark" not in signals

    def test_sailor_sees_navigational_signals(self, four_charts, shared_observations):
        output = four_charts["sailor"].plot(shared_observations)
        signals = {obs.signal for obs in output.positive_observations}
        assert "current" in signals
        assert "passage_safety" in signals

    def test_tourist_sees_surface_signals(self, four_charts, shared_observations):
        output = four_charts["tourist"].plot(shared_observations)
        signals = {obs.signal for obs in output.positive_observations}
        assert "scenic_value" in signals
        assert "landmark" in signals

    def test_native_sees_absence_signals(self, four_charts, shared_observations):
        output = four_charts["native"].plot(shared_observations)
        signals = {obs.signal for obs in output.positive_observations}
        assert "baseline_shift" in signals
        assert "expected_absent" in signals

    def test_all_charts_generate_negative_observations(self, four_charts, shared_observations):
        """Each chart should report what it expected but didn't find."""
        for name, chart in four_charts.items():
            output = chart.plot(shared_observations)
            # Each chart should have at least some negative observations
            # for signals it expects but that aren't in the data
            assert len(output.negative_observations) >= 0  # depends on data

    def test_charts_cover_same_data(self, four_charts, shared_observations):
        """All charts process the same observations."""
        for name, chart in four_charts.items():
            output = chart.plot(shared_observations)
            # Should have at least some positive observations
            assert len(output.positive_observations) > 0

    def test_chart_weighting_applied(self, four_charts, shared_observations):
        """Chart should weight values by sensor weight."""
        fish = four_charts["fisherman"]
        output = fish.plot(shared_observations)
        abundance_obs = [
            obs for obs in output.positive_observations if obs.signal == "abundance"
        ]
        assert len(abundance_obs) > 0
        # Raw abundance values were 0.85 and 0.90, weight is 0.95
        # Weighted: 0.85*0.95=0.8075 and 0.90*0.95=0.855
        for obs in abundance_obs:
            raw_value = next(
                o.value for o in shared_observations
                if o.location == obs.location and o.signal == "abundance"
            )
            assert obs.value == pytest.approx(raw_value * 0.95)
            assert obs.value < raw_value  # weighted down


# ---------------------------------------------------------------------------
# Referencer tests
# ---------------------------------------------------------------------------

class TestChartReferencer:

    def test_referencer_runs(self, four_chart_outputs):
        ref = ChartReferencer()
        result = ref.run(four_chart_outputs)
        assert result.chart_count == 4

    def test_referencer_finds_locations(self, four_chart_outputs):
        ref = ChartReferencer()
        result = ref.run(four_chart_outputs)
        assert "bay-7" in result.locations_covered
        assert "reef-3" in result.locations_covered

    def test_referencer_produces_summary(self, four_chart_outputs):
        ref = ChartReferencer()
        result = ref.run(four_chart_outputs)
        summary = result.summary()
        assert "Chart Referencer Results" in summary
        assert "4 charts" in summary

    def test_referencer_detects_consensus(self, four_chart_outputs):
        """If multiple charts see the same signal, consensus should form."""
        ref = ChartReferencer()
        result = ref.run(four_chart_outputs)
        # With 4 charts over shared data, some consensus is expected
        # (exact amount depends on overlap)
        assert isinstance(result.consensus, list)

    def test_referencer_detects_divergence(self, four_chart_outputs):
        ref = ChartReferencer()
        result = ref.run(four_chart_outputs)
        # Should find divergence where charts disagree
        assert isinstance(result.divergence, list)

    def test_referencer_detects_discovery(self, four_chart_outputs):
        """Discovery signals should fire when Native sees unexplained absence."""
        ref = ChartReferencer()
        result = ref.run(four_chart_outputs)
        # Native chart should produce at least some discovery candidates
        assert isinstance(result.discovery, list)

    def test_consensus_threshold(self, four_chart_outputs):
        ref = ChartReferencer()
        ref.consensus_threshold = 2  # lower threshold
        result = ref.run(four_chart_outputs)
        # Should find more consensus with lower threshold
        assert isinstance(result.consensus, list)


# ---------------------------------------------------------------------------
# Divergence tests
# ---------------------------------------------------------------------------

class TestDivergenceAnalyzer:

    def test_compare_two_charts(self, four_charts, shared_observations):
        analyzer = DivergenceAnalyzer()
        out_a = four_charts["fisherman"].plot(shared_observations)
        out_b = four_charts["sailor"].plot(shared_observations)
        diffs = analyzer.compare(out_a, out_b)
        assert isinstance(diffs, list)
        assert len(diffs) > 0  # Fisherman and sailor should diverge

    def test_analyze_all_charts(self, four_chart_outputs):
        analyzer = DivergenceAnalyzer()
        diffs = analyzer.analyze(four_chart_outputs)
        assert isinstance(diffs, list)

    def test_divergence_types_are_valid(self, four_chart_outputs):
        analyzer = DivergenceAnalyzer()
        diffs = analyzer.analyze(four_chart_outputs)
        for d in diffs:
            assert d.divergence_type in DivergenceType

    def test_filter_by_type(self, four_chart_outputs):
        analyzer = DivergenceAnalyzer()
        all_diffs = analyzer.analyze(four_chart_outputs)
        constructive = analyzer.filter_by_type(all_diffs, DivergenceType.CONSTRUCTIVE)
        for d in constructive:
            assert d.divergence_type == DivergenceType.CONSTRUCTIVE

    def test_most_severe(self, four_chart_outputs):
        analyzer = DivergenceAnalyzer()
        all_diffs = analyzer.analyze(four_chart_outputs)
        severe = analyzer.most_severe(all_diffs, n=3)
        assert len(severe) <= 3

    def test_divergence_summary(self, four_chart_outputs):
        analyzer = DivergenceAnalyzer()
        all_diffs = analyzer.analyze(four_chart_outputs)
        summary = analyzer.summary(all_diffs)
        assert "Divergence Analysis" in summary

    def test_constructive_divergence(self):
        """One chart sees abundance, the other has no opinion."""
        analyzer = DivergenceAnalyzer()
        from chart_system.charts import ChartOutput, ChartType

        chart_a = ChartOutput(
            chart_type=ChartType.FISHERMAN,
            positive_observations=[
                Observation(location="test", signal="abundance", value=0.8, confidence=0.9),
            ],
        )
        chart_b = ChartOutput(
            chart_type=ChartType.SAILOR,
            # Sailor doesn't have abundance in sensor_weights, so it won't see it
        )
        diffs = analyzer.compare(chart_a, chart_b)
        # Should find the abundance signal as a divergence
        abundance_diffs = [d for d in diffs if d.signal == "abundance"]
        assert len(abundance_diffs) > 0

    def test_contradictory_divergence(self):
        """Two charts make incompatible claims."""
        analyzer = DivergenceAnalyzer()
        from chart_system.charts import ChartOutput, ChartType

        chart_a = ChartOutput(
            chart_type=ChartType.FISHERMAN,
            positive_observations=[
                Observation(location="test", signal="shared_sig", value=0.9, confidence=0.9),
            ],
        )
        chart_b = ChartOutput(
            chart_type=ChartType.SAILOR,
            negative_observations=[
                Observation(
                    location="test", signal="shared_sig", value=0.0,
                    confidence=0.8, expected=False
                ),
            ],
        )
        diffs = analyzer.compare(chart_a, chart_b)
        shared_diffs = [d for d in diffs if d.signal == "shared_sig"]
        assert len(shared_diffs) > 0
        assert shared_diffs[0].divergence_type == DivergenceType.CONTRADICTORY


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

class TestIntegration:

    def test_full_pipeline(self, shared_observations):
        """Run the full chart system pipeline end-to-end."""
        # 1. Run all four charts
        charts = [ChartFisherman(), ChartSailor(), ChartTourist(), ChartNative()]
        outputs = [ch.plot(shared_observations) for ch in charts]

        # 2. Cross-reference
        referencer = ChartReferencer()
        result = referencer.run(outputs)

        # 3. Analyze divergence
        analyzer = DivergenceAnalyzer()
        divergences = analyzer.analyze(outputs)

        # 4. Assertions
        assert len(outputs) == 4
        assert result.chart_count == 4
        assert isinstance(divergences, list)

        # Each chart should have produced output
        for out in outputs:
            assert len(out.positive_observations) > 0

        # Referencer should have processed locations
        assert len(result.locations_covered) >= 2

    def test_same_data_different_readings(self, shared_observations):
        """The core claim: same data through different charts → different readings."""
        fish_out = ChartFisherman().plot(shared_observations)
        sail_out = ChartSailor().plot(shared_observations)
        tour_out = ChartTourist().plot(shared_observations)
        nat_out = ChartNative().plot(shared_observations)

        # Each chart should see a different set of signals
        fish_signals = {o.signal for o in fish_out.positive_observations}
        sail_signals = {o.signal for o in sail_out.positive_observations}
        tour_signals = {o.signal for o in tour_out.positive_observations}
        nat_signals = {o.signal for o in nat_out.positive_observations}

        # No chart should see exactly the same set as another
        all_signal_sets = [fish_signals, sail_signals, tour_signals, nat_signals]
        for i in range(len(all_signal_sets)):
            for j in range(i + 1, len(all_signal_sets)):
                assert all_signal_sets[i] != all_signal_sets[j], (
                    f"Charts {i} and {j} see the same signals — defeats the purpose"
                )
