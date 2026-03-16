"""Command-line interface for the Index Analytics Terminal.

Entry point: ``iat``

Subcommands
-----------
``iat rebalance``
    Simulate an index rebalancing event (addition or removal of a stock).

``iat dividend``
    Simulate a dividend shock: ex-div price drop, capture strategy, DRIP.

``iat demo``
    Run a built-in demonstration using realistic fictional data.

Usage examples
--------------
.. code-block:: console

    # Simulate adding a stock to an index
    iat rebalance --ticker ACME --price 150 --shares-out 1000 --adv 5 \\
                  --name "Acme Corp" --action ADD \\
                  --index-name "S&P 500" --index-aum 5000 \\
                  --new-weight 0.01 \\
                  --announce 2024-01-15 --effective 2024-01-31

    # Simulate a dividend shock
    iat dividend --ticker ACME --price 150 --shares-out 1000 --adv 5 \\
                 --name "Acme Corp" --dividend 0.75 \\
                 --ex-div 2024-02-15

    # Run the built-in demo
    iat demo
"""

from __future__ import annotations

from datetime import date

import click

from .display import (
    print_banner,
    print_rebalancing_impact,
    print_arbitrage_scenario,
    print_dividend_shock,
    print_capture_result,
    print_drip_table,
)
from .models import Index, IndexConstituent, Stock
from .simulators import (
    DividendEvent,
    DividendShockSimulator,
    RebalancingEvent,
    RebalancingSimulator,
)


# ---------------------------------------------------------------------------
# Shared option decorators
# ---------------------------------------------------------------------------


def _stock_options(f):
    """Decorate *f* with options that describe a stock."""
    decorators = [
        click.option("--ticker", required=True, help="Ticker symbol (e.g. AAPL)."),
        click.option("--name", default="", show_default=False, help="Company name."),
        click.option(
            "--price",
            type=float,
            required=True,
            help="Current stock price (USD).",
        ),
        click.option(
            "--shares-out",
            type=float,
            required=True,
            help="Shares outstanding in millions.",
        ),
        click.option(
            "--adv",
            type=float,
            required=True,
            help="Average daily volume in millions of shares.",
        ),
        click.option("--sector", default="Unknown", help="GICS sector."),
        click.option(
            "--beta", type=float, default=1.0, show_default=True, help="Market beta."
        ),
        click.option(
            "--volatility",
            type=float,
            default=0.20,
            show_default=True,
            help="Annualised volatility (0–1).",
        ),
    ]
    for d in reversed(decorators):
        f = d(f)
    return f


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option("1.0.0", prog_name="iat")
def main() -> None:
    """Index Analytics Terminal — simulate index rebalancing effects and dividend shocks."""
    print_banner()


# ---------------------------------------------------------------------------
# `rebalance` subcommand
# ---------------------------------------------------------------------------


@main.command()
@_stock_options
@click.option(
    "--action",
    type=click.Choice(["ADD", "REMOVE"], case_sensitive=False),
    required=True,
    help="Whether the stock is being added to or removed from the index.",
)
@click.option("--index-name", default="S&P 500", show_default=True, help="Index name.")
@click.option(
    "--index-aum",
    type=float,
    default=5000.0,
    show_default=True,
    help="Aggregate tracking-fund AUM in billions USD.",
)
@click.option(
    "--new-weight",
    type=float,
    default=0.005,
    show_default=True,
    help="Target weight in the index [0–1].  Use 0 for a removal.",
)
@click.option(
    "--old-weight",
    type=float,
    default=0.0,
    show_default=True,
    help="Current weight in the index [0–1].  Use 0 for a fresh addition.",
)
@click.option(
    "--announce",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    required=True,
    help="Announcement date (YYYY-MM-DD).",
)
@click.option(
    "--effective",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    required=True,
    help="Effective date (YYYY-MM-DD).",
)
@click.option(
    "--position",
    type=float,
    default=1.0,
    show_default=True,
    help="Arbitrage position size in millions USD.",
)
@click.option(
    "--tx-cost",
    type=float,
    default=5.0,
    show_default=True,
    help="One-way transaction cost in basis points.",
)
def rebalance(
    ticker, name, price, shares_out, adv, sector, beta, volatility,
    action, index_name, index_aum, new_weight, old_weight,
    announce, effective, position, tx_cost,
) -> None:
    """Simulate an index rebalancing event (addition or removal)."""
    stock = Stock(
        ticker=ticker.upper(),
        name=name or ticker.upper(),
        price=price,
        shares_outstanding=shares_out,
        adv=adv,
        sector=sector,
        beta=beta,
        volatility=volatility,
    )
    index = Index(name=index_name, ticker="IDX", total_aum=index_aum)

    event = RebalancingEvent(
        action=action.upper(),
        stock=stock,
        index=index,
        announcement_date=announce.date(),
        effective_date=effective.date(),
        new_weight=new_weight,
        old_weight=old_weight,
    )

    simulator = RebalancingSimulator()
    impact = simulator.simulate(event)
    print_rebalancing_impact(impact)

    scenario = simulator.simulate_arbitrage_scenario(
        event,
        impact,
        position_size_dollars=position * 1_000_000,
        transaction_cost_bps=tx_cost,
    )
    print_arbitrage_scenario(scenario, position)


# ---------------------------------------------------------------------------
# `dividend` subcommand
# ---------------------------------------------------------------------------


@main.command()
@_stock_options
@click.option(
    "--dividend",
    "dividend_per_share",
    type=float,
    required=True,
    help="Dividend per share in USD.",
)
@click.option(
    "--ex-div",
    "ex_div_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    required=True,
    help="Ex-dividend date (YYYY-MM-DD).",
)
@click.option(
    "--declaration",
    "declaration_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Declaration date (YYYY-MM-DD).  Defaults to 14 days before ex-div.",
)
@click.option(
    "--frequency",
    type=int,
    default=4,
    show_default=True,
    help="Number of dividend payments per year.",
)
@click.option(
    "--div-tax",
    type=float,
    default=0.15,
    show_default=True,
    help="Marginal dividend tax rate (0–1).",
)
@click.option(
    "--cg-tax",
    type=float,
    default=0.20,
    show_default=True,
    help="Marginal capital-gains tax rate (0–1).",
)
@click.option(
    "--tx-cost",
    type=float,
    default=10.0,
    show_default=True,
    help="Round-trip transaction cost in basis points for the capture strategy.",
)
@click.option(
    "--drip-years",
    type=int,
    default=10,
    show_default=True,
    help="Projection horizon (years) for the DRIP analysis.",
)
@click.option(
    "--no-capture",
    is_flag=True,
    default=False,
    help="Skip the dividend-capture strategy simulation.",
)
@click.option(
    "--no-drip",
    is_flag=True,
    default=False,
    help="Skip the DRIP projection.",
)
def dividend(
    ticker, name, price, shares_out, adv, sector, beta, volatility,
    dividend_per_share, ex_div_date, declaration_date, frequency,
    div_tax, cg_tax, tx_cost, drip_years, no_capture, no_drip,
) -> None:
    """Simulate a dividend shock, capture strategy, and DRIP projection."""
    stock = Stock(
        ticker=ticker.upper(),
        name=name or ticker.upper(),
        price=price,
        shares_outstanding=shares_out,
        adv=adv,
        sector=sector,
        beta=beta,
        volatility=volatility,
    )

    ex_date = ex_div_date.date()
    from datetime import timedelta
    decl_date = declaration_date.date() if declaration_date else ex_date - timedelta(days=14)

    event = DividendEvent(
        stock=stock,
        dividend_per_share=dividend_per_share,
        declaration_date=decl_date,
        ex_dividend_date=ex_date,
        frequency=frequency,
    )

    sim = DividendShockSimulator(
        dividend_tax_rate=div_tax,
        capital_gains_tax_rate=cg_tax,
    )

    result = sim.simulate(event)
    print_dividend_shock(result)

    if not no_capture:
        capture = sim.simulate_capture(event, transaction_cost_bps=tx_cost)
        print_capture_result(capture)

    if not no_drip:
        drip = sim.dividend_reinvestment_plan(event, years=drip_years)
        print_drip_table(drip)


# ---------------------------------------------------------------------------
# `demo` subcommand
# ---------------------------------------------------------------------------


@main.command()
def demo() -> None:
    """Run a built-in demonstration with realistic fictional data."""
    from datetime import date as _date

    click.echo()
    click.secho("━━━ DEMO 1: Index Rebalancing ━━━", bold=True)
    click.echo()

    # Stock: fictional "TechCore Inc"
    techcore = Stock(
        ticker="TCRX",
        name="TechCore Inc",
        price=245.60,
        shares_outstanding=800.0,  # 800 M shares → ~$196 B market cap
        adv=4.5,                   # 4.5 M shares/day
        sector="Information Technology",
        beta=1.35,
        volatility=0.28,
    )

    # Index: fictional "Global 500" with $4 T of tracking AUM
    global500 = Index(
        name="Global 500",
        ticker="G500",
        total_aum=4_000.0,  # $4 T
    )
    # Pre-populate with an existing constituent to show weight redistribution
    existing = Stock(
        ticker="ALPH",
        name="Alpha Industries",
        price=310.00,
        shares_outstanding=600.0,
        adv=3.0,
        sector="Financials",
        beta=0.9,
        volatility=0.18,
    )
    global500.add_constituent(existing, weight=0.01)

    rebalance_event = RebalancingEvent(
        action="ADD",
        stock=techcore,
        index=global500,
        announcement_date=_date(2024, 3, 1),
        effective_date=_date(2024, 3, 22),
        new_weight=0.008,
        old_weight=0.0,
    )

    sim = RebalancingSimulator()
    impact = sim.simulate(rebalance_event)
    print_rebalancing_impact(impact)

    arb = sim.simulate_arbitrage_scenario(
        rebalance_event, impact, position_size_dollars=2_000_000
    )
    print_arbitrage_scenario(arb, position_m=2.0)

    # ── Demo 2: Dividend shock ──────────────────────────────────────────── #
    click.echo()
    click.secho("━━━ DEMO 2: Dividend Shock ━━━", bold=True)
    click.echo()

    div_stock = Stock(
        ticker="DIVI",
        name="Dividend Aristocrat Corp",
        price=82.40,
        shares_outstanding=500.0,
        adv=2.0,
        sector="Consumer Staples",
        beta=0.65,
        volatility=0.14,
    )

    div_event = DividendEvent(
        stock=div_stock,
        dividend_per_share=0.68,
        declaration_date=_date(2024, 4, 1),
        ex_dividend_date=_date(2024, 4, 15),
        frequency=4,
    )

    div_sim = DividendShockSimulator(
        dividend_tax_rate=0.15,
        capital_gains_tax_rate=0.20,
        reference_date=_date(2024, 4, 1),
    )

    div_result = div_sim.simulate(div_event)
    print_dividend_shock(div_result)

    capture = div_sim.simulate_capture(div_event, transaction_cost_bps=8.0)
    print_capture_result(capture)

    drip = div_sim.dividend_reinvestment_plan(div_event, years=10)
    print_drip_table(drip)
