"""Shared pytest fixtures."""

from __future__ import annotations

from datetime import date

import pytest

from index_analytics_terminal.models.stock import Stock
from index_analytics_terminal.models.index import Index
from index_analytics_terminal.simulators.rebalancing import RebalancingEvent
from index_analytics_terminal.simulators.dividend_shock import DividendEvent


@pytest.fixture()
def sample_stock() -> Stock:
    return Stock(
        ticker="ACME",
        name="Acme Corp",
        price=100.0,
        shares_outstanding=500.0,   # 500 M shares
        adv=2.0,                    # 2 M shares/day
        sector="Technology",
        beta=1.2,
        volatility=0.25,
    )


@pytest.fixture()
def large_cap_stock() -> Stock:
    """A mega-cap stock with very high ADV."""
    return Stock(
        ticker="MEGA",
        name="Mega Corp",
        price=300.0,
        shares_outstanding=5_000.0,
        adv=20.0,
        sector="Technology",
        beta=0.95,
        volatility=0.18,
    )


@pytest.fixture()
def sample_index() -> Index:
    return Index(
        name="Test Index",
        ticker="TIDX",
        total_aum=1_000.0,  # $1 T
    )


@pytest.fixture()
def add_event(sample_stock, sample_index) -> RebalancingEvent:
    return RebalancingEvent(
        action="ADD",
        stock=sample_stock,
        index=sample_index,
        announcement_date=date(2024, 1, 15),
        effective_date=date(2024, 1, 31),
        new_weight=0.01,
        old_weight=0.0,
    )


@pytest.fixture()
def remove_event(sample_stock, sample_index) -> RebalancingEvent:
    return RebalancingEvent(
        action="REMOVE",
        stock=sample_stock,
        index=sample_index,
        announcement_date=date(2024, 1, 15),
        effective_date=date(2024, 1, 31),
        new_weight=0.0,
        old_weight=0.01,
    )


@pytest.fixture()
def sample_dividend_event(sample_stock) -> DividendEvent:
    return DividendEvent(
        stock=sample_stock,
        dividend_per_share=0.50,
        declaration_date=date(2024, 3, 1),
        ex_dividend_date=date(2024, 3, 15),
        frequency=4,
    )
