# index-analytics-terminal

A terminal-based trading tool to simulate **index rebalancing effects**, **dividend shocks**, and related arbitrage strategies.

---

## Features

| Module | What it does |
|---|---|
| **Index Rebalancing Simulator** | Estimates price impact when a stock is added to / removed from a major index; models the arbitrage window between announcement and effective date |
| **Dividend Shock Simulator** | Predicts the ex-dividend price drop (Elton-Gruber model), analyses dividend-capture strategies, computes DDM fair values, and projects DRIP returns |
| **Rich terminal display** | Colour-coded tables with demand/supply analysis, P&L breakdowns, and return metrics |

---

## Quick start

```bash
# Install
pip install -e .

# Run the built-in demo (fictional data)
iat demo

# Simulate a stock addition to the S&P 500
iat rebalance \
  --ticker AAPL \
  --price 185.00 \
  --shares-out 15500 \
  --adv 55.0 \
  --name "Apple Inc" \
  --action ADD \
  --index-name "S&P 500" \
  --index-aum 5000 \
  --new-weight 0.07 \
  --announce 2024-03-01 \
  --effective 2024-03-22

# Simulate a dividend shock
iat dividend \
  --ticker KO \
  --price 61.50 \
  --shares-out 4300 \
  --adv 12.0 \
  --name "Coca-Cola" \
  --dividend 0.485 \
  --ex-div 2024-03-14 \
  --frequency 4 \
  --drip-years 20
```

---

## Commands

### `iat rebalance`

Simulate an index rebalancing event.

```
Options:
  --ticker TEXT           Ticker symbol (e.g. AAPL)          [required]
  --price FLOAT           Current stock price (USD)           [required]
  --shares-out FLOAT      Shares outstanding in millions      [required]
  --adv FLOAT             Average daily volume (M shares)     [required]
  --action ADD|REMOVE     Addition or removal                 [required]
  --index-name TEXT       Index name                          [default: S&P 500]
  --index-aum FLOAT       Tracking-fund AUM in billions USD   [default: 5000]
  --new-weight FLOAT      Target weight [0-1]                 [default: 0.005]
  --old-weight FLOAT      Current weight [0-1]                [default: 0.0]
  --announce DATE         Announcement date (YYYY-MM-DD)      [required]
  --effective DATE        Effective date (YYYY-MM-DD)         [required]
  --position FLOAT        Arb position size in millions USD   [default: 1.0]
  --tx-cost FLOAT         One-way transaction cost (bps)      [default: 5.0]
```

**Output includes:**
- Demand / supply analysis (shares & dollars to trade, demand/ADV ratio)
- Square-root price-impact estimate
- Estimated post-impact price
- Tracking-error contribution for index funds
- Arbitrage P&L per share & annualised return
- Concrete arbitrage scenario with entry/exit prices, Sharpe ratio

### `iat dividend`

Simulate a dividend shock.

```
Options:
  --ticker TEXT           Ticker symbol                       [required]
  --price FLOAT           Current stock price (USD)           [required]
  --shares-out FLOAT      Shares outstanding in millions      [required]
  --adv FLOAT             Average daily volume (M shares)     [required]
  --dividend FLOAT        Dividend per share (USD)            [required]
  --ex-div DATE           Ex-dividend date (YYYY-MM-DD)       [required]
  --frequency INT         Payments per year                   [default: 4]
  --div-tax FLOAT         Dividend tax rate [0-1]             [default: 0.15]
  --cg-tax FLOAT          Capital-gains tax rate [0-1]        [default: 0.20]
  --tx-cost FLOAT         Round-trip transaction cost (bps)   [default: 10.0]
  --drip-years INT        DRIP projection horizon (years)     [default: 10]
  --no-capture            Skip dividend-capture analysis
  --no-drip               Skip DRIP projection
```

**Output includes:**
- Dividend yield (gross and after-tax)
- Theoretical ex-dividend price drop (Elton-Gruber model)
- Expected capital / income / total return
- Gordon Growth Model fair value and over/under-valuation signal
- Dividend-capture strategy P&L with break-even analysis
- Year-by-year DRIP projection (shares, price, total value, income)

### `iat demo`

Runs both simulations with realistic fictional data — no arguments needed.

---

## Models & methodology

### Index Rebalancing — Square-Root Impact Model

When an index fund must trade a large block relative to available liquidity,
price impact follows a square-root relationship (Almgren & Chriss, 2001):

```
impact (%) = k × sqrt(demand / supply)

demand = index_tracking_AUM × |Δweight|
supply = ADV × trading_days_in_window
k      ≈ 0.10  (empirically calibrated)
```

Arbitrageurs buy (additions) or short (deletions) on the announcement date and
unwind on the effective date, capturing ~65 % of the theoretical impact.

### Dividend Shock — Elton-Gruber Tax-Clientele Model (1970)

The ex-dividend price drop is governed by the marginal investor's tax rates:

```
ΔP = D × (1 − τ_dividend) / (1 − τ_capital_gains)
```

For a tax-exempt investor (τ = 0), ΔP = D (full drop).  
For a high-CG-tax investor, ΔP > D (stock drops *more* than the dividend).

### DDM Fair Value — Gordon Growth Model

```
Fair Value = D₁ / (r − g)

D₁ = next-year dividend (= D_annual × (1 + g))
r  = rf + β × equity_premium   (CAPM)
g  = 2.5 %  (long-run sustainable growth)
```

---

## Project structure

```
index_analytics_terminal/
├── cli.py               # Click-based CLI entry point
├── models/
│   ├── stock.py         # Stock dataclass
│   └── index.py         # Index & IndexConstituent dataclasses
├── simulators/
│   ├── rebalancing.py   # RebalancingSimulator
│   └── dividend_shock.py # DividendShockSimulator
└── display/
    └── tables.py        # Rich terminal display
tests/
├── conftest.py
├── test_rebalancing.py
└── test_dividend_shock.py
```

---

## Running tests

```bash
pip install pytest
pytest tests/ -v
```

---

## License

MIT
