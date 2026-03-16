# Index Analytics Terminal · Nifty 50

> A Delta One desk tool for Nifty 50 index analytics — built with live NSE data.

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)
![Dash](https://img.shields.io/badge/Dash-2.18-orange?style=flat-square)
![NSE](https://img.shields.io/badge/Data-NSE%20India%20API-green?style=flat-square)

---

## Overview

This tool simulates key Delta One desk workflows on the **Nifty 50 index futures**, using live data from the NSE India API. It covers three core modules that a Delta One trader monitors daily:

- **Basis Monitor** — Fair value decomposition, basis calculation, rate sensitivity
- **Dividend Shock Simulator** — Impact of dividend changes on futures fair value and P&L per lot
- **Rebalancing Simulator** — Constituent swap mechanics, tracker flows, futures repricing

---

## Pages

### 01 · Basis Monitor
Computes the theoretical fair value of the Nifty 50 near-month futures contract:

```
Fair Value = Spot × [1 + rf × (T/365)] − Dividend Drag
Basis      = Market Futures − Fair Value
```

- Live Nifty 50 spot and constituent data from NSE API
- User inputs: futures price, risk-free rate, global dividend yield
- Rate sensitivity table (0.25% steps, ±2% around current rate)
- Waterfall chart: spot → carry → dividend drag → fair value
- Basis vs rate chart

### 02 · Dividend Shock Simulator
Simulates the impact of a dividend change on futures fair value:

- Single stock shock: select any Nifty 50 constituent, input a shocked dividend yield
- Shows FV delta in index points and P&L per futures lot (lot size = 75)
- Edit top 15 constituent dividend yields and recalculate full index drag
- Sensitivity chart: shocked yield vs FV delta

### 03 · Rebalancing Simulator
Models the impact of a constituent swap on announcement day:

- Select stock to remove and stock to add
- Computes new weights across all 50 constituents
- Estimates tracker flows (shares + ₹ Cr) based on passive AUM input
- Shows futures fair value before and after swap

### 04 · Methodology
Full documentation of Nifty 50 index rules:
- Index structure and fair value formula
- Semi-annual rebalancing calendar and eligibility criteria
- Divisor adjustment mechanics
- F&O contract specifications (lot size, expiry, settlement)

---

## Data Sources

| Data | Source |
|------|--------|
| Live constituent prices & weights | NSE India API (`nsepython`) |
| Index spot level | NSE India API |
| Dividend yields | NSE corporate actions (manually updated) |
| F&O lot sizes | NSE F&O circular |
| Expiry calendar | Computed (last Thursday of each month) |

> **Note**: Bloomberg API integration (BLPAPI) is on the roadmap for production use — forward dividend estimates and live futures prices would replace the current manual inputs.

---

## Installation

```bash
# Clone the repo
git clone https://github.com/Mohamed-Abdellahi/index-analytics-terminal.git
cd index-analytics-terminal

# Install dependencies
pip install -r requirements.txt

# Run
python app.py
```

Open **http://localhost:8050** in your browser.

---

## Requirements

```
dash>=2.18.0
dash-bootstrap-components>=1.6.0
plotly>=5.18.0
nsepython
pandas
numpy
```

---

## Project Structure

```
index-analytics-terminal/
├── app.py              ← Entry point, routing, rebalancing page
├── shared.py           ← Live data fetch, helpers, figure builders
├── pages/
│   ├── basis_monitor.py    ← Page 1: Basis Monitor
│   ├── dividend_shock.py   ← Page 2: Dividend Shock Simulator
│   └── info.py             ← Page 4: Methodology
├── data/
│   ├── constituents.py     ← NSE constituent fetch
│   ├── futures.py          ← Spot price, expiry calendar
│   └── index_math.py       ← Fair value, dividend drag, swap simulation
└── assets/
    └── style.css           ← Bloomberg terminal dark theme
```

---

## Author

**Mohamed-Abdellahi MOHAMED-ABDELLAHI**
MSc 203 · Université Paris Dauphine–PSL

📧 [mohamed-abdellahi.mohamed-abdellahi@dauphine.eu](mailto:mohamed-abdellahi.mohamed-abdellahi@dauphine.eu)
🔗 [LinkedIn](https://www.linkedin.com/in/mohamed-abdellahi-mohamed-abdellahi-4341a1205/)

---

*For informational purposes only — not investment advice.*
