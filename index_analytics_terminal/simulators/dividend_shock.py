"""Dividend Shock Simulator.

Simulates the ex-dividend price drop and analyses dividend-capture strategies.

Key dates
---------
* **Declaration date** — company announces the dividend.
* **Ex-dividend date** — buyer of the stock on or after this date is NOT entitled
  to the declared dividend.  The stock price theoretically drops by the
  after-tax dividend on this date.
* **Record date** — investor must be a shareholder of record to receive payment
  (usually T+1 after ex-div).
* **Payment date** — dividend cash is paid to eligible shareholders.

Price-drop model (Elton & Gruber 1970)
---------------------------------------
Under the Elton-Gruber tax-clientele model:

    ΔP = D × (1 − τ_d) / (1 − τ_cg)

where τ_d and τ_cg are the marginal dividend and capital-gains tax rates.
For a zero-tax investor (e.g. pension fund) ΔP ≈ D (full drop).

Dividend Capture
----------------
The classic capture strategy:
    1. Buy the stock just before the ex-dividend date.
    2. Collect the dividend.
    3. Sell on the ex-dividend date (accepting the price drop).
    Net P&L = dividend − price drop − transaction costs

Dividend Discount Model (DDM)
-------------------------------
Gordon Growth Model (constant-growth variant):

    Fair Value = D₁ / (r − g)

where D₁ = next period dividend, r = required return, g = perpetual growth rate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from ..models.stock import Stock


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DividendEvent:
    """Describes a single dividend event.

    Attributes:
        stock: The issuing :class:`~index_analytics_terminal.models.stock.Stock`.
        dividend_per_share: Gross dividend per share in USD.
        declaration_date: Date the dividend is announced.
        ex_dividend_date: First trading day *without* dividend entitlement.
        record_date: Shareholder-of-record date (defaults to ex_dividend_date + 1 day).
        payment_date: Date dividend cash is paid (defaults to ex_dividend_date + 14 days).
        frequency: Number of dividend payments per year (e.g. ``4`` = quarterly).
    """

    stock: Stock
    dividend_per_share: float
    declaration_date: date
    ex_dividend_date: date
    record_date: Optional[date] = None
    payment_date: Optional[date] = None
    frequency: int = 4  # quarterly by default

    def __post_init__(self) -> None:
        if self.dividend_per_share < 0:
            raise ValueError("dividend_per_share must be non-negative")
        if self.ex_dividend_date < self.declaration_date:
            raise ValueError("ex_dividend_date must be >= declaration_date")
        if self.record_date is None:
            self.record_date = self.ex_dividend_date + timedelta(days=1)
        if self.payment_date is None:
            self.payment_date = self.ex_dividend_date + timedelta(days=14)

    @property
    def annual_dividend(self) -> float:
        """Annualised dividend per share."""
        return self.dividend_per_share * self.frequency

    @property
    def dividend_yield(self) -> float:
        """Forward dividend yield (annualised) at current stock price."""
        if self.stock.price <= 0:
            return 0.0
        return self.annual_dividend / self.stock.price


@dataclass
class DividendShockResult:
    """Comprehensive result of a dividend-shock simulation."""

    event: DividendEvent

    # Ex-div price-drop analysis
    theoretical_ex_div_price: float
    price_drop_dollars: float
    price_drop_pct: float

    # Dividend yield
    dividend_yield_pct: float
    annual_dividend: float

    # Tax-adjusted metrics
    after_tax_dividend: float
    after_tax_yield_pct: float

    # Total-return breakdown
    capital_return_pct: float   # expected capital gain/loss over next year
    income_return_pct: float    # dividend yield component
    total_return_pct: float     # capital + income

    # DDM fair value
    ddm_fair_value: float
    ddm_implied_return: str     # "overvalued" / "undervalued" / "fairly valued"

    # Days until ex-dividend
    days_to_ex_div: int


@dataclass
class CaptureResult:
    """Result of a dividend-capture strategy simulation."""

    event: DividendEvent

    # Trade details
    buy_price: float
    sell_price: float
    dividend_received: float
    transaction_cost_dollars: float

    # P&L
    gross_pnl: float
    net_pnl: float
    pnl_pct: float
    annualized_return_pct: float

    # Break-even
    break_even_price_drop_pct: float
    is_profitable: bool


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------


class DividendShockSimulator:
    """Simulates ex-dividend price drops and dividend-capture strategies.

    Parameters
    ----------
    dividend_tax_rate:
        Marginal tax rate on dividend income (default ``0.15`` = 15 %).
    capital_gains_tax_rate:
        Marginal tax rate on short-term capital gains (default ``0.20`` = 20 %).
    required_return:
        Discount rate used in the DDM fair-value calculation (default ``0.08``).
    reference_date:
        The "today" date for calculating days-to-ex-div; defaults to
        ``date.today()`` if not supplied.
    """

    def __init__(
        self,
        dividend_tax_rate: float = 0.15,
        capital_gains_tax_rate: float = 0.20,
        required_return: float = 0.08,
        reference_date: Optional[date] = None,
    ) -> None:
        if not (0 <= dividend_tax_rate <= 1):
            raise ValueError("dividend_tax_rate must be in [0, 1]")
        if not (0 <= capital_gains_tax_rate <= 1):
            raise ValueError("capital_gains_tax_rate must be in [0, 1]")
        self.dividend_tax_rate = dividend_tax_rate
        self.capital_gains_tax_rate = capital_gains_tax_rate
        self.required_return = required_return
        self._reference_date = reference_date

    @property
    def reference_date(self) -> date:
        return self._reference_date if self._reference_date is not None else date.today()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def simulate(self, event: DividendEvent) -> DividendShockResult:
        """Run the full dividend-shock simulation for *event*.

        Parameters
        ----------
        event:
            The :class:`DividendEvent` to simulate.

        Returns
        -------
        :class:`DividendShockResult`
            All calculated metrics.
        """
        stock = event.stock
        D = event.dividend_per_share

        # ------------------------------------------------------------------
        # 1. Ex-dividend price drop (Elton-Gruber model)
        # ------------------------------------------------------------------
        denom = 1 - self.capital_gains_tax_rate
        numer = 1 - self.dividend_tax_rate
        price_drop = D * (numer / denom) if denom != 0 else D

        ex_div_price = max(0.0, stock.price - price_drop)
        price_drop_pct = (price_drop / stock.price * 100) if stock.price > 0 else 0.0

        # ------------------------------------------------------------------
        # 2. Yield calculations
        # ------------------------------------------------------------------
        dividend_yield_pct = event.dividend_yield * 100
        after_tax_div = D * (1 - self.dividend_tax_rate)
        annual_after_tax = after_tax_div * event.frequency
        after_tax_yield_pct = (
            annual_after_tax / stock.price * 100 if stock.price > 0 else 0.0
        )

        # ------------------------------------------------------------------
        # 3. Total return estimate
        # ------------------------------------------------------------------
        # Expected capital return: rf + beta*(market_premium) - dividend_yield
        # Simplified: assume 7% equity premium, 4% risk-free rate
        risk_free = 0.04
        equity_premium = 0.07
        expected_total = risk_free + stock.beta * equity_premium
        income_return = dividend_yield_pct / 100
        capital_return = expected_total - income_return

        # ------------------------------------------------------------------
        # 4. DDM fair value (Gordon Growth Model)
        # ------------------------------------------------------------------
        ddm_fair_value = self._ddm_fair_value(
            event.annual_dividend, event.frequency, stock.beta
        )
        if ddm_fair_value > 0 and stock.price > 0:
            premium_to_fair = (stock.price - ddm_fair_value) / ddm_fair_value * 100
            if premium_to_fair > 5:
                ddm_implied = "overvalued"
            elif premium_to_fair < -5:
                ddm_implied = "undervalued"
            else:
                ddm_implied = "fairly valued"
        else:
            ddm_implied = "N/A"

        # ------------------------------------------------------------------
        # 5. Days to ex-div
        # ------------------------------------------------------------------
        days_to_ex = max(0, (event.ex_dividend_date - self.reference_date).days)

        return DividendShockResult(
            event=event,
            theoretical_ex_div_price=ex_div_price,
            price_drop_dollars=price_drop,
            price_drop_pct=price_drop_pct,
            dividend_yield_pct=dividend_yield_pct,
            annual_dividend=event.annual_dividend,
            after_tax_dividend=after_tax_div,
            after_tax_yield_pct=after_tax_yield_pct,
            capital_return_pct=capital_return * 100,
            income_return_pct=income_return * 100,
            total_return_pct=expected_total * 100,
            ddm_fair_value=ddm_fair_value,
            ddm_implied_return=ddm_implied,
            days_to_ex_div=days_to_ex,
        )

    def simulate_capture(
        self,
        event: DividendEvent,
        transaction_cost_bps: float = 10.0,
        holding_days: int = 1,
    ) -> CaptureResult:
        """Simulate a dividend-capture trade.

        The strategy:
            1. Buy at market close *before* the ex-dividend date.
            2. Receive the dividend.
            3. Sell *holding_days* after the ex-dividend date.

        Parameters
        ----------
        event:
            The dividend event.
        transaction_cost_bps:
            Round-trip transaction cost in basis points (default 10 bps).
        holding_days:
            Number of trading days to hold after the ex-div date (default 1).

        Returns
        -------
        :class:`CaptureResult`
        """
        stock = event.stock
        D = event.dividend_per_share

        # Prices
        buy_price = stock.price  # buy at current price (day before ex-div)

        # After ex-div, price drops by the after-tax amount
        after_tax_drop = D * (1 - self.dividend_tax_rate)
        sell_price = max(0.0, buy_price - after_tax_drop)

        # Transaction costs (round-trip)
        tx_cost = buy_price * transaction_cost_bps / 10_000 * 2  # buy + sell

        # After-tax dividend received
        after_tax_div = D * (1 - self.dividend_tax_rate)

        # P&L
        gross_pnl = after_tax_div - (buy_price - sell_price)
        net_pnl = gross_pnl - tx_cost
        pnl_pct = (net_pnl / buy_price * 100) if buy_price > 0 else 0.0

        # Annualised return (holding period = holding_days)
        holding = max(1, holding_days)
        ann_return = pnl_pct * (252 / holding)

        # Break-even: max price drop we can absorb and still profit
        max_drop = after_tax_div - tx_cost
        break_even_drop_pct = (max_drop / buy_price * 100) if buy_price > 0 else 0.0

        return CaptureResult(
            event=event,
            buy_price=buy_price,
            sell_price=sell_price,
            dividend_received=after_tax_div,
            transaction_cost_dollars=tx_cost,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            pnl_pct=pnl_pct,
            annualized_return_pct=ann_return,
            break_even_price_drop_pct=break_even_drop_pct,
            is_profitable=net_pnl > 0,
        )

    def dividend_reinvestment_plan(
        self,
        event: DividendEvent,
        years: int = 10,
        dividend_growth_rate: float = 0.03,
    ) -> list[dict]:
        """Project a dividend reinvestment plan (DRIP) over *years* years.

        Dividends are reinvested at the end of each year at the prevailing
        price (assumed to appreciate at the required return minus the income
        return).

        Parameters
        ----------
        event:
            The dividend event that seeds the projection.
        years:
            Projection horizon in years (default 10).
        dividend_growth_rate:
            Annual rate at which the dividend per share grows (default 3 %).

        Returns
        -------
        list of dict
            One dict per year with keys: year, shares, price, total_value,
            annual_dividend_income, cumulative_dividends.
        """
        results = []
        shares = 1.0  # start with 1 share
        price = event.stock.price
        dps = event.annual_dividend
        cumulative_dividends = 0.0

        # Price appreciation rate ≈ required_return − dividend_yield
        price_growth = max(0.0, self.required_return - event.dividend_yield)

        for yr in range(1, years + 1):
            price *= 1 + price_growth
            dps *= 1 + dividend_growth_rate
            annual_income = shares * dps * (1 - self.dividend_tax_rate)
            cumulative_dividends += annual_income
            new_shares = annual_income / price
            shares += new_shares
            results.append(
                {
                    "year": yr,
                    "shares": shares,
                    "price": price,
                    "total_value": shares * price,
                    "annual_dividend_income": annual_income,
                    "cumulative_dividends": cumulative_dividends,
                }
            )
        return results

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _ddm_fair_value(
        self,
        annual_dividend: float,
        frequency: int,
        beta: float,
    ) -> float:
        """Gordon Growth Model fair value.

        Uses a growth rate of 2.5 % and a required return built from CAPM:
        r = rf + β × equity_premium.  If r <= g, returns 0.
        """
        growth_rate = 0.025  # long-run sustainable dividend growth
        risk_free = 0.04
        equity_premium = 0.07
        required_return = risk_free + beta * equity_premium

        if required_return <= growth_rate or annual_dividend <= 0:
            return 0.0

        # D₁ = next year's dividend
        d1 = annual_dividend * (1 + growth_rate)
        return d1 / (required_return - growth_rate)
