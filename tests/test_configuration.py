"""Tests for ChartConfiguration with γ allocations."""

import pytest
from chart_system.configuration import (
    ChartConfiguration,
    FISHERMAN_CONFIGURATION,
    SAILOR_CONFIGURATION,
    TOURIST_CONFIGURATION,
    NATIVE_CONFIGURATION,
    get_configuration,
)
from chart_system.charts import ChartType


class TestChartConfiguration:
    def test_fisherman_gamma_total(self):
        cfg = FISHERMAN_CONFIGURATION
        assert cfg.total_gamma_ratio > 0.7
        assert cfg.is_thick()

    def test_sailor_gamma_total(self):
        cfg = SAILOR_CONFIGURATION
        assert cfg.total_gamma_ratio > 0.7
        assert cfg.is_thick()

    def test_tourist_has_eta(self):
        cfg = TOURIST_CONFIGURATION
        assert cfg.eta_ratio > 0.0
        # Tourist doesn't allocate everything
        assert cfg.total_gamma_ratio < 1.0

    def test_native_allocates_complement(self):
        cfg = NATIVE_CONFIGURATION
        # Native focuses on absence signals
        assert cfg.gamma_allocation["absence:*"] > 0

    def test_eta_property(self):
        cfg = ChartConfiguration(
            chart_type=ChartType.FISHERMAN,
            capacity=100,
            gamma_allocation={"a": 0.3},
        )
        assert cfg.total_gamma == pytest.approx(30)
        assert cfg.eta == pytest.approx(70)

    def test_allocation_for_exact(self):
        cfg = ChartConfiguration(
            chart_type=ChartType.FISHERMAN,
            gamma_allocation={"abundance": 0.5},
        )
        assert cfg.allocation_for("abundance") == 0.5

    def test_allocation_for_wildcard(self):
        cfg = ChartConfiguration(
            chart_type=ChartType.FISHERMAN,
            gamma_allocation={"ecological:*": 0.3},
        )
        assert cfg.allocation_for("ecological:temperature") == 0.3
        assert cfg.allocation_for("ecological") == 0.3

    def test_allocation_for_missing(self):
        cfg = ChartConfiguration(
            chart_type=ChartType.FISHERMAN,
            gamma_allocation={"a": 0.1},
        )
        assert cfg.allocation_for("nonexistent") == 0.0

    def test_get_configuration_fisherman(self):
        cfg = get_configuration(ChartType.FISHERMAN)
        assert cfg.chart_type == ChartType.FISHERMAN

    def test_get_configuration_all_types(self):
        for ct in ChartType:
            cfg = get_configuration(ct)
            assert cfg.chart_type == ct

    def test_to_dict(self):
        cfg = ChartConfiguration(
            chart_type=ChartType.NATIVE,
            capacity=50,
            gamma_allocation={"absence:*": 0.5},
            description="test",
        )
        d = cfg.to_dict()
        assert d["chart_type"] == "native"
        assert d["capacity"] == 50
        assert d["description"] == "test"

    def test_thin_chart(self):
        cfg = ChartConfiguration(
            chart_type=ChartType.TOURIST,
            gamma_allocation={"a": 0.1},
        )
        assert cfg.is_thin()

    def test_all_configurations_sum_leq_one(self):
        """No chart should over-allocate beyond its capacity."""
        for cfg in [FISHERMAN_CONFIGURATION, SAILOR_CONFIGURATION,
                    TOURIST_CONFIGURATION, NATIVE_CONFIGURATION]:
            assert cfg.total_gamma_ratio <= 1.0, f"{cfg.chart_type} over-allocated"
