# =============================================================================
# pages/info.py
# Static information page — Nifty 50 methodology, rules, formulas
# No callbacks, no live data — purely educational
# =============================================================================

import dash
from dash import html
from datetime import datetime

#dash.register_page(__name__, path="/info", name="Methodology", order=4)


def layout():
    return html.Div([

        # ── Page header ───────────────────────────────────────────────────────
        html.Div([
            html.H1("Nifty 50 — Index Methodology", className="page-title"),
            html.P(
                "Structure · Rebalancing Rules · Fair Value Mechanics · Delta One Context",
                className="page-subtitle"
            ),
        ]),

        # ── Alert ─────────────────────────────────────────────────────────────
        html.Div([
            "This page documents the exact NSE methodology underlying all simulations. "
            "All formulas and rules are sourced from the NSE Index Methodology document "
            "and the NSE F&O product specifications."
        ], className="alert-box"),

        # ── Section 1: Index Structure ────────────────────────────────────────
        html.P("01 · Index Structure", className="section-label"),

        html.Div([
            html.H4("What is the Nifty 50?"),
            html.P(
                "The Nifty 50 is a free-float market capitalisation-weighted index of the 50 largest "
                "and most liquid stocks listed on the National Stock Exchange of India (NSE). "
                "It represents approximately 65% of the total float-adjusted market capitalisation "
                "of all NSE-listed equities."
            ),
            html.Br(),
            html.P("Key structural parameters:"),
            html.Ul([
                html.Li("Base date: November 3, 1995 | Base value: 1,000 points"),
                html.Li("Base capital: ₹2.06 trillion (fixed — adjusted only by NSE for continuity)"),
                html.Li("Index type: Price Return — dividends are NOT reinvested"),
                html.Li("Weighting: Free-float market cap weighted (not total market cap)"),
                html.Li("Single stock weight cap: 33% of index at rebalancing"),
                html.Li("Top-3 combined weight cap: 62% of index at rebalancing"),
            ]),
        ], className="info-block"),

        html.Div([
            html.H4("Index Level Formula"),
            html.P("The Nifty 50 level is computed as:"),
            html.Div(
                "Index Level = Σ (Price_i × Shares_FF_i × IWF_i) / Divisor",
                className="formula-box"
            ),
            html.P("Where:"),
            html.Ul([
                html.Li("Price_i = last traded price of constituent i"),
                html.Li("Shares_FF_i = free-float shares outstanding (millions)"),
                html.Li("IWF_i = Investable Weight Factor = free-float shares / total shares outstanding"),
                html.Li("Divisor = adjusted base market capital (NSE maintains this; adjusted on every corporate action)"),
            ]),
            html.Br(),
            html.P(
                "The Divisor is the key continuity mechanism. Every time a corporate action occurs "
                "(stock split, bonus issue, rights issue, constituent change), NSE adjusts the Divisor "
                "so that the index level does not jump artificially. This is what makes the index "
                "a continuous, tradeable reference — and what Delta One desks model precisely "
                "around rebalancing events."
            ),
        ], className="info-block"),

        # ── Section 2: Rebalancing Rules ──────────────────────────────────────
        html.P("02 · Rebalancing Rules", className="section-label"),

        html.Div([
            html.H4("Semi-Annual Rebalancing Calendar"),
            html.Ul([
                html.Li("Frequency: Twice per year (semi-annual)"),
                html.Li("Data cut-off dates: January 31 and July 31"),
                html.Li("Data window: 6 months prior to each cut-off date"),
                html.Li("Advance notice: 4 weeks before implementation"),
                html.Li([
                    "Implementation: ",
                    html.Strong("First trading day after the March and September F&O expiry"),
                    " — this is the exact day passive trackers must trade"
                ]),
            ]),
        ], className="info-block"),

        html.Div([
            html.H4("Eligibility Criteria"),
            html.P("For a stock to be eligible for Nifty 50 inclusion:"),
            html.Ul([
                html.Li("Must be listed on NSE and part of the Nifty 500 universe"),
                html.Li("Must be available for trading in the F&O segment"),
                html.Li(
                    "Impact cost ≤ 0.50% on 90% of observations over the past 6 months "
                    "(measured on a ₹100 million basket)"
                ),
                html.Li("Free-float market cap ≥ 1.5× that of the smallest current Nifty 50 constituent"),
                html.Li("Minimum 1 month listing history on NSE"),
                html.Li("Must not be under any regulatory action or trading suspension"),
            ]),
        ], className="info-block"),

        html.Div([
            html.H4("Why This Matters for Delta One"),
            html.P(
                "The 4-week advance notice creates a well-defined trading window. "
                "Passive funds (ETFs, index funds) tracking the Nifty 50 collectively manage "
                "approximately ₹2,500+ billion in AUM. On implementation day, they must "
                "simultaneously sell the outgoing stock and buy the incoming stock in proportion "
                "to their AUM. This creates predictable, large, price-insensitive flows that "
                "Delta One desks model and position around."
            ),
            html.Br(),
            html.P(
                "The Rebalancing Simulator in this tool computes exactly these flows — "
                "how many shares need to change hands, at what value, and what the implied "
                "impact on the futures fair value is."
            ),
        ], className="info-block"),

        # ── Section 3: Futures Fair Value ─────────────────────────────────────
        html.P("03 · Futures Fair Value & Basis", className="section-label"),

        html.Div([
            html.H4("Fair Value Formula"),
            html.P("The theoretical price of the Nifty 50 near-month futures contract is:"),
            html.Div(
                "Fair Value = Spot × [1 + rf × (T / 365)] − Dividend Drag",
                className="formula-box"
            ),
            html.P("Where:"),
            html.Ul([
                html.Li("Spot = current Nifty 50 index level"),
                html.Li("rf = annualized risk-free rate (proxy: RBI repo rate or 91-day T-bill yield)"),
                html.Li("T = calendar days to futures expiry"),
                html.Li("Dividend Drag = present value of expected dividends from all constituents before expiry"),
            ]),
        ], className="info-block"),

        html.Div([
            html.H4("Dividend Drag — The Core Mechanism"),
            html.P(
                "Because Nifty 50 is a Price Return Index, dividends are not reinvested. "
                "When a constituent pays a dividend, its stock price drops by the dividend amount "
                "on the ex-date, which reduces the index level. The futures contract had already "
                "priced in this expected dividend — so the futures trades at a structural discount "
                "to the carry price by exactly the dividend drag amount."
            ),
            html.Div(
                "Drag_i = Index_Level × (weight_i / 100) × (div_yield_i / 100) × (T / 365)",
                className="formula-box"
            ),
            html.Div(
                "Total Drag = Σ Drag_i  (summed over all 50 constituents)",
                className="formula-box"
            ),
            html.Br(),
            html.P(
                "The Dividend Shock Simulator allows you to override the expected dividend yield "
                "of any constituent and immediately see the impact on the futures fair value and "
                "the P&L per contract. This is the exact calculation a Delta One trader runs when "
                "a company announces an unexpected special dividend or a dividend cut."
            ),
        ], className="info-block"),

        html.Div([
            html.H4("Basis and Arbitrage"),
            html.Div(
                "Basis = Market Futures Price − Fair Value",
                className="formula-box"
            ),
            html.Div(
                "Basis (annualized %) = (Basis / Spot) × (365 / T) × 100",
                className="formula-box"
            ),
            html.P("Interpreting the basis:"),
            html.Ul([
                html.Li(
                    "Positive basis (futures rich): futures trade above fair value. "
                    "Arb: buy spot basket, sell futures. "
                    "Common when market is in strong uptrend and retail buys futures."
                ),
                html.Li(
                    "Negative basis (futures cheap): futures trade below fair value. "
                    "Arb: sell spot basket, buy futures. "
                    "Common during risk-off periods and FII selling."
                ),
                html.Li(
                    "The basis converges to zero at expiry — this is the fundamental "
                    "constraint that makes index arbitrage riskless in theory."
                ),
            ]),
        ], className="info-block"),

        # ── Section 4: Corporate Actions ──────────────────────────────────────
        html.P("04 · Corporate Actions & Divisor Adjustments", className="section-label"),

        html.Div([
            html.H4("Ordinary vs Special Dividends"),
            html.Ul([
                html.Li([
                    html.Strong("Ordinary dividends: "),
                    "NSE does NOT adjust the index divisor. The dividend is expected by the market "
                    "and already reflected in the futures price via the dividend drag. "
                    "On ex-date, the stock price drops and so does the index — no discontinuity adjustment needed."
                ]),
                html.Li([
                    html.Strong("Special dividends: "),
                    "NSE DOES adjust the index divisor. A special dividend is by definition unexpected "
                    "and not priced into the futures. NSE adjusts the divisor so the index level "
                    "remains continuous, but the futures price must immediately re-price "
                    "to reflect the new (higher) dividend drag."
                ]),
            ]),
            html.Br(),
            html.P(
                "This distinction is critical for the Dividend Shock Simulator — "
                "when you shock a dividend yield upward, you are modelling what happens "
                "when the market re-prices expected dividends (e.g. after a special dividend announcement). "
                "The futures fair value drops, and a trader who is long futures faces an immediate mark-to-market loss."
            ),
        ], className="info-block"),

        # ── Section 5: F&O Specifications ─────────────────────────────────────
        html.P("05 · Nifty 50 F&O Specifications", className="section-label"),

        html.Div([
            html.H4("Contract Specifications"),
            html.Ul([
                html.Li("Underlying: Nifty 50 Index"),
                html.Li("Lot size: 75 units per contract"),
                html.Li("Contract value: 75 × Index Level (e.g. at 23,151 → ₹17.36 lakh per contract)"),
                html.Li("Expiry: Last Thursday of each month (adjusted for NSE holidays)"),
                html.Li("Series: Near month, mid month, far month (3 monthly contracts)"),
                html.Li("Settlement: Cash-settled at final settlement price (closing value on expiry day)"),
                html.Li("Tick size: 0.05 index points = ₹3.75 per contract"),
                html.Li("Trading hours: 09:15 – 15:30 IST (regular) | 15:30 – 23:30 IST (evening session)"),
            ]),
        ], className="info-block"),

        # ── Footer ────────────────────────────────────────────────────────────
        html.Div([
            html.Span("Sources: NSE Index Methodology Document · NSE F&O Product Note · RBI · PPAC"),
            html.Span(f"Last updated: {datetime.today().strftime('%B %d, %Y')}"),
        ], className="footer"),

    ], className="page-container")
