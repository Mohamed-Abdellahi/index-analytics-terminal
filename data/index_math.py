# =============================================================================
# data/index_math.py
# Pure calculation engine — ZERO assumptions, ZERO defaults
# Every input must be explicitly provided by the caller
# No hardcoded rates, no proxy prices, no fallbacks
#
# HOW TO TEST IN NOTEBOOK:
#   from data.index_math import compute_dividend_drag, compute_fair_value
#   from data.constituents import get_constituent_df, get_prices_dict
#   from data.futures import get_nifty_spot, get_days_to_expiry
#
#   df             = get_constituent_df()
#   prices         = get_prices_dict()
#   spot           = get_nifty_spot()
#   days           = get_days_to_expiry()
#   futures_price  = float(input("Enter Nifty futures price: "))
#   risk_free_rate = float(input("Enter risk-free rate (e.g. 0.065): "))
#
#   drag = compute_dividend_drag(df, prices, spot, days)
#   fv   = compute_fair_value(spot, days, drag, futures_price, risk_free_rate)
#   print(fv)
# =============================================================================

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# CONSTANTS — structural only, no financial assumptions
# =============================================================================

NIFTY_LOT_SIZE = 75  # units per futures contract — fixed by NSE


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FairValueResult:
    spot:              float
    fair_value:        float
    market_futures:    float
    basis:             float
    basis_annualized:  float   # % annualized
    cost_of_carry:     float   # index points
    dividend_drag:     float   # index points
    days_to_expiry:    int


@dataclass
class DividendShockResult:
    symbol:               str
    stock_name:           str
    weight_pct:           float
    base_div_yield:       float   # %
    shocked_div_yield:    float   # %
    delta_div_points:     float   # index points
    base_fair_value:      float
    shocked_fair_value:   float
    delta_fair_value:     float   # index points
    delta_per_lot:        float   # ₹ P&L per futures contract


@dataclass
class RebalancingResult:
    stock_out:              str
    stock_in:               str
    old_index_level:        float
    new_index_level:        float
    delta_index_points:     float
    old_weights:            dict    # {symbol: weight_pct}
    new_weights:            dict    # {symbol: weight_pct}
    tracker_aum_bn:         float   # ₹ billion
    buy_stock_in_shares:    float
    buy_stock_in_value:     float   # ₹
    sell_stock_out_shares:  float
    sell_stock_out_value:   float   # ₹
    old_fair_value:         float
    new_fair_value:         float
    delta_future_points:    float


# =============================================================================
# CORE CALCULATIONS
# =============================================================================

def compute_dividend_drag(
    df: pd.DataFrame,
    prices: dict,
    index_level: float,
    days_to_expiry: int,
    overrides: dict = None,
) -> float:
    """
    Compute total dividend drag on Nifty futures in index points.

    The Nifty 50 is a Price Return Index — dividends are NOT reinvested.
    Each dividend paid by a constituent reduces its spot price → reduces
    the index level. The futures price had already priced in these expected
    dividends → the futures trades at a discount to the carry price by
    exactly this dividend drag amount.

    Formula per constituent i:
        drag_i = index_level × (weight_i / 100) × (div_yield_i / 100) × (days / 365)

    Total drag = Σ drag_i

    Args:
        df             : DataFrame from get_constituent_df()
                         must have columns [weight_pct, div_yield]
        prices         : dict {symbol: last_price} from get_prices_dict()
                         used to confirm symbol is active
        index_level    : current Nifty spot level
        days_to_expiry : calendar days to futures expiry
        overrides      : dict {symbol: new_div_yield_%} — used in shock simulation
                         only overrides the symbols you specify, rest unchanged

    Returns:
        float — total dividend drag in index points

    Example (notebook):
        drag = compute_dividend_drag(df, prices, 23151, 30)
        print(f"Dividend drag: {drag:.2f} pts")

        # With override — simulate Reliance special dividend
        drag_shocked = compute_dividend_drag(df, prices, 23151, 30,
                                             overrides={"RELIANCE": 2.0})
    """
    overrides     = overrides or {}
    total_drag    = 0.0
    time_fraction = days_to_expiry / 365.0

    for symbol, row in df.iterrows():
        if symbol not in prices:
            continue
        div_yield   = overrides.get(symbol, row["div_yield"])
        weight      = row["weight_pct"] / 100.0
        total_drag += index_level * weight * (div_yield / 100.0) * time_fraction

    return total_drag


def compute_fair_value(
    index_level: float,
    days_to_expiry: int,
    dividend_drag: float,
    market_futures: float,
    risk_free_rate: float,
) -> FairValueResult:
    """
    Compute the theoretical fair value of Nifty 50 futures.

    Formula:
        Fair Value = Spot × [1 + rf × (T/365)] - Dividend_Drag

    Basis = Market Futures - Fair Value
        Positive basis → futures trading RICH  → sell futures, buy spot
        Negative basis → futures trading CHEAP → buy futures, sell spot

    Args:
        index_level    : current Nifty spot level
        days_to_expiry : calendar days to futures expiry
        dividend_drag  : total dividend drag in pts (from compute_dividend_drag)
        market_futures : actual futures price observed in the market
        risk_free_rate : annualized risk-free rate as decimal (e.g. 0.065 for 6.5%)
                         use RBI repo rate or 91-day T-bill yield

    Returns:
        FairValueResult dataclass

    Example (notebook):
        fv = compute_fair_value(
            index_level    = 23151,
            days_to_expiry = 30,
            dividend_drag  = 45.2,
            market_futures = 23200,
            risk_free_rate = 0.065
        )
        print(f"Fair value : {fv.fair_value:.2f}")
        print(f"Basis      : {fv.basis:+.2f} pts")
        print(f"Basis ann. : {fv.basis_annualized:+.4f}%")
    """
    time_fraction = days_to_expiry / 365.0
    cost_of_carry = index_level * risk_free_rate * time_fraction
    fair_value    = index_level + cost_of_carry - dividend_drag
    basis         = market_futures - fair_value
    basis_ann     = (basis / index_level) * (365.0 / days_to_expiry) * 100 \
                    if days_to_expiry > 0 else 0.0

    return FairValueResult(
        spot             = round(index_level, 2),
        fair_value       = round(fair_value, 2),
        market_futures   = round(market_futures, 2),
        basis            = round(basis, 2),
        basis_annualized = round(basis_ann, 4),
        cost_of_carry    = round(cost_of_carry, 2),
        dividend_drag    = round(dividend_drag, 2),
        days_to_expiry   = days_to_expiry,
    )


# =============================================================================
# MODULE 1 — DIVIDEND SHOCK SIMULATOR
# =============================================================================

def simulate_dividend_shock(
    symbol: str,
    shocked_div_yield: float,
    df: pd.DataFrame,
    prices: dict,
    index_level: float,
    days_to_expiry: int,
    market_futures: float,
    risk_free_rate: float,
) -> DividendShockResult:
    """
    Simulate the impact of changing one constituent's expected dividend
    on the Nifty 50 futures fair value.

    Use cases on a :
        - Company announces SPECIAL DIVIDEND → yield rises → FV drops → futures cheap
        - Company CUTS dividend → yield falls → FV rises → futures rich
        - You have a different div view than market consensus

    All inputs must be explicitly provided — no defaults.

    Args:
        symbol            : NSE symbol to shock (e.g. "RELIANCE")
        shocked_div_yield : your scenario dividend yield in % (e.g. 2.0)
        df                : DataFrame from get_constituent_df()
        prices            : dict from get_prices_dict()
        index_level       : current Nifty spot level
        days_to_expiry    : calendar days to futures expiry
        market_futures    : actual futures price in the market
        risk_free_rate    : annualized risk-free rate as decimal

    Returns:
        DividendShockResult dataclass

    Example (notebook):
        result = simulate_dividend_shock(
            symbol            = "RELIANCE",
            shocked_div_yield = 2.0,
            df                = df,
            prices            = prices,
            index_level       = 23151,
            days_to_expiry    = 30,
            market_futures    = 23200,
            risk_free_rate    = 0.065,
        )
        print(f"FV change   : {result.delta_fair_value:+.2f} pts")
        print(f"P&L per lot : ₹{result.delta_per_lot:+,.0f}")
    """
    row            = df.loc[symbol]
    base_div_yield = row["div_yield"]
    weight_pct     = row["weight_pct"]
    stock_name     = row["name"] if "name" in df.columns else symbol

    base_drag    = compute_dividend_drag(df, prices, index_level, days_to_expiry)
    shocked_drag = compute_dividend_drag(df, prices, index_level, days_to_expiry,
                                         overrides={symbol: shocked_div_yield})

    base_fv    = compute_fair_value(index_level, days_to_expiry, base_drag,    market_futures, risk_free_rate)
    shocked_fv = compute_fair_value(index_level, days_to_expiry, shocked_drag, market_futures, risk_free_rate)

    delta_fv      = shocked_fv.fair_value - base_fv.fair_value
    delta_per_lot = delta_fv * NIFTY_LOT_SIZE

    return DividendShockResult(
        symbol             = symbol,
        stock_name         = stock_name,
        weight_pct         = weight_pct,
        base_div_yield     = base_div_yield,
        shocked_div_yield  = shocked_div_yield,
        delta_div_points   = round(shocked_drag - base_drag, 4),
        base_fair_value    = base_fv.fair_value,
        shocked_fair_value = shocked_fv.fair_value,
        delta_fair_value   = round(delta_fv, 2),
        delta_per_lot      = round(delta_per_lot, 0),
    )


# =============================================================================
# MODULE 2 — CONSTITUENT SWAP SIMULATOR
# =============================================================================

def simulate_constituent_swap(
    symbol_out: str,
    symbol_in: str,
    price_in: float,
    div_yield_in: float,
    df: pd.DataFrame,
    prices: dict,
    index_level: float,
    days_to_expiry: int,
    market_futures: float,
    risk_free_rate: float,
    tracker_aum_bn: float,
) -> RebalancingResult:
    """
    Simulate the impact of replacing one Nifty 50 constituent with another.

    What happens on rebalancing implementation day:
        1. NSE removes stock_out, adds stock_in
        2. Divisor adjusted → index level stays continuous at announcement
        3. Passive trackers MUST sell stock_out, buy stock_in
        4. Futures fair value re-prices with new dividend profile

    Tracker flows are what Delta One desks model before each rebalancing —
    they know exactly how many shares need to change hands and position
    accordingly to capture the implementation impact.

    All inputs must be explicitly provided — no defaults.

    Args:
        symbol_out     : NSE symbol being removed (e.g. "DRREDDY")
        symbol_in      : NSE symbol being added (e.g. "ETERNAL")
        price_in       : current market price of incoming stock (₹)
        div_yield_in   : dividend yield of incoming stock (%)
        df             : DataFrame from get_constituent_df()
        prices         : dict from get_prices_dict()
        index_level    : current Nifty spot level
        days_to_expiry : calendar days to futures expiry
        market_futures : actual futures price in the market
        risk_free_rate : annualized risk-free rate as decimal
        tracker_aum_bn : total AUM of passive Nifty trackers (₹ billion)
                         source: AMFI data, currently ~₹2,500bn for Nifty 50

    Returns:
        RebalancingResult dataclass

    Example (notebook):
        result = simulate_constituent_swap(
            symbol_out     = "DRREDDY",
            symbol_in      = "ETERNAL",
            price_in       = 217.0,
            div_yield_in   = 0.0,
            df             = df,
            prices         = prices,
            index_level    = 23151,
            days_to_expiry = 30,
            market_futures = 23200,
            risk_free_rate = 0.065,
            tracker_aum_bn = 2500,
        )
        print(f"Futures delta : {result.delta_future_points:+.2f} pts")
        print(f"Buy  {result.stock_in}  : ₹{result.buy_stock_in_value/1e7:.1f} Cr")
        print(f"Sell {result.stock_out} : ₹{result.sell_stock_out_value/1e7:.1f} Cr")
    """
    # ── Total FF market cap before swap ──────────────────────────────────────
    total_ffmc_before = df["ffmc"].sum()

    # ── FF market cap of outgoing stock ──────────────────────────────────────
    ffmc_out     = df.loc[symbol_out, "ffmc"]
    price_out    = df.loc[symbol_out, "last_price"]
    weight_out   = df.loc[symbol_out, "weight_pct"] / 100.0

    # ── Estimate FF market cap of incoming stock ──────────────────────────────
    # ffmc_in = ffmc_out × (price_in / price_out) as first-order approximation
    # In production this would use actual shares_ff × iwf from NSE factsheet
    ffmc_in = total_ffmc_before * weight_out * (price_in / price_out) if price_out > 0 else 0

    total_ffmc_after = total_ffmc_before - ffmc_out + ffmc_in

    # ── New weights ───────────────────────────────────────────────────────────
    old_weights = {s: round(row["weight_pct"], 4) for s, row in df.iterrows()}
    new_weights = {}
    for s, row in df.iterrows():
        if s == symbol_out:
            continue
        new_weights[s] = round(row["ffmc"] / total_ffmc_after * 100, 4)
    new_weights[symbol_in] = round(ffmc_in / total_ffmc_after * 100, 4)

    # ── Tracker flows ─────────────────────────────────────────────────────────
    tracker_aum = tracker_aum_bn * 1_000_000_000
    buy_value   = tracker_aum * (new_weights.get(symbol_in, 0) / 100.0)
    sell_value  = tracker_aum * weight_out
    buy_shares  = buy_value  / price_in  if price_in  > 0 else 0
    sell_shares = sell_value / price_out if price_out > 0 else 0

    # ── New fair value ────────────────────────────────────────────────────────
    new_df = df.drop(index=symbol_out).copy()
    for s in new_df.index:
        new_df.loc[s, "weight_pct"] = new_weights.get(s, 0)

    new_df.loc[symbol_in] = {
        "name":       symbol_in,
        "sector":     "Unknown",
        "last_price": price_in,
        "prev_close": price_in,
        "change":     0, "pct_change": 0,
        "ffmc":       ffmc_in,
        "weight_pct": new_weights[symbol_in],
        "year_high":  price_in, "year_low": price_in,
        "is_fno":     True,
        "div_yield":  div_yield_in,
        "lot_size":   0,
    }

    new_prices = {**prices, symbol_in: price_in}

    base_drag  = compute_dividend_drag(df,     prices,     index_level, days_to_expiry)
    new_drag   = compute_dividend_drag(new_df, new_prices, index_level, days_to_expiry)
    base_fv    = compute_fair_value(index_level, days_to_expiry, base_drag, market_futures, risk_free_rate)
    new_fv     = compute_fair_value(index_level, days_to_expiry, new_drag,  market_futures, risk_free_rate)

    return RebalancingResult(
        stock_out             = symbol_out,
        stock_in              = symbol_in,
        old_index_level       = round(index_level, 2),
        new_index_level       = round(index_level, 2),  # continuous at announcement
        delta_index_points    = 0.0,                    # divisor adjusted by NSE
        old_weights           = old_weights,
        new_weights           = new_weights,
        tracker_aum_bn        = tracker_aum_bn,
        buy_stock_in_shares   = round(buy_shares, 0),
        buy_stock_in_value    = round(buy_value, 0),
        sell_stock_out_shares = round(sell_shares, 0),
        sell_stock_out_value  = round(sell_value, 0),
        old_fair_value        = base_fv.fair_value,
        new_fair_value        = new_fv.fair_value,
        delta_future_points   = round(new_fv.fair_value - base_fv.fair_value, 2),
    )


# =============================================================================
# SENSITIVITY TABLE
# =============================================================================

def sensitivity_table(
    index_level: float,
    days_to_expiry: int,
    dividend_drag: float,
    market_futures: float,
    risk_free_rate_min: float,
    risk_free_rate_max: float,
    steps: int = 7,
) -> pd.DataFrame:
    """
    Sensitivity of fair value and basis to risk-free rate.
    All bounds must be explicitly provided.

    Args:
        risk_free_rate_min : lower bound of rate range (e.g. 0.04)
        risk_free_rate_max : upper bound of rate range (e.g. 0.10)
        steps              : number of rate steps

    Example (notebook):
        tbl = sensitivity_table(23151, 30, 45.2, 23200, 0.04, 0.10)
        print(tbl)
    """
    rates = np.linspace(risk_free_rate_min, risk_free_rate_max, steps)
    rows  = []
    for r in rates:
        fv = compute_fair_value(index_level, days_to_expiry, dividend_drag, market_futures, r)
        rows.append({
            "risk_free_rate_%": round(r * 100, 2),
            "fair_value":       fv.fair_value,
            "basis":            fv.basis,
            "basis_ann_%":      fv.basis_annualized,
        })
    return pd.DataFrame(rows)