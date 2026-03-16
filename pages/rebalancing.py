# =============================================================================
# pages/rebalancing.py — Page 3: Constituent Swap Simulator
# =============================================================================

import dash
from dash import html, dcc, Input, Output, State
import plotly.graph_objects as go
import pandas as pd

from data.constituents import get_constituent_df, get_prices_dict, CANDIDATE_ADDITIONS
from data.futures import get_nifty_spot, get_days_to_expiry, get_expiry_dates
from data.index_math import simulate_constituent_swap
from components.footer import make_footer

dash.register_page(__name__, path="/rebalancing", name="Rebalancing", order=3)

A  = "#FF9900"
G  = "#00CC44"
R  = "#FF3333"
GR = "#888888"
BG = "#000000"
CA = "#111111"
BO = "#2A2A2A"


def fmt(v, d=2, pre="", suf=""):
    if v is None: return "—"
    return f"{pre}{v:,.{d}f}{suf}"


def layout():
    df     = get_constituent_df()
    prices = get_prices_dict()
    spot   = get_nifty_spot()
    days   = get_days_to_expiry()
    expiry = get_expiry_dates(1)[0]

    if df is None or not prices or not spot:
        return html.Div("⚠ Unable to fetch live data from NSE.", className="page-container")

    symbols     = df.index.tolist()
    out_options = [{"label": f"{s}  —  {df.loc[s,'name']}  ({df.loc[s,'weight_pct']:.2f}%)", "value": s} for s in symbols]
    in_options  = [{"label": f"{s}  —  {v['name']}", "value": s} for s, v in CANDIDATE_ADDITIONS.items()]

    inp_style = {"width": "100%", "marginBottom": "0.8rem"}

    return html.Div([

        html.H1("REBALANCING SIMULATOR", className="page-title"),
        html.P("Constituent swap · Weight redistribution · Tracker flows · Futures impact", className="page-subtitle"),

        # KPIs
        html.Div([
            html.Div([html.Div("NIFTY SPOT",    className="kpi-label"), html.Div(fmt(spot), className="kpi-value")], className="kpi-card"),
            html.Div([html.Div("DAYS TO EXPIRY",className="kpi-label"), html.Div(str(days), className="kpi-value"), html.Div(expiry.strftime("%d %b %Y"), className="kpi-delta-neu")], className="kpi-card"),
            html.Div([html.Div("TRACKER AUM",   className="kpi-label"), html.Div("₹2,500 bn", className="kpi-value"), html.Div("default · editable", className="kpi-delta-neu")], className="kpi-card"),
            html.Div([html.Div("NOTICE PERIOD", className="kpi-label"), html.Div("4 WEEKS",  className="kpi-value"), html.Div("NSE advance notice", className="kpi-delta-neu")], className="kpi-card"),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(4,1fr)", "gap": "1px", "marginBottom": "1.5rem", "border": f"1px solid {A}"}),

        html.Div([

            # ── LEFT: inputs ────────────────────────────────────────────────
            html.Div([
                html.P("SWAP INPUTS", className="section-label"),

                html.Label("Stock to REMOVE", className="input-label"),
                dcc.Dropdown(id="reb-out", options=out_options, value=symbols[-1],
                             clearable=False, style={"marginBottom": "0.8rem"}),

                html.Label("Stock to ADD", className="input-label"),
                dcc.Dropdown(id="reb-in", options=in_options,
                             value=list(CANDIDATE_ADDITIONS.keys())[0],
                             clearable=False, style={"marginBottom": "0.8rem"}),

                html.Label("Price of incoming stock (₹)", className="input-label"),
                dcc.Input(id="reb-price-in", type="number", value=3500, step=1, style=inp_style),

                html.Label("Div yield of incoming stock (%)", className="input-label"),
                dcc.Input(id="reb-div-in", type="number", value=0.20, step=0.05, style=inp_style),

                html.Label("Futures Price (market)", className="input-label"),
                dcc.Input(id="reb-futures", type="number", value=round(spot), step=0.05, style=inp_style),

                html.Label("Risk-Free Rate (%)", className="input-label"),
                dcc.Input(id="reb-rfr", type="number", value=6.5, step=0.05, style=inp_style),

                html.Label("Tracker AUM (₹ billion)", className="input-label"),
                dcc.Input(id="reb-aum", type="number", value=2500, step=100, style=inp_style),

                html.Button("RUN SIMULATION →", id="reb-run-btn", n_clicks=0, className="bbg-btn"),

                html.Div(id="reb-results", style={"marginTop": "1rem"}),

            ], style={"flex": "0 0 300px"}),

            # ── RIGHT: charts ────────────────────────────────────────────────
            html.Div([
                html.P("WEIGHT REDISTRIBUTION — BEFORE vs AFTER", className="section-label"),
                dcc.Graph(id="reb-weights-chart", config={"displayModeBar": False}),

                html.P("TRACKER FLOWS ON IMPLEMENTATION DAY", className="section-label"),
                dcc.Graph(id="reb-flows-chart", config={"displayModeBar": False}),
            ], style={"flex": "1", "minWidth": "0", "paddingLeft": "2rem"}),

        ], style={"display": "flex", "gap": "0", "alignItems": "flex-start"}),

        dcc.Store(id="reb-store-spot",   data=spot),
        dcc.Store(id="reb-store-days",   data=days),
        dcc.Store(id="reb-store-df",     data=df.reset_index().to_dict("records")),
        dcc.Store(id="reb-store-prices", data=prices),
        dcc.Interval(id="reb-load-trigger", interval=300, max_intervals=1),

        make_footer("Tracker AUM source: AMFI · Divisor adjusted by NSE at announcement"),

    ], className="page-container")


@dash.callback(
    Output("reb-results",      "children"),
    Output("reb-weights-chart","figure"),
    Output("reb-flows-chart",  "figure"),
    Input("reb-run-btn",       "n_clicks"),
    Input("reb-load-trigger",  "n_intervals"),
    State("reb-out",           "value"),
    State("reb-in",            "value"),
    State("reb-price-in",      "value"),
    State("reb-div-in",        "value"),
    State("reb-futures",       "value"),
    State("reb-rfr",           "value"),
    State("reb-aum",           "value"),
    State("reb-store-spot",    "data"),
    State("reb-store-days",    "data"),
    State("reb-store-df",      "data"),
    State("reb-store-prices",  "data"),
    prevent_initial_call=False,
)
def run_rebalancing(n_clicks, n_intervals, sym_out, sym_in, price_in, div_in,
                    futures_price, rfr, aum_bn,
                    spot, days, df_data, prices):

    df      = pd.DataFrame(df_data).set_index("symbol")
    rfr_dec = (rfr or 6.5) / 100.0
    futures = futures_price or spot
    price_in = price_in or 3500
    div_in   = div_in   or 0.0
    aum_bn   = aum_bn   or 2500

    result = simulate_constituent_swap(
        symbol_out=sym_out, symbol_in=sym_in,
        price_in=price_in, div_yield_in=div_in,
        df=df, prices=prices,
        index_level=spot, days_to_expiry=days,
        market_futures=futures, risk_free_rate=rfr_dec,
        tracker_aum_bn=aum_bn,
    )

    fv_cls = "result-pos" if result.delta_future_points > 0 else "result-neg"

    results = html.Div([
        html.P("SWAP RESULTS", className="section-label"),
        html.Div([
            html.Div([html.Span("Removed",       className="result-label"), html.Span(sym_out, className="result-neg")], className="result-row"),
            html.Div([html.Span("Added",          className="result-label"), html.Span(sym_in,  className="result-pos")], className="result-row"),
            html.Div([html.Span("FV before",      className="result-label"), html.Span(fmt(result.old_fair_value),           className="result-value")], className="result-row"),
            html.Div([html.Span("FV after",       className="result-label"), html.Span(fmt(result.new_fair_value),           className="result-value")], className="result-row"),
            html.Div([html.Span("FV Δ",           className="result-label"), html.Span(f"{result.delta_future_points:+.2f} pts", className=fv_cls)], className="result-row"),
        ], className="result-box"),

        html.P("TRACKER FLOWS", className="section-label"),
        html.Div([
            html.Div([html.Span(f"BUY  {sym_in}",  className="result-label"), html.Span(f"₹{result.buy_stock_in_value/1e7:,.1f} Cr  ·  {result.buy_stock_in_shares:,.0f} shares",   className="result-pos")], className="result-row"),
            html.Div([html.Span(f"SELL {sym_out}",  className="result-label"), html.Span(f"₹{result.sell_stock_out_value/1e7:,.1f} Cr  ·  {result.sell_stock_out_shares:,.0f} shares", className="result-neg")], className="result-row"),
            html.Div([html.Span("Tracker AUM",       className="result-label"), html.Span(f"₹{result.tracker_aum_bn:,.0f} bn",  className="result-value")], className="result-row"),
        ], className="result-box"),
    ])

    # ── Weights chart ─────────────────────────────────────────────────────────
    top = sorted(result.old_weights, key=lambda s: result.old_weights[s], reverse=True)[:15]
    weights_fig = go.Figure()
    weights_fig.add_trace(go.Bar(
        name="BEFORE", x=top,
        y=[result.old_weights.get(s, 0) for s in top],
        marker_color=BO, marker_line_width=0,
    ))
    weights_fig.add_trace(go.Bar(
        name="AFTER", x=top,
        y=[result.new_weights.get(s, 0) for s in top],
        marker_color=A, marker_line_width=0, opacity=0.85,
    ))
    weights_fig.update_layout(
        barmode="group",
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(family="IBM Plex Mono", color=A, size=11),
        height=300, margin=dict(l=10, r=10, t=10, b=60),
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color=GR), tickangle=-45),
        yaxis=dict(showgrid=True, gridcolor=BO, ticksuffix="%", tickfont=dict(size=10, color=GR)),
        legend=dict(font=dict(size=10, color=GR), bgcolor="rgba(0,0,0,0)"),
    )

    # ── Flows chart ───────────────────────────────────────────────────────────
    flows_fig = go.Figure(go.Bar(
        x=[sym_in, sym_out],
        y=[result.buy_stock_in_value/1e7, -result.sell_stock_out_value/1e7],
        marker_color=[G, R], marker_line_width=0,
        text=[f"₹{result.buy_stock_in_value/1e7:,.1f} Cr", f"-₹{result.sell_stock_out_value/1e7:,.1f} Cr"],
        textposition="outside",
        textfont=dict(family="IBM Plex Mono", size=13, color=A),
    ))
    flows_fig.add_hline(y=0, line_color=BO, line_width=1)
    flows_fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(family="IBM Plex Mono", color=A, size=11),
        height=220, margin=dict(l=10, r=10, t=10, b=40),
        xaxis=dict(showgrid=False, tickfont=dict(size=12, color=GR)),
        yaxis=dict(showgrid=True, gridcolor=BO, ticksuffix=" Cr", tickfont=dict(size=10, color=GR)),
        showlegend=False,
    )

    return results, weights_fig, flows_fig