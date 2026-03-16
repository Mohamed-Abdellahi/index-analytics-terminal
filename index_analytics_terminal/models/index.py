"""Index data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .stock import Stock


@dataclass
class IndexConstituent:
    """A stock's position within an index.

    Attributes:
        stock: The underlying :class:`Stock`.
        weight: Portfolio weight in the range ``[0, 1]``.
    """

    stock: Stock
    weight: float

    def __post_init__(self) -> None:
        if not (0 <= self.weight <= 1):
            raise ValueError(
                f"Weight must be in [0, 1], got {self.weight} for {self.stock.ticker}"
            )


@dataclass
class Index:
    """Represents a market index (e.g. S&P 500, NASDAQ-100).

    Attributes:
        name: Human-readable index name (e.g. ``"S&P 500"``).
        ticker: Index ticker/symbol (e.g. ``"SPX"``).
        total_aum: Aggregate AUM of all funds *tracking* this index, in
            **billions** USD.  This drives the dollar demand/supply
            calculation during rebalancing simulations.
        constituents: Mapping from ticker symbol to :class:`IndexConstituent`.
        rebalance_frequency: How often the index rebalances
            (``"quarterly"``, ``"monthly"``, ``"annual"``).
    """

    name: str
    ticker: str
    total_aum: float  # billions USD
    constituents: Dict[str, IndexConstituent] = field(default_factory=dict)
    rebalance_frequency: str = "quarterly"

    # ------------------------------------------------------------------ #
    # Properties                                                           #
    # ------------------------------------------------------------------ #

    @property
    def total_aum_dollars(self) -> float:
        """Aggregate tracking-fund AUM in USD."""
        return self.total_aum * 1_000_000_000

    @property
    def num_constituents(self) -> int:
        return len(self.constituents)

    @property
    def total_weight(self) -> float:
        return sum(c.weight for c in self.constituents.values())

    # ------------------------------------------------------------------ #
    # Mutation helpers                                                     #
    # ------------------------------------------------------------------ #

    def add_constituent(self, stock: Stock, weight: float) -> None:
        """Add *stock* with the given *weight* (other weights are rescaled)."""
        self.constituents[stock.ticker] = IndexConstituent(stock=stock, weight=weight)
        self._normalize_weights()

    def remove_constituent(self, ticker: str) -> Optional[IndexConstituent]:
        """Remove the constituent with *ticker*.  Remaining weights are rescaled."""
        constituent = self.constituents.pop(ticker, None)
        if constituent and self.constituents:
            self._normalize_weights()
        return constituent

    def get_weight(self, ticker: str) -> float:
        """Return the weight of *ticker*, or ``0.0`` if not present."""
        constituent = self.constituents.get(ticker)
        return constituent.weight if constituent else 0.0

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _normalize_weights(self) -> None:
        total = sum(c.weight for c in self.constituents.values())
        if total > 0:
            for c in self.constituents.values():
                c.weight /= total

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"{self.name} ({self.ticker}): {self.num_constituents} constituents | "
            f"Tracking AUM ${self.total_aum:.1f}B"
        )
