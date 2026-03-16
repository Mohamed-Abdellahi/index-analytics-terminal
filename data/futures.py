# =============================================================================
# data/futures.py
# Nifty 50 — live prices via NSE API + expiry calendar logic
# Replaced yfinance with nsepython for reliable Indian market data
#
# HOW TO TEST IN NOTEBOOK:
#   from data.futures import get_nifty_spot, get_expiry_dates, get_days_to_expiry
#   print(get_nifty_spot())
#   print(get_expiry_dates())
# =============================================================================

from nsepython import nsefetch
from datetime import datetime, date
from typing import Optional, Dict, Any
import calendar


# =============================================================================
# NSE API ENDPOINTS
# =============================================================================

NSE_NIFTY50_URL  = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
NSE_FUTURES_URL  = "https://www.nseindia.com/api/quote-derivative?symbol=NIFTY"


# =============================================================================
# NSE F&O EXPIRY CALENDAR
# Nifty monthly futures expire on the last Thursday of each month.
# If that Thursday is a market holiday, expiry moves to the previous Wednesday.
# =============================================================================

NSE_HOLIDAYS_2026 = {
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 17),   # Holi
    date(2026, 4, 14),   # Good Friday
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Gandhi Jayanti
    date(2026, 10, 22),  # Diwali (tentative)
    date(2026, 11, 5),   # Diwali Laxmi Puja (tentative)
    date(2026, 12, 25),  # Christmas
}


def get_last_thursday(year: int, month: int) -> date:
    """Return the last Thursday of a given month, adjusted for NSE holidays."""
    last_day = calendar.monthrange(year, month)[1]
    d = date(year, month, last_day)
    while d.weekday() != 3:  # 3 = Thursday
        d = date(year, month, d.day - 1)
    while d in NSE_HOLIDAYS_2026 or d.weekday() in (5, 6):
        d = date(year, month, d.day - 1)
    return d


def get_expiry_dates(n_months: int = 3) -> list:
    """
    Get the next n monthly expiry dates for Nifty futures.

    Returns:
        list of date objects, sorted ascending

    Example (notebook):
        from data.futures import get_expiry_dates
        print(get_expiry_dates())
    """
    today = date.today()
    expiries = []
    year, month = today.year, today.month
    while len(expiries) < n_months:
        exp = get_last_thursday(year, month)
        if exp >= today:
            expiries.append(exp)
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return sorted(expiries)


def get_days_to_expiry(expiry: Optional[date] = None) -> int:
    """
    Calendar days from today to the nearest (or given) Nifty expiry.

    Example (notebook):
        from data.futures import get_days_to_expiry
        print(f"Days to expiry: {get_days_to_expiry()}")
    """
    if expiry is None:
        expiry = get_expiry_dates(1)[0]
    return max((expiry - date.today()).days, 1)


# =============================================================================
# LIVE DATA — NSE API
# =============================================================================

def get_nifty50_data() -> Optional[Dict[str, Any]]:
    """
    Fetch full Nifty 50 index data from NSE API.
    Returns the raw API response dict.

    Example (notebook):
        from data.futures import get_nifty50_data
        data = get_nifty50_data()
        print(data['metadata'])   # index level, advances, declines
        print(data['data'][0])    # first constituent
    """
    try:
        return nsefetch(NSE_NIFTY50_URL)
    except Exception as e:
        print(f"[get_nifty50_data] Error: {e}")
        return None


def get_nifty_spot() -> Optional[float]:
    """
    Fetch the latest Nifty 50 spot index level from NSE.

    Returns:
        float — latest index level, or None on error

    Example (notebook):
        from data.futures import get_nifty_spot
        print(f"Nifty spot: {get_nifty_spot():,.2f}")
    """
    try:
        data = get_nifty50_data()
        if data is None:
            return None
        # metadata contains the index level
        return float(data["metadata"]["last"])
    except Exception as e:
        print(f"[get_nifty_spot] Error: {e}")
        return None


def get_live_constituent_prices() -> Dict[str, float]:
    """
    Fetch latest prices for all Nifty 50 constituents from NSE API.
    Uses the same endpoint as get_nifty50_data() — single API call for all 50 stocks.

    Returns:
        dict {nse_symbol: last_price}

    Example (notebook):
        from data.futures import get_live_constituent_prices
        prices = get_live_constituent_prices()
        print(prices)
    """
    try:
        data = get_nifty50_data()
        if data is None:
            return {}
        prices = {}
        for item in data["data"]:
            symbol = item.get("symbol")
            price  = item.get("lastPrice")
            if symbol and price:
                prices[symbol] = float(price)
        return prices
    except Exception as e:
        print(f"[get_live_constituent_prices] Error: {e}")
        return {}


def get_futures_price() -> Optional[float]:
    """
    Fetch the latest Nifty 50 near-month futures price from NSE.
    Falls back to spot price if futures data unavailable.

    Returns:
        float — futures last price, or None on error

    Example (notebook):
        from data.futures import get_futures_price
        print(f"Nifty Futures: {get_futures_price():,.2f}")
    """
    try:
        data = nsefetch(NSE_FUTURES_URL)
        # Find near-month futures contract
        if "stocks" in data:
            for item in data["stocks"]:
                md = item.get("metadata", {})
                if md.get("instrumentType") == "Index Futures":
                    return float(md.get("lastPrice", 0))
        # Fallback to spot
        return get_nifty_spot()
    except Exception as e:
        print(f"[get_futures_price] Falling back to spot: {e}")
        return get_nifty_spot()