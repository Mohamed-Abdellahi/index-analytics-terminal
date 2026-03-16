"""Tests for the Dividend Shock Simulator."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from index_analytics_terminal.models.stock import Stock
from index_analytics_terminal.simulators.dividend_shock import (
    CaptureResult,
    DividendEvent,
    DividendShockResult,
    DividendShockSimulator,
)


# ---------------------------------------------------------------------------
# DividendEvent model tests
# ---------------------------------------------------------------------------


class TestDividendEvent:
    def test_defaults_record_and_payment_dates(self, sample_dividend_event):
        event = sample_dividend_event
        assert event.record_date == event.ex_dividend_date + timedelta(days=1)
        assert event.payment_date == event.ex_dividend_date + timedelta(days=14)

    def test_negative_dividend_raises(self, sample_stock):
        with pytest.raises(ValueError, match="non-negative"):
            DividendEvent(
                stock=sample_stock,
                dividend_per_share=-0.50,
                declaration_date=date(2024, 3, 1),
                ex_dividend_date=date(2024, 3, 15),
            )

    def test_ex_div_before_declaration_raises(self, sample_stock):
        with pytest.raises(ValueError, match="ex_dividend_date must be"):
            DividendEvent(
                stock=sample_stock,
                dividend_per_share=0.50,
                declaration_date=date(2024, 3, 15),
                ex_dividend_date=date(2024, 3, 1),
            )

    def test_annual_dividend_quarterly(self, sample_dividend_event):
        # 0.50 × 4 = 2.00
        assert sample_dividend_event.annual_dividend == pytest.approx(2.00)

    def test_dividend_yield(self, sample_dividend_event):
        # annual_div = 2.00, price = 100 → yield = 2 %
        assert sample_dividend_event.dividend_yield == pytest.approx(0.02)

    def test_zero_price_yield(self, sample_stock):
        stock_zero = Stock(
            ticker="ZRO",
            name="Zero Price",
            price=0.0,
            shares_outstanding=100.0,
            adv=1.0,
        )
        event = DividendEvent(
            stock=stock_zero,
            dividend_per_share=0.50,
            declaration_date=date(2024, 3, 1),
            ex_dividend_date=date(2024, 3, 15),
        )
        assert event.dividend_yield == 0.0


# ---------------------------------------------------------------------------
# DividendShockSimulator tests
# ---------------------------------------------------------------------------


class TestDividendShockSimulator:
    def test_simulate_returns_result(self, sample_dividend_event):
        sim = DividendShockSimulator()
        result = sim.simulate(sample_dividend_event)
        assert isinstance(result, DividendShockResult)

    def test_ex_div_price_lower_than_current(self, sample_dividend_event):
        sim = DividendShockSimulator()
        result = sim.simulate(sample_dividend_event)
        assert result.theoretical_ex_div_price < sample_dividend_event.stock.price

    def test_price_drop_equals_dividend_at_zero_tax(self, sample_stock):
        """With equal div and CG tax rates, price drop equals dividend."""
        event = DividendEvent(
            stock=sample_stock,
            dividend_per_share=1.00,
            declaration_date=date(2024, 3, 1),
            ex_dividend_date=date(2024, 3, 15),
        )
        sim = DividendShockSimulator(dividend_tax_rate=0.20, capital_gains_tax_rate=0.20)
        result = sim.simulate(event)
        # (1-0.20)/(1-0.20) = 1 → drop = 1.00
        assert result.price_drop_dollars == pytest.approx(1.00, rel=1e-5)

    def test_price_drop_larger_with_higher_cg_tax(self, sample_dividend_event):
        """Higher CG tax → larger ex-div price drop (Elton-Gruber: ΔP = D×(1-τ_d)/(1-τ_cg))."""
        sim_low_cg = DividendShockSimulator(dividend_tax_rate=0.15, capital_gains_tax_rate=0.10)
        sim_high_cg = DividendShockSimulator(dividend_tax_rate=0.15, capital_gains_tax_rate=0.40)
        drop_low = sim_low_cg.simulate(sample_dividend_event).price_drop_dollars
        drop_high = sim_high_cg.simulate(sample_dividend_event).price_drop_dollars
        assert drop_high > drop_low

    def test_after_tax_yield_lower_than_gross(self, sample_dividend_event):
        sim = DividendShockSimulator(dividend_tax_rate=0.15)
        result = sim.simulate(sample_dividend_event)
        assert result.after_tax_yield_pct < result.dividend_yield_pct

    def test_days_to_ex_div(self, sample_dividend_event):
        reference = date(2024, 3, 1)  # same as declaration
        sim = DividendShockSimulator(reference_date=reference)
        result = sim.simulate(sample_dividend_event)
        expected = (sample_dividend_event.ex_dividend_date - reference).days
        assert result.days_to_ex_div == expected

    def test_ddm_fair_value_positive(self, sample_dividend_event):
        sim = DividendShockSimulator()
        result = sim.simulate(sample_dividend_event)
        assert result.ddm_fair_value > 0

    def test_overvalued_stock(self, sample_stock):
        """If market price >>> DDM value, signal should be 'overvalued'."""
        # With $0.01 dividend and price=$100, DDM value will be tiny
        pricey = Stock(
            ticker="OVR",
            name="Overvalued Inc",
            price=100.0,
            shares_outstanding=200.0,
            adv=1.0,
            beta=1.0,
        )
        event = DividendEvent(
            stock=pricey,
            dividend_per_share=0.01,   # tiny dividend → DDM value ≈ $0.44
            declaration_date=date(2024, 3, 1),
            ex_dividend_date=date(2024, 3, 15),
            frequency=4,
        )
        sim = DividendShockSimulator()
        result = sim.simulate(event)
        assert result.ddm_implied_return == "overvalued"

    def test_undervalued_stock(self, sample_stock):
        """If market price <<< DDM value, signal should be 'undervalued'."""
        cheap = Stock(
            ticker="UND",
            name="Undervalued Inc",
            price=10.0,
            shares_outstanding=200.0,
            adv=1.0,
            beta=1.0,
        )
        event = DividendEvent(
            stock=cheap,
            dividend_per_share=2.00,   # very high dividend → high DDM value
            declaration_date=date(2024, 3, 1),
            ex_dividend_date=date(2024, 3, 15),
            frequency=4,
        )
        sim = DividendShockSimulator()
        result = sim.simulate(event)
        assert result.ddm_implied_return == "undervalued"

    def test_invalid_tax_rate_raises(self):
        with pytest.raises(ValueError, match="dividend_tax_rate"):
            DividendShockSimulator(dividend_tax_rate=1.5)

    def test_invalid_cg_tax_rate_raises(self):
        with pytest.raises(ValueError, match="capital_gains_tax_rate"):
            DividendShockSimulator(capital_gains_tax_rate=-0.1)

    # ── Capture strategy tests ─────────────────────────────────────────── #

    def test_capture_result_type(self, sample_dividend_event):
        sim = DividendShockSimulator()
        capture = sim.simulate_capture(sample_dividend_event)
        assert isinstance(capture, CaptureResult)

    def test_capture_buy_sell_prices(self, sample_dividend_event):
        sim = DividendShockSimulator(dividend_tax_rate=0.0)
        capture = sim.simulate_capture(sample_dividend_event, transaction_cost_bps=0)
        # With no tax, sell price = buy_price - dividend
        assert capture.sell_price == pytest.approx(
            capture.buy_price - sample_dividend_event.dividend_per_share, rel=1e-5
        )

    def test_capture_zero_cost_breakeven_no_tax(self, sample_dividend_event):
        """Zero transaction costs and zero tax → breakeven (dividend exactly offsets drop)."""
        sim = DividendShockSimulator(dividend_tax_rate=0.0, capital_gains_tax_rate=0.0)
        capture = sim.simulate_capture(sample_dividend_event, transaction_cost_bps=0)
        assert capture.net_pnl == pytest.approx(0.0, abs=1e-10)

    def test_capture_high_cost_may_be_unprofitable(self, sample_dividend_event):
        """Extremely high transaction cost should make capture unprofitable."""
        sim = DividendShockSimulator()
        capture = sim.simulate_capture(sample_dividend_event, transaction_cost_bps=5000)
        assert not capture.is_profitable

    def test_capture_break_even_positive(self, sample_dividend_event):
        sim = DividendShockSimulator()
        capture = sim.simulate_capture(sample_dividend_event)
        assert capture.break_even_price_drop_pct >= 0

    # ── DRIP tests ─────────────────────────────────────────────────────── #

    def test_drip_returns_correct_number_of_years(self, sample_dividend_event):
        sim = DividendShockSimulator()
        rows = sim.dividend_reinvestment_plan(sample_dividend_event, years=5)
        assert len(rows) == 5

    def test_drip_total_value_grows(self, sample_dividend_event):
        sim = DividendShockSimulator()
        rows = sim.dividend_reinvestment_plan(sample_dividend_event, years=10)
        assert rows[-1]["total_value"] > rows[0]["total_value"]

    def test_drip_shares_increase(self, sample_dividend_event):
        sim = DividendShockSimulator()
        rows = sim.dividend_reinvestment_plan(sample_dividend_event, years=10)
        assert rows[-1]["shares"] > rows[0]["shares"]

    def test_drip_cumulative_dividends_monotonic(self, sample_dividend_event):
        sim = DividendShockSimulator()
        rows = sim.dividend_reinvestment_plan(sample_dividend_event, years=5)
        cumulative = [r["cumulative_dividends"] for r in rows]
        assert all(
            cumulative[i] <= cumulative[i + 1] for i in range(len(cumulative) - 1)
        )

    def test_drip_year_sequence(self, sample_dividend_event):
        sim = DividendShockSimulator()
        rows = sim.dividend_reinvestment_plan(sample_dividend_event, years=5)
        assert [r["year"] for r in rows] == [1, 2, 3, 4, 5]
