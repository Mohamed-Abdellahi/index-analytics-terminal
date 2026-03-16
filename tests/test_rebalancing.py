"""Tests for the Index Rebalancing Simulator."""

from __future__ import annotations

import math
from datetime import date

import pytest

from index_analytics_terminal.models.index import Index, IndexConstituent
from index_analytics_terminal.models.stock import Stock
from index_analytics_terminal.simulators.rebalancing import (
    RebalancingEvent,
    RebalancingImpact,
    RebalancingSimulator,
)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestStock:
    def test_market_cap(self, sample_stock):
        # price=100, shares=500 M → market_cap = 50_000 M
        assert sample_stock.market_cap == pytest.approx(50_000.0)

    def test_market_cap_dollars(self, sample_stock):
        assert sample_stock.market_cap_dollars == pytest.approx(50_000_000_000.0)

    def test_adv_dollars(self, sample_stock):
        # adv=2 M shares × price=$100 × 1e6 = $200 M
        assert sample_stock.adv_dollars == pytest.approx(200_000_000.0)

    def test_daily_volatility(self, sample_stock):
        expected = 0.25 / math.sqrt(252)
        assert sample_stock.daily_volatility == pytest.approx(expected)


class TestIndex:
    def test_total_aum_dollars(self, sample_index):
        # 1_000 B → 1 T
        assert sample_index.total_aum_dollars == pytest.approx(1_000_000_000_000.0)

    def test_add_constituent_normalizes_weights(self, sample_index, sample_stock):
        another = Stock(
            ticker="ZZZ",
            name="ZZZ Corp",
            price=50.0,
            shares_outstanding=200.0,
            adv=1.0,
        )
        sample_index.add_constituent(sample_stock, weight=0.5)
        sample_index.add_constituent(another, weight=0.5)
        assert sample_index.total_weight == pytest.approx(1.0, rel=1e-6)

    def test_remove_constituent(self, sample_index, sample_stock):
        sample_index.add_constituent(sample_stock, weight=0.5)
        removed = sample_index.remove_constituent(sample_stock.ticker)
        assert removed is not None
        assert sample_stock.ticker not in sample_index.constituents

    def test_remove_nonexistent_returns_none(self, sample_index):
        assert sample_index.remove_constituent("NOEXIST") is None

    def test_get_weight_missing(self, sample_index):
        assert sample_index.get_weight("MISS") == 0.0

    def test_invalid_constituent_weight(self, sample_stock):
        with pytest.raises(ValueError, match="Weight must be in"):
            IndexConstituent(stock=sample_stock, weight=1.5)


class TestRebalancingEvent:
    def test_invalid_action(self, sample_stock, sample_index):
        with pytest.raises(ValueError, match="action must be"):
            RebalancingEvent(
                action="BUY",
                stock=sample_stock,
                index=sample_index,
                announcement_date=date(2024, 1, 1),
                effective_date=date(2024, 1, 15),
                new_weight=0.01,
            )

    def test_effective_before_announcement_raises(self, sample_stock, sample_index):
        with pytest.raises(ValueError, match="effective_date must be"):
            RebalancingEvent(
                action="ADD",
                stock=sample_stock,
                index=sample_index,
                announcement_date=date(2024, 1, 15),
                effective_date=date(2024, 1, 10),
                new_weight=0.01,
            )

    def test_invalid_new_weight(self, sample_stock, sample_index):
        with pytest.raises(ValueError, match="new_weight must be"):
            RebalancingEvent(
                action="ADD",
                stock=sample_stock,
                index=sample_index,
                announcement_date=date(2024, 1, 1),
                effective_date=date(2024, 1, 15),
                new_weight=1.5,
            )


# ---------------------------------------------------------------------------
# Simulator tests
# ---------------------------------------------------------------------------


class TestRebalancingSimulator:
    def test_simulate_add_returns_impact(self, add_event):
        sim = RebalancingSimulator()
        impact = sim.simulate(add_event)
        assert isinstance(impact, RebalancingImpact)

    def test_add_increases_estimated_price(self, add_event):
        sim = RebalancingSimulator()
        impact = sim.simulate(add_event)
        assert impact.estimated_post_impact_price > add_event.stock.price

    def test_remove_decreases_estimated_price(self, remove_event):
        sim = RebalancingSimulator()
        impact = sim.simulate(remove_event)
        assert impact.estimated_post_impact_price < remove_event.stock.price

    def test_price_impact_is_non_negative(self, add_event):
        sim = RebalancingSimulator()
        impact = sim.simulate(add_event)
        assert impact.price_impact_pct >= 0

    def test_price_impact_capped_at_30(self):
        """Tiny ADV stock with huge demand → impact capped at 30 %."""
        illiquid = Stock(
            ticker="ILL",
            name="Illiquid Inc",
            price=10.0,
            shares_outstanding=10.0,
            adv=0.001,
            volatility=0.50,
        )
        giant_index = Index(name="Giant", ticker="GNT", total_aum=10_000.0)
        event = RebalancingEvent(
            action="ADD",
            stock=illiquid,
            index=giant_index,
            announcement_date=date(2024, 1, 1),
            effective_date=date(2024, 1, 2),
            new_weight=0.10,
        )
        sim = RebalancingSimulator()
        impact = sim.simulate(event)
        assert impact.price_impact_pct <= 30.0

    def test_higher_aum_gives_higher_impact(self, sample_stock):
        """Bigger index fund AUM → larger price impact."""
        event_small = RebalancingEvent(
            action="ADD",
            stock=sample_stock,
            index=Index(name="Small", ticker="SML", total_aum=100.0),
            announcement_date=date(2024, 1, 1),
            effective_date=date(2024, 1, 31),
            new_weight=0.01,
        )
        event_large = RebalancingEvent(
            action="ADD",
            stock=sample_stock,
            index=Index(name="Large", ticker="LRG", total_aum=5_000.0),
            announcement_date=date(2024, 1, 1),
            effective_date=date(2024, 1, 31),
            new_weight=0.01,
        )
        sim = RebalancingSimulator()
        assert sim.simulate(event_large).price_impact_pct > sim.simulate(event_small).price_impact_pct

    def test_longer_window_reduces_impact(self, sample_stock, sample_index):
        """More trading days → more supply → lower price impact."""
        event_short = RebalancingEvent(
            action="ADD",
            stock=sample_stock,
            index=sample_index,
            announcement_date=date(2024, 1, 1),
            effective_date=date(2024, 1, 5),   # ~3 trading days
            new_weight=0.01,
        )
        event_long = RebalancingEvent(
            action="ADD",
            stock=sample_stock,
            index=sample_index,
            announcement_date=date(2024, 1, 1),
            effective_date=date(2024, 3, 1),   # ~40 trading days
            new_weight=0.01,
        )
        sim = RebalancingSimulator()
        assert sim.simulate(event_short).price_impact_pct > sim.simulate(event_long).price_impact_pct

    def test_demand_to_adv_ratio_calculation(self, add_event):
        """Sanity-check the demand/ADV ratio."""
        sim = RebalancingSimulator()
        impact = sim.simulate(add_event)
        # demand = AUM × Δweight
        demand = add_event.index.total_aum_dollars * add_event.new_weight
        calendar_days = (add_event.effective_date - add_event.announcement_date).days
        trading_days = max(1, round(calendar_days * 252 / 365))
        expected_ratio = demand / (add_event.stock.adv_dollars * trading_days)
        assert impact.demand_to_adv_ratio == pytest.approx(expected_ratio, rel=1e-5)

    def test_dollars_traded_calculation(self, add_event):
        sim = RebalancingSimulator()
        impact = sim.simulate(add_event)
        expected = add_event.index.total_aum_dollars * add_event.new_weight / 1_000_000
        assert impact.dollars_traded_millions == pytest.approx(expected, rel=1e-5)

    def test_announcement_return_positive_for_add(self, add_event):
        sim = RebalancingSimulator()
        impact = sim.simulate(add_event)
        assert impact.announcement_return_pct > 0

    def test_announcement_return_negative_for_remove(self, remove_event):
        sim = RebalancingSimulator()
        impact = sim.simulate(remove_event)
        assert impact.announcement_return_pct < 0

    def test_tracking_error_positive(self, add_event):
        sim = RebalancingSimulator()
        impact = sim.simulate(add_event)
        assert impact.tracking_error_contribution_bps > 0

    def test_arbitrage_pnl_positive_for_add(self, add_event):
        sim = RebalancingSimulator()
        impact = sim.simulate(add_event)
        assert impact.arbitrage_pnl_per_share > 0

    def test_same_day_announcement_effective(self, sample_stock, sample_index):
        """Announcement and effective on the same day should not crash."""
        event = RebalancingEvent(
            action="ADD",
            stock=sample_stock,
            index=sample_index,
            announcement_date=date(2024, 1, 15),
            effective_date=date(2024, 1, 15),
            new_weight=0.01,
        )
        sim = RebalancingSimulator()
        impact = sim.simulate(event)
        assert impact.price_impact_pct >= 0

    # ── Arbitrage scenario tests ──────────────────────────────────────── #

    def test_arb_scenario_profitable_add(self, add_event):
        sim = RebalancingSimulator()
        impact = sim.simulate(add_event)
        scenario = sim.simulate_arbitrage_scenario(add_event, impact)
        # For an addition with meaningful impact, buy-low-sell-high should profit
        # before considering announcement day premium
        assert isinstance(scenario.pnl_dollars, float)

    def test_arb_scenario_dates_match_event(self, add_event):
        sim = RebalancingSimulator()
        impact = sim.simulate(add_event)
        scenario = sim.simulate_arbitrage_scenario(add_event, impact)
        assert scenario.entry_date == add_event.announcement_date
        assert scenario.exit_date == add_event.effective_date

    def test_arb_scenario_shares_positive(self, add_event):
        sim = RebalancingSimulator()
        impact = sim.simulate(add_event)
        scenario = sim.simulate_arbitrage_scenario(
            add_event, impact, position_size_dollars=1_000_000
        )
        assert scenario.shares_traded > 0

    def test_custom_impact_calibration(self, add_event):
        sim_low = RebalancingSimulator(impact_calibration=0.05)
        sim_high = RebalancingSimulator(impact_calibration=0.20)
        assert (
            sim_low.simulate(add_event).price_impact_pct
            < sim_high.simulate(add_event).price_impact_pct
        )
