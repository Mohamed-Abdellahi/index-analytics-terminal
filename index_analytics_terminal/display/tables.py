"""Rich-based terminal display utilities."""

from __future__ import annotations

from typing import List

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..simulators.rebalancing import ArbitrageScenario, RebalancingImpact
from ..simulators.dividend_shock import CaptureResult, DividendShockResult

console = Console()

_GREEN = "bold green"
_RED = "bold red"
_YELLOW = "bold yellow"
_CYAN = "cyan"
_BLUE = "bold blue"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _signed(value: float, fmt: str = ".2f", suffix: str = "") -> Text:
    """Return a coloured :class:`rich.text.Text` for a signed number."""
    colour = _GREEN if value >= 0 else _RED
    sign = "+" if value >= 0 else ""
    return Text(f"{sign}{value:{fmt}}{suffix}", style=colour)


def _pct(value: float) -> Text:
    return _signed(value, ".2f", " %")


def _dollars(value: float) -> Text:
    rounded = round(value, 2)
    colour = _GREEN if rounded >= 0 else _RED
    sign = "+" if rounded >= 0 else "-"
    return Text(f"{sign}${abs(rounded):,.2f}", style=colour)


# ---------------------------------------------------------------------------
# Public printers
# ---------------------------------------------------------------------------


def print_banner() -> None:
    """Print the application banner."""
    console.print(
        Panel(
            "[bold cyan]Index Analytics Terminal[/bold cyan]\n"
            "[dim]Simulate index rebalancing effects · dividend shocks · "
            "arbitrage strategies[/dim]",
            box=box.DOUBLE_EDGE,
            style="bold",
        )
    )


def print_rebalancing_impact(impact: RebalancingImpact) -> None:
    """Pretty-print a :class:`~simulators.rebalancing.RebalancingImpact`."""
    event = impact.event
    stock = event.stock
    idx = event.index

    action_colour = _GREEN if event.action == "ADD" else _RED
    action_label = Text(event.action, style=f"bold {action_colour}")

    # ── Header panel ────────────────────────────────────────────────────── #
    header = (
        f"[bold]{idx.name}[/bold] rebalancing  ·  "
        f"{event.action}  [bold cyan]{stock.ticker}[/bold cyan]  "
        f"({stock.name})\n"
        f"Announcement: [yellow]{event.announcement_date}[/yellow]  →  "
        f"Effective: [yellow]{event.effective_date}[/yellow]"
    )
    console.print(Panel(header, title="[bold]Rebalancing Event[/bold]", box=box.ROUNDED))

    # ── Stock info ───────────────────────────────────────────────────────── #
    stock_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    stock_table.add_column("Field", style="dim")
    stock_table.add_column("Value")
    stock_table.add_row("Ticker", f"[bold]{stock.ticker}[/bold]")
    stock_table.add_row("Price", f"${stock.price:,.2f}")
    stock_table.add_row("Market Cap", f"${stock.market_cap:,.0f} M")
    stock_table.add_row("ADV", f"{stock.adv:.2f} M shares  (${stock.adv_dollars/1e6:,.0f} M)")
    stock_table.add_row("Volatility (ann.)", f"{stock.volatility*100:.1f} %")
    stock_table.add_row("Sector", stock.sector)
    stock_table.add_row("Old Weight", f"{event.old_weight*100:.3f} %")
    stock_table.add_row("New Weight", f"{event.new_weight*100:.3f} %")
    console.print(Panel(stock_table, title="[bold]Stock Details[/bold]", box=box.ROUNDED))

    # ── Demand / supply ──────────────────────────────────────────────────── #
    ds_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    ds_table.add_column("Metric", style="dim")
    ds_table.add_column("Value")
    ds_table.add_row("Index Tracking AUM", f"${idx.total_aum:.1f} B")
    ds_table.add_row("Shares to Trade", f"{impact.shares_traded_millions:.2f} M shares")
    ds_table.add_row("Dollars to Trade", f"${impact.dollars_traded_millions:,.0f} M")
    ds_table.add_row("Trading-Day Window", f"{impact.days_to_effective} days")
    demand_colour = _RED if impact.demand_to_adv_ratio > 1 else _GREEN
    ds_table.add_row(
        "Demand / ADV × Days",
        Text(f"{impact.demand_to_adv_ratio:.2f}×", style=demand_colour),
    )
    console.print(Panel(ds_table, title="[bold]Demand & Supply[/bold]", box=box.ROUNDED))

    # ── Price impact ─────────────────────────────────────────────────────── #
    pi_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    pi_table.add_column("Metric", style="dim")
    pi_table.add_column("Value")
    pi_table.add_row("Est. Price Impact", _pct(impact.price_impact_pct))
    pi_table.add_row("Impact in $", _dollars(impact.price_impact_dollars))
    pi_table.add_row("Current Price", f"${stock.price:,.2f}")
    pi_table.add_row(
        "Est. Post-Impact Price",
        f"[bold]${impact.estimated_post_impact_price:,.2f}[/bold]",
    )
    pi_table.add_row("Announcement-Day Return", _pct(impact.announcement_return_pct))
    pi_table.add_row(
        "Tracking-Error Contribution",
        f"{impact.tracking_error_contribution_bps:.1f} bps",
    )
    console.print(Panel(pi_table, title="[bold]Price Impact Estimate[/bold]", box=box.ROUNDED))

    # ── Arbitrage summary ────────────────────────────────────────────────── #
    arb_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    arb_table.add_column("Metric", style="dim")
    arb_table.add_column("Value")
    arb_table.add_row("Arb P&L per Share", _dollars(impact.arbitrage_pnl_per_share))
    arb_table.add_row("Total Arb P&L (10 % pos.)", f"${impact.arbitrage_pnl_total_millions:.2f} M")
    arb_table.add_row("Annualised Return", _pct(impact.annualized_return_pct))
    console.print(Panel(arb_table, title="[bold]Arbitrage Summary[/bold]", box=box.ROUNDED))


def print_arbitrage_scenario(scenario: ArbitrageScenario, position_m: float) -> None:
    """Pretty-print an :class:`~simulators.rebalancing.ArbitrageScenario`."""
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t.add_column("Metric", style="dim")
    t.add_column("Value")
    t.add_row("Position Size", f"${position_m:.1f} M")
    t.add_row("Entry Date", str(scenario.entry_date))
    t.add_row("Exit Date", str(scenario.exit_date))
    t.add_row("Entry Price", f"${scenario.entry_price:,.2f}")
    t.add_row("Exit Price", f"${scenario.exit_price:,.2f}")
    t.add_row("Shares Traded", f"{scenario.shares_traded:,.0f}")
    t.add_row("Gross P&L", _dollars(scenario.pnl_dollars))
    t.add_row("P&L %", _pct(scenario.pnl_pct))
    t.add_row("Annualised Return", _pct(scenario.annualized_return_pct))
    t.add_row("Sharpe Ratio", f"{scenario.sharpe_ratio:.2f}")
    console.print(Panel(t, title="[bold]Arbitrage Scenario ($1 M)[/bold]", box=box.ROUNDED))


def print_dividend_shock(result: DividendShockResult) -> None:
    """Pretty-print a :class:`~simulators.dividend_shock.DividendShockResult`."""
    event = result.event
    stock = event.stock

    header = (
        f"[bold cyan]{stock.ticker}[/bold cyan] — {stock.name}\n"
        f"Ex-Dividend Date: [yellow]{event.ex_dividend_date}[/yellow]  |  "
        f"Payment Date: [yellow]{event.payment_date}[/yellow]  |  "
        f"Days to Ex-Div: [bold]{result.days_to_ex_div}[/bold]"
    )
    console.print(Panel(header, title="[bold]Dividend Event[/bold]", box=box.ROUNDED))

    # ── Dividend details ──────────────────────────────────────────────────── #
    div_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    div_table.add_column("Metric", style="dim")
    div_table.add_column("Value")
    div_table.add_row("Dividend per Share", f"${event.dividend_per_share:.4f}")
    div_table.add_row("Annual Dividend (DPS×freq)", f"${result.annual_dividend:.4f}")
    div_table.add_row("Frequency", f"{event.frequency}× per year")
    div_table.add_row("Dividend Yield", _pct(result.dividend_yield_pct))
    div_table.add_row("After-Tax DPS", f"${result.after_tax_dividend:.4f}")
    div_table.add_row("After-Tax Yield", _pct(result.after_tax_yield_pct))
    console.print(Panel(div_table, title="[bold]Dividend Details[/bold]", box=box.ROUNDED))

    # ── Ex-div price drop ─────────────────────────────────────────────────── #
    pd_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    pd_table.add_column("Metric", style="dim")
    pd_table.add_column("Value")
    pd_table.add_row("Pre-Ex-Div Price", f"${stock.price:,.2f}")
    pd_table.add_row("Theoretical Price Drop", _dollars(-result.price_drop_dollars))
    pd_table.add_row("Price Drop %", _pct(-result.price_drop_pct))
    pd_table.add_row(
        "Theoretical Ex-Div Price",
        f"[bold]${result.theoretical_ex_div_price:,.2f}[/bold]",
    )
    console.print(Panel(pd_table, title="[bold]Ex-Dividend Price Drop[/bold]", box=box.ROUNDED))

    # ── Total return & DDM ────────────────────────────────────────────────── #
    ret_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    ret_table.add_column("Metric", style="dim")
    ret_table.add_column("Value")
    ret_table.add_row("Expected Capital Return", _pct(result.capital_return_pct))
    ret_table.add_row("Expected Income Return", _pct(result.income_return_pct))
    ret_table.add_row("Expected Total Return", _pct(result.total_return_pct))
    ret_table.add_row("DDM Fair Value (GGM)", f"${result.ddm_fair_value:,.2f}")
    ddm_colour = _RED if result.ddm_implied_return == "overvalued" else _GREEN
    ret_table.add_row(
        "DDM Signal",
        Text(result.ddm_implied_return.upper(), style=ddm_colour),
    )
    console.print(Panel(ret_table, title="[bold]Return Analysis & Valuation[/bold]", box=box.ROUNDED))


def print_capture_result(result: CaptureResult) -> None:
    """Pretty-print a :class:`~simulators.dividend_shock.CaptureResult`."""
    profitability = (
        Text("✔ PROFITABLE", style=_GREEN)
        if result.is_profitable
        else Text("✘ LOSS-MAKING", style=_RED)
    )

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t.add_column("Metric", style="dim")
    t.add_column("Value")
    t.add_row("Buy Price", f"${result.buy_price:,.4f}")
    t.add_row("Sell Price (ex-div)", f"${result.sell_price:,.4f}")
    t.add_row("After-Tax Dividend Received", f"${result.dividend_received:,.4f}")
    t.add_row("Transaction Costs", f"${result.transaction_cost_dollars:,.4f}")
    t.add_row("Gross P&L", _dollars(result.gross_pnl))
    t.add_row("Net P&L", _dollars(result.net_pnl))
    t.add_row("P&L %", _pct(result.pnl_pct))
    t.add_row("Annualised Return", _pct(result.annualized_return_pct))
    t.add_row("Break-Even Max Drop", _pct(result.break_even_price_drop_pct))
    t.add_row("Strategy Verdict", profitability)
    console.print(Panel(t, title="[bold]Dividend Capture Strategy[/bold]", box=box.ROUNDED))


def print_drip_table(rows: List[dict]) -> None:
    """Pretty-print a DRIP projection table."""
    t = Table(
        title="Dividend Reinvestment Plan Projection",
        box=box.ROUNDED,
        show_lines=False,
    )
    t.add_column("Year", justify="right", style="bold cyan")
    t.add_column("Shares", justify="right")
    t.add_column("Price ($)", justify="right")
    t.add_column("Total Value ($)", justify="right", style="bold green")
    t.add_column("Annual Div. Income ($)", justify="right")
    t.add_column("Cumulative Divs. ($)", justify="right")

    for row in rows:
        t.add_row(
            str(row["year"]),
            f"{row['shares']:,.4f}",
            f"{row['price']:,.2f}",
            f"{row['total_value']:,.2f}",
            f"{row['annual_dividend_income']:,.2f}",
            f"{row['cumulative_dividends']:,.2f}",
        )
    console.print(t)
