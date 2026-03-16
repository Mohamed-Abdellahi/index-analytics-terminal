# =============================================================================
# data/constituents.py
# Nifty 50 constituents — fetched dynamically from NSE API
# Only lot_size and div_yield are hardcoded (not available in NSE index API)
#

# =============================================================================

import pandas as pd
from typing import Optional
from data.futures import get_nifty50_data


# =============================================================================
# HARDCODED STATIC DATA
# Only what the NSE API doesn't provide
# we have to update div_yield manually after each earnings season
# =============================================================================

# F&O lot sizes — source: NSE F&O lot size circular
LOT_SIZES = {
    "RELIANCE": 250, "HDFCBANK": 550, "BHARTIARTL": 475, "SBIN": 1500,
    "ICICIBANK": 700, "TCS": 175, "BAJFINANCE": 125, "INFY": 400,
    "LT": 175, "HINDUNILVR": 300, "SUNPHARMA": 350, "MARUTI": 100,
    "AXISBANK": 625, "ITC": 1600, "NTPC": 3000, "M&M": 700,
    "KOTAKBANK": 400, "HCLTECH": 700, "TITAN": 175, "ONGC": 1925,
    "BEL": 4500, "ULTRACEMCO": 100, "ADANIPORTS": 1250, "WIPRO": 3000,
    "TATAMOTORS": 1425, "POWERGRID": 2750, "TATASTEEL": 5500,
    "NESTLEIND": 40, "TECHM": 600, "JSWSTEEL": 1350, "COALINDIA": 4200,
    "BAJAJFINSV": 500, "ASIANPAINT": 300, "CIPLA": 650, "DRREDDY": 125,
    "HINDALCO": 1400, "BPCL": 1800, "EICHERMOT": 175, "GRASIM": 375,
    "TATACONSUM": 900, "APOLLOHOSP": 125, "HEROMOTOCO": 300,
    "SHRIRAMFIN": 500, "INDUSINDBK": 900, "ADANIENT": 250,
    "DIVISLAB": 200, "BAJAJ-AUTO": 250, "BRITANNIA": 200,
    "SBILIFE": 750, "HDFCLIFE": 1100,
}

# Dividend yields (%) — last 12 months
# Update after each results season... but we can also take it from bbg
DIV_YIELDS = {
    "RELIANCE": 0.35, "HDFCBANK": 1.10, "BHARTIARTL": 0.40, "SBIN": 1.80,
    "ICICIBANK": 0.80, "TCS": 1.50, "BAJFINANCE": 0.25, "INFY": 2.20,
    "LT": 0.90, "HINDUNILVR": 1.60, "SUNPHARMA": 0.70, "MARUTI": 0.80,
    "AXISBANK": 0.10, "ITC": 3.20, "NTPC": 2.50, "M&M": 0.60,
    "KOTAKBANK": 0.10, "HCLTECH": 3.50, "TITAN": 0.35, "ONGC": 4.20,
    "BEL": 1.00, "ULTRACEMCO": 0.40, "ADANIPORTS": 0.50, "WIPRO": 0.20,
    "TATAMOTORS": 0.50, "POWERGRID": 3.80, "TATASTEEL": 1.50,
    "NESTLEIND": 1.20, "TECHM": 2.80, "JSWSTEEL": 1.20, "COALINDIA": 6.50,
    "BAJAJFINSV": 0.10, "ASIANPAINT": 1.30, "CIPLA": 0.60, "DRREDDY": 0.55,
    "HINDALCO": 0.80, "BPCL": 5.50, "EICHERMOT": 1.10, "GRASIM": 0.50,
    "TATACONSUM": 0.90, "APOLLOHOSP": 0.30, "HEROMOTOCO": 3.00,
    "SHRIRAMFIN": 1.00, "INDUSINDBK": 1.20, "ADANIENT": 0.05,
    "DIVISLAB": 1.00, "BAJAJ-AUTO": 1.50, "BRITANNIA": 1.50,
    "SBILIFE": 0.00, "HDFCLIFE": 0.30,
}


# Candidate stocks for addition (Module 2 — Rebalancing Simulator)
CANDIDATE_ADDITIONS = {
    "TRENT":  {"name": "Trent (Tata Retail)",   "sector": "Consumer Discretionary", "iwf": 0.65, "shares_ff": 890,  "div_yield": 0.20, "lot_size": 350},
    "ZOMATO": {"name": "Zomato",                 "sector": "Consumer Discretionary", "iwf": 0.82, "shares_ff": 8600, "div_yield": 0.00, "lot_size": 2000},
    "JIOFIN": {"name": "Jio Financial Services", "sector": "Financials",             "iwf": 0.36, "shares_ff": 5700, "div_yield": 0.00, "lot_size": 4500},
    "VEDL":   {"name": "Vedanta",                "sector": "Materials",              "iwf": 0.38, "shares_ff": 1490, "div_yield": 8.00, "lot_size": 2750},
}


# =============================================================================
# DYNAMIC FETCH — NSE API
# =============================================================================

def get_constituents() -> Optional[list]:
    """
    Fetch all Nifty 50 constituents dynamically from NSE API.
    Computes weights from ffmc (free-float market cap).

    Returns:
        list of dicts with fields:
            symbol, name, sector, last_price, ffmc,
            weight_pct, div_yield, lot_size,
            change, pct_change, prev_close,
            year_high, year_low, is_fno

    Example (notebook):
        from data.constituents import get_constituents
        cs = get_constituents()
        for c in cs[:3]:
            print(c['symbol'], c['last_price'], c['weight_pct'])
    """
    try:
        data = get_nifty50_data()
        if data is None:
            return None

        # Filter out the index itself (symbol = "NIFTY 50")
        raw        = [item for item in data["data"] if item.get("symbol") != "NIFTY 50"]
        total_ffmc = sum(item.get("ffmc", 0) for item in raw)

        constituents = []
        for item in raw:
            symbol = item.get("symbol", "")
            ffmc   = item.get("ffmc", 0)
            meta   = item.get("meta", {}) ## meta contains companyName, industry, isFNOSec etc. — more static info about the stock

            constituents.append({
                "symbol":     symbol,
                "name":       meta.get("companyName", symbol),
                "sector":     meta.get("industry", "Unknown"),
                "last_price": float(item.get("lastPrice", 0)),
                "prev_close": float(item.get("previousClose", 0)),
                "change":     float(item.get("change", 0)),
                "pct_change": float(item.get("pChange", 0)),
                "ffmc":       float(ffmc),
                "weight_pct": round(ffmc / total_ffmc * 100, 4) if total_ffmc else 0,
                "year_high":  float(item.get("yearHigh", 0)),
                "year_low":   float(item.get("yearLow", 0)),
                "is_fno":     meta.get("isFNOSec", False),
                "div_yield":  DIV_YIELDS.get(symbol, 0.0),
                "lot_size":   LOT_SIZES.get(symbol, 0),
            })

        constituents.sort(key=lambda x: x["weight_pct"], reverse=True)
        return constituents

    except Exception as e:
        print(f"[get_constituents] Error: {e}")
        return None


def get_constituent_df() -> Optional[pd.DataFrame]:
    """
    Return a clean DataFrame of all Nifty 50 constituents.

    Example (notebook):
        from data.constituents import get_constituent_df
        df = get_constituent_df()
        print(df[['name', 'sector', 'weight_pct', 'last_price', 'div_yield']])
    """
    constituents = get_constituents()
    if constituents is None:
        return None
    return pd.DataFrame(constituents).set_index("symbol")


def get_prices_dict() -> dict:
    """
    Return {symbol: last_price} for all Nifty 50 constituents.
    Single API call — much faster than fetching one by one.

    Example (notebook):
        from data.constituents import get_prices_dict
        prices = get_prices_dict()
        print(prices['RELIANCE'])
    """
    constituents = get_constituents()
    if not constituents:
        return {}
    return {c["symbol"]: c["last_price"] for c in constituents}