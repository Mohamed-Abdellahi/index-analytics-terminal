# =============================================================================
# pages/dividend_shock.py — Page 2: Dividend Shock Simulator
# layout() returns the page layout
# register(app) registers all callbacks — called from app.py
# =============================================================================

from dash import html, dcc, Input, Output, State
import plotly.graph_objects as go
import numpy as np

from shared import (
    A, G, R, GR, CA, BO,
    INPUT_STYLE, BTN_STYLE,
    df_g, prices_g, spot_g, days_g, expiry_g,
    fmt, parse_num, result_row, kpi_card, page_footer,
    build_drag_chart, compute_dividend_drag, compute_fair_value,
)
from data.index_math import simulate_dividend_shock, NIFTY_LOT_SIZE


def layout():
    spot   = spot_g
    days   = days_g
    df     = df_g
    expiry = expiry_g

    symbols = df.index.tolist()
    options = [{"label": f"{s}  —  {df.loc[s,'name']}", "value": s} for s in symbols]
    top15   = df.sort_values("weight_pct", ascending=False).head(15)

    div_rows = [html.Div([
        html.Span("SYMBOL", style={"color":A,"fontSize":"0.6rem","width":"110px","display":"inline-block"}),
        html.Span("WT%",    style={"color":A,"fontSize":"0.6rem","width":"52px","display":"inline-block","textAlign":"right"}),
        html.Span("DIV%",   style={"color":A,"fontSize":"0.6rem","width":"72px","display":"inline-block","textAlign":"right"}),
    ], style={"display":"flex","gap":"8px","paddingBottom":"5px",
              "borderBottom":f"1px solid {A}","marginBottom":"3px"})]

    for sym, row in top15.iterrows():
        div_rows.append(html.Div([
            html.Span(sym,                         style={"color":A,"fontSize":"0.75rem","width":"110px"}),
            html.Span(f"{row['weight_pct']:.2f}%", style={"color":GR,"fontSize":"0.7rem","width":"52px","textAlign":"right"}),
            dcc.Input(
                id={"type":"d-div","index":sym}, type="number",
                value=round(row["div_yield"],2), step=0.05,
                style={"width":"72px","textAlign":"right","background":CA,
                       "border":f"1px solid {BO}","color":A,
                       "fontFamily":"IBM Plex Mono","fontSize":"0.78rem","padding":"2px 5px"},
            ),
            html.Span("%", style={"color":GR,"fontSize":"0.7rem"}),
        ], style={"display":"flex","alignItems":"center","gap":"8px",
                  "padding":"4px 0","borderBottom":f"1px solid {BO}"}))

    return html.Div([
        html.H1("DIVIDEND SHOCK SIMULATOR", className="page-title"),
        html.P("Simulate dividend changes — per constituent or global", className="page-subtitle"),

        html.Div([
            kpi_card("NIFTY SPOT",     fmt(spot)),
            kpi_card("DAYS TO EXPIRY", str(days), expiry.strftime("%d %b %Y")),
            kpi_card("LOT SIZE",       "75 units", "per contract"),
            kpi_card("CONTRACT VALUE", fmt(spot*NIFTY_LOT_SIZE/100000, 1, suf=" L"), "₹ lakhs"),
        ], style={"display":"grid","gridTemplateColumns":"repeat(4,1fr)",
                  "gap":"1px","marginBottom":"1.5rem","border":f"1px solid {A}"}),

        html.Div([
            html.Div([
                html.P("SINGLE STOCK SHOCK", className="section-label"),
                html.Label("Select stock", className="input-label"),
                dcc.Dropdown(id="d-stock", options=options, value=symbols[0],
                             clearable=False, style={"marginBottom":"0.8rem"}),
                html.Div(id="d-cur-yield", style={"marginBottom":"0.8rem"}),
                html.Label("Shocked yield (%)", className="input-label"),
                dcc.Input(id="d-shocked", type="number", value=2.0, step=0.1, style=INPUT_STYLE),
                html.Label("Futures Price", className="input-label"),
                dcc.Input(id="d-futures", type="number", value=round(spot), step=0.05, style=INPUT_STYLE),
                html.Label("Risk-Free Rate (%)", className="input-label"),
                dcc.Input(id="d-rfr", type="number", value=6.5, step=0.05, style=INPUT_STYLE),
                html.Button("RUN SHOCK →", id="d-btn", n_clicks=0, style=BTN_STYLE),
                html.Div(id="d-results", style={"marginTop":"1rem"}),
            ], style={"flex":"0 0 270px"}),

            html.Div([
                html.P("CONSTITUENT DIV YIELDS — EDIT & RECALCULATE", className="section-label"),
                html.Div(div_rows, style={"background":CA,"border":f"1px solid {BO}",
                                          "padding":"0.8rem","overflowY":"auto","maxHeight":"500px"}),
                html.Div("Remaining 35 stocks use loaded yields",
                         style={"color":"#3A3A3A","fontSize":"0.6rem","marginTop":"6px"}),
                html.Button("RECALCULATE WITH CUSTOM YIELDS →", id="d-custom-btn", n_clicks=0,
                            style={**BTN_STYLE,"marginTop":"0.8rem","fontSize":"0.68rem"}),
                html.Div(id="d-custom-results", style={"marginTop":"1rem"}),
            ], style={"flex":"0 0 280px","paddingLeft":"1.5rem","paddingRight":"1.5rem"}),

            html.Div([
                html.P("DIVIDEND DRAG — TOP CONTRIBUTORS", className="section-label"),
                html.Div(dcc.Graph(id="d-drag", figure=build_drag_chart(df, spot, days),
                                   config={"displayModeBar":False}),
                         style={"backgroundColor":"#000000"}),
                html.P("SENSITIVITY — SHOCKED YIELD vs FV DELTA", className="section-label"),
                html.Div(dcc.Graph(id="d-sensi",
                                   figure=go.Figure(layout={"paper_bgcolor":"#000000",
                                                            "plot_bgcolor":"#000000","height":240}),
                                   config={"displayModeBar":False}),
                         style={"backgroundColor":"#000000"}),
            ], style={"flex":"1","minWidth":"0"}),
        ], style={"display":"flex","alignItems":"flex-start"}),

        page_footer(f"Expiry: {expiry.strftime('%d %b %Y').upper()} · Lot: {NIFTY_LOT_SIZE} units"),
    ], className="page-container")


def register(app):
    """Register all callbacks for this page. Called from app.py."""
    import dash

    @app.callback(
        Output("d-cur-yield", "children"),
        Input("d-stock",      "value"),
    )
    def show_yield(symbol):
        if not symbol or symbol not in df_g.index: return ""
        row = df_g.loc[symbol]
        return html.Div([
            html.Span("Current yield: ", style={"color":GR,"fontSize":"0.72rem"}),
            html.Span(f"{row['div_yield']:.2f}%", style={"color":A,"fontSize":"0.72rem","fontWeight":"600"}),
            html.Span(f"  ·  Weight: {row['weight_pct']:.2f}%", style={"color":GR,"fontSize":"0.72rem"}),
        ])

    @app.callback(
        Output("d-results", "children"),
        Output("d-drag",    "figure"),
        Output("d-sensi",   "figure"),
        Input("d-btn",      "n_clicks"),
        State("d-stock",    "value"),
        State("d-shocked",  "value"),
        State("d-futures",  "value"),
        State("d-rfr",      "value"),
        prevent_initial_call=True,
    )
    def shock_calc(n, symbol, shocked_yield, futures_price, rfr):
        print(f">>> SHOCK CALC: symbol={symbol}, shocked={shocked_yield}")
        spot   = spot_g
        days   = days_g
        df     = df_g
        prices = prices_g

        rfr_dec = parse_num(rfr, 6.5) / 100.0
        futures = parse_num(futures_price, float(round(spot)))
        sy      = parse_num(shocked_yield, 2.0)

        result = simulate_dividend_shock(
            symbol=symbol, shocked_div_yield=sy,
            df=df, prices=prices,
            index_level=spot, days_to_expiry=days,
            market_futures=futures, risk_free_rate=rfr_dec,
        )

        dc = "result-pos" if result.delta_fair_value > 0 else "result-neg"
        lc = "result-pos" if result.delta_per_lot    > 0 else "result-neg"

        results = html.Div([
            result_row("Stock",      result.stock_name, "result-amb"),
            result_row("Weight",     f"{result.weight_pct:.2f}%"),
            result_row("Div yield",  f"{result.base_div_yield:.2f}% → {sy:.2f}%"),
            result_row("Drag Δ",     f"{result.delta_div_points:+.4f} pts", dc),
            result_row("FV before",  fmt(result.base_fair_value)),
            result_row("FV after",   fmt(result.shocked_fair_value)),
            result_row("FV Δ",       f"{result.delta_fair_value:+.2f} pts", dc),
            result_row("P&L / lot",  f"₹{result.delta_per_lot:+,.0f}", lc),
        ], className="result-box")

        drag_fig = build_drag_chart(df, spot, days, symbol)

        yields    = np.linspace(0, 15, 80)
        base_drag = compute_dividend_drag(df, prices, spot, days)
        base_fv   = compute_fair_value(spot, days, base_drag, futures, rfr_dec)
        deltas    = [
            compute_fair_value(spot, days,
                               compute_dividend_drag(df, prices, spot, days, overrides={symbol:y}),
                               futures, rfr_dec).fair_value - base_fv.fair_value
            for y in yields
        ]

        cur = df.loc[symbol, "div_yield"] if symbol in df.index else 0
        sf  = go.Figure()
        sf.add_trace(go.Scatter(x=list(yields), y=deltas, mode="lines",
                                line=dict(color=A, width=2), fill="tozeroy",
                                fillcolor="rgba(255,153,0,0.05)"))
        sf.add_vline(x=cur, line_dash="dash", line_color="rgba(136,136,136,0.5)",
                     annotation_text=f"CUR {cur:.2f}%",
                     annotation_font=dict(color=GR, size=10, family="IBM Plex Mono"))
        sf.add_vline(x=sy, line_dash="solid", line_color="rgba(255,51,51,0.6)",
                     annotation_text=f"SHOCK {sy:.1f}%",
                     annotation_font=dict(color=R, size=10, family="IBM Plex Mono"))
        sf.add_hline(y=0, line_color=BO, line_width=1)
        sf.update_layout(
            paper_bgcolor="#000000", plot_bgcolor="#000000",
            font=dict(family="IBM Plex Mono", color=A, size=11),
            height=240, margin=dict(l=10, r=20, t=10, b=30),
            xaxis=dict(showgrid=False, ticksuffix="%", tickfont=dict(size=10, color=GR)),
            yaxis=dict(showgrid=True, gridcolor=BO, ticksuffix=" pts",
                       tickfont=dict(size=10, color=GR)),
            showlegend=False,
        )
        return results, drag_fig, sf

    @app.callback(
        Output("d-custom-results", "children"),
        Input("d-custom-btn",      "n_clicks"),
        State({"type":"d-div","index":dash.ALL}, "value"),
        State({"type":"d-div","index":dash.ALL}, "id"),
        State("d-futures",         "value"),
        State("d-rfr",             "value"),
        prevent_initial_call=True,
    )
    def custom_yields(n, div_values, div_ids, futures_price, rfr):
        print(f">>> CUSTOM YIELDS: n={n}")
        spot   = spot_g
        days   = days_g
        df     = df_g
        prices = prices_g

        rfr_dec   = parse_num(rfr, 6.5) / 100.0
        futures   = parse_num(futures_price, float(round(spot)))
        overrides = {id_d["index"]: float(v) for id_d, v in zip(div_ids, div_values) if v is not None}

        base_drag = compute_dividend_drag(df, prices, spot, days)
        cust_drag = compute_dividend_drag(df, prices, spot, days, overrides=overrides)
        base_fv   = compute_fair_value(spot, days, base_drag, futures, rfr_dec)
        cust_fv   = compute_fair_value(spot, days, cust_drag, futures, rfr_dec)
        delta     = cust_fv.fair_value - base_fv.fair_value
        dc        = "result-pos" if delta >= 0 else "result-neg"

        return html.Div([
            result_row("Base FV",   fmt(base_fv.fair_value)),
            result_row("Custom FV", fmt(cust_fv.fair_value)),
            result_row("FV Δ",      f"{delta:+.2f} pts", dc),
            result_row("P&L / lot", f"₹{delta*NIFTY_LOT_SIZE:+,.0f}", dc),
        ], className="result-box")