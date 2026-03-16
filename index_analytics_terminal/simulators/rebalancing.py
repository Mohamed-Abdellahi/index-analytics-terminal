"""Index Rebalancing Simulator.

Simulates the price impact and arbitrage opportunities that arise when a stock
is added to or removed from a major equity index.

Academic foundations
--------------------
* Beneish & Whaley (1996) — *An Anatomy of the "S&P Game": The Effects of
  Changing the Rules.*
* Harris & Gurel (1986) — *Price and Volume Effects Associated with Changes in
  the S&P 500 List.*
* Petajisto (2011) — *The Index Premium and Its Hidden Cost for Index Funds.*
* Almgren & Chriss (2001) — *Optimal Execution of Portfolio Transactions.*

Methodology
-----------
Price impact uses a square-root market-impact model:

    impact (%) = k × sqrt(demand / supply)

where
    demand = index_tracking_AUM × |Δweight|
    supply = ADV × trading_days_in_window
    k      = empirical calibration constant (~0.10)

The arbitrage window runs from the announcement date to the effective date.
Arbitrageurs can capture a fraction of the total impact by buying
(for additions) or shorting (for deletions) immediately after announcement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Tuple

from ..models.stock import Stock
from ..models.index import Index


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RebalancingEvent:
    """Describes a single index rebalancing event.

    Attributes:
        action: ``"ADD"`` or ``"REMOVE"``.
        stock: The stock being added or removed.
        index: The index being rebalanced.
        announcement_date: Date the change is publicly announced.
        effective_date: Date the change takes effect (index funds must trade).
        new_weight: Target weight after the change (0 for a removal).
        old_weight: Weight before the change (0 for a brand-new addition).
    """

    action: str
    stock: Stock
    index: Index
    announcement_date: date
    effective_date: date
    new_weight: float
    old_weight: float = 0.0

    def __post_init__(self) -> None:
        if self.action not in ("ADD", "REMOVE"):
            raise ValueError(f"action must be 'ADD' or 'REMOVE', got '{self.action}'")
        if self.new_weight < 0 or self.new_weight > 1:
            raise ValueError(f"new_weight must be in [0, 1], got {self.new_weight}")
        if self.old_weight < 0 or self.old_weight > 1:
            raise ValueError(f"old_weight must be in [0, 1], got {self.old_weight}")
        if self.effective_date < self.announcement_date:
            raise ValueError("effective_date must be >= announcement_date")


@dataclass
class RebalancingImpact:
    """Full result set from a rebalancing simulation.

    All monetary amounts are in **USD** unless the field name includes a unit
    suffix (e.g. ``_millions``).
    """

    event: RebalancingEvent

    # Demand / supply
    shares_traded_millions: float
    dollars_traded_millions: float
    days_to_effective: int
    demand_to_adv_ratio: float

    # Price-impact estimates
    price_impact_pct: float
    price_impact_dollars: float
    estimated_post_impact_price: float

    # Arbitrage
    arbitrage_pnl_per_share: float
    arbitrage_pnl_total_millions: float
    annualized_return_pct: float

    # Risk
    tracking_error_contribution_bps: float
    announcement_return_pct: float


@dataclass
class ArbitrageScenario:
    """A concrete arbitrage trade scenario around a rebalancing event."""

    entry_price: float
    exit_price: float
    entry_date: date
    exit_date: date
    shares_traded: float
    pnl_dollars: float
    pnl_pct: float
    annualized_return_pct: float
    sharpe_ratio: float


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------


class RebalancingSimulator:
    """Simulates index rebalancing price effects and arbitrage opportunities.

    Parameters
    ----------
    trading_days_per_year:
        Convention for converting calendar days to trading days (default 252).
    impact_calibration:
        Calibration constant *k* for the square-root impact model.
        The default (``0.10``) is tuned to match empirical S&P 500 studies.
    arb_capture_ratio:
        Fraction of the theoretical impact that arbitrageurs can realistically
        capture net of risk (default ``0.65``).
    """

    # Empirical average price reactions on key dates (additions / deletions)
    _ANNOUNCEMENT_RETURN_ADD = 3.5    # % on announcement day
    _EFFECTIVE_RETURN_ADD = 2.0       # % on effective date
    _ANNOUNCEMENT_RETURN_DEL = -6.0   # % on deletion announcement

    def __init__(
        self,
        trading_days_per_year: int = 252,
        impact_calibration: float = 0.10,
        arb_capture_ratio: float = 0.65,
    ) -> None:
        self.trading_days_per_year = trading_days_per_year
        self.impact_calibration = impact_calibration
        self.arb_capture_ratio = arb_capture_ratio

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def simulate(self, event: RebalancingEvent) -> RebalancingImpact:
        """Run the full rebalancing simulation for *event*.

        Parameters
        ----------
        event:
            The :class:`RebalancingEvent` to simulate.

        Returns
        -------
        :class:`RebalancingImpact`
            All calculated metrics.
        """
        stock = event.stock
        index = event.index

        # ------------------------------------------------------------------
        # 1. Time window
        # ------------------------------------------------------------------
        calendar_days = max(1, (event.effective_date - event.announcement_date).days)
        trading_days = max(1, round(calendar_days * self.trading_days_per_year / 365))

        # ------------------------------------------------------------------
        # 2. Demand / supply
        # ------------------------------------------------------------------
        weight_change = abs(event.new_weight - event.old_weight)
        dollars_traded = index.total_aum_dollars * weight_change
        shares_traded = dollars_traded / stock.price if stock.price > 0 else 0.0

        demand_to_adv = (
            dollars_traded / (stock.adv_dollars * trading_days)
            if stock.adv_dollars > 0
            else 0.0
        )

        # ------------------------------------------------------------------
        # 3. Price impact
        # ------------------------------------------------------------------
        price_impact_pct = self._price_impact(
            dollars_traded, stock.adv_dollars, trading_days
        )
        price_impact_dollars = stock.price * price_impact_pct / 100

        if event.action == "ADD":
            estimated_post_price = stock.price * (1 + price_impact_pct / 100)
        else:
            estimated_post_price = stock.price * (1 - price_impact_pct / 100)

        # ------------------------------------------------------------------
        # 4. Arbitrage P&L
        # ------------------------------------------------------------------
        arb_pnl_per_share = (
            stock.price * (price_impact_pct / 100) * self.arb_capture_ratio
        )
        # Arb position assumed at 10 % of total index-fund demand
        arb_position_shares = shares_traded * 0.10
        arb_total_pnl_millions = arb_pnl_per_share * arb_position_shares / 1_000_000

        # Annualised return
        if trading_days > 0 and stock.price > 0:
            raw_return_pct = (arb_pnl_per_share / stock.price) * 100
            annualized_return = raw_return_pct * (self.trading_days_per_year / trading_days)
        else:
            annualized_return = 0.0

        # ------------------------------------------------------------------
        # 5. Risk metrics
        # ------------------------------------------------------------------
        te_bps = self._tracking_error_bps(weight_change, stock.volatility, trading_days)

        announcement_return = (
            self._ANNOUNCEMENT_RETURN_ADD
            if event.action == "ADD"
            else self._ANNOUNCEMENT_RETURN_DEL
        )

        return RebalancingImpact(
            event=event,
            shares_traded_millions=shares_traded / 1_000_000,
            dollars_traded_millions=dollars_traded / 1_000_000,
            days_to_effective=trading_days,
            demand_to_adv_ratio=demand_to_adv,
            price_impact_pct=price_impact_pct,
            price_impact_dollars=price_impact_dollars,
            estimated_post_impact_price=estimated_post_price,
            arbitrage_pnl_per_share=arb_pnl_per_share,
            arbitrage_pnl_total_millions=arb_total_pnl_millions,
            annualized_return_pct=annualized_return,
            tracking_error_contribution_bps=te_bps,
            announcement_return_pct=announcement_return,
        )

    def simulate_arbitrage_scenario(
        self,
        event: RebalancingEvent,
        impact: RebalancingImpact,
        position_size_dollars: float = 1_000_000,
        transaction_cost_bps: float = 5.0,
    ) -> ArbitrageScenario:
        """Simulate a concrete arbitrage trade for *event*.

        The strategy buys (for additions) or shorts (for deletions) at the
        close of the announcement day, then unwinds on the effective date.

        Parameters
        ----------
        event:
            The rebalancing event.
        impact:
            Pre-calculated :class:`RebalancingImpact` for the event.
        position_size_dollars:
            Notional size of the arbitrage position in USD (default $1 M).
        transaction_cost_bps:
            One-way transaction cost in basis points (default 5 bps).

        Returns
        -------
        :class:`ArbitrageScenario`
        """
        stock = event.stock

        # Entry at announcement-day close (price has already moved)
        entry_price = stock.price * (1 + impact.announcement_return_pct / 100)

        # Exit at effective-date (post full-impact) price
        exit_price = impact.estimated_post_impact_price

        tx_cost_per_share = (entry_price + exit_price) * transaction_cost_bps / 10_000
        shares = position_size_dollars / entry_price if entry_price > 0 else 0.0

        if event.action == "ADD":
            gross_pnl = (exit_price - entry_price) * shares
        else:
            gross_pnl = (entry_price - exit_price) * shares

        net_pnl = gross_pnl - tx_cost_per_share * shares
        pnl_pct = (net_pnl / position_size_dollars * 100) if position_size_dollars > 0 else 0.0

        ann_return = (
            pnl_pct * (self.trading_days_per_year / impact.days_to_effective)
            if impact.days_to_effective > 0
            else 0.0
        )

        daily_vol = stock.volatility / math.sqrt(self.trading_days_per_year)
        period_vol_pct = daily_vol * math.sqrt(impact.days_to_effective) * 100
        sharpe = pnl_pct / period_vol_pct if period_vol_pct > 0 else 0.0

        return ArbitrageScenario(
            entry_price=entry_price,
            exit_price=exit_price,
            entry_date=event.announcement_date,
            exit_date=event.effective_date,
            shares_traded=shares,
            pnl_dollars=net_pnl,
            pnl_pct=pnl_pct,
            annualized_return_pct=ann_return,
            sharpe_ratio=sharpe,
        )

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _price_impact(
        self,
        demand_dollars: float,
        adv_dollars: float,
        trading_days: int,
    ) -> float:
        """Square-root market-impact model, returns impact in percent."""
        if adv_dollars <= 0 or trading_days <= 0:
            return 0.0
        supply = adv_dollars * trading_days
        ratio = demand_dollars / supply
        impact_pct = self.impact_calibration * math.sqrt(ratio) * 100
        return min(impact_pct, 30.0)  # cap at 30 %

    def _tracking_error_bps(
        self,
        weight_change: float,
        volatility: float,
        trading_days: int,
    ) -> float:
        """Tracking-error contribution in basis points for imperfect execution."""
        daily_vol = volatility / math.sqrt(self.trading_days_per_year)
        te = weight_change * daily_vol * math.sqrt(trading_days) * 10_000
        return abs(te)
