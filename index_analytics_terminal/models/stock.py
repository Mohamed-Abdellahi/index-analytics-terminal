"""Stock data model."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Stock:
    """Represents a publicly-traded equity instrument.

    Attributes:
        ticker: Exchange ticker symbol (e.g. ``"AAPL"``).
        name: Full company name.
        price: Current price in USD.
        shares_outstanding: Total shares outstanding in *millions*.
        adv: Average daily volume in *millions* of shares.
        sector: GICS sector (informational, defaults to ``"Unknown"``).
        beta: Market beta (sensitivity to broad-market moves).
        volatility: Annualised price volatility (e.g. ``0.20`` = 20 %).
    """

    ticker: str
    name: str
    price: float
    shares_outstanding: float  # millions
    adv: float  # millions of shares
    sector: str = "Unknown"
    beta: float = 1.0
    volatility: float = 0.20

    # ------------------------------------------------------------------ #
    # Derived properties                                                   #
    # ------------------------------------------------------------------ #

    @property
    def market_cap(self) -> float:
        """Market capitalisation in *millions* USD."""
        return self.price * self.shares_outstanding

    @property
    def market_cap_dollars(self) -> float:
        """Market capitalisation in USD."""
        return self.market_cap * 1_000_000

    @property
    def adv_dollars(self) -> float:
        """Average daily volume in USD."""
        return self.adv * self.price * 1_000_000

    @property
    def daily_volatility(self) -> float:
        """Daily volatility derived from the annualised figure."""
        return self.volatility / math.sqrt(252)

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"{self.ticker} ({self.name}): ${self.price:,.2f} | "
            f"MCap ${self.market_cap:,.0f}M | ADV {self.adv:.2f}M shares"
        )
