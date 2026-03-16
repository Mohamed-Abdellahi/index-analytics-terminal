# =============================================================================
# app.py — INDEX ANALYTICS TERMINAL · NIFTY 50
# Clean entry point — no use_pages, manual routing
# Pages live in pages/ and expose layout() + register(app)
# =============================================================================

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from datetime import datetime

from shared import A, G, BO

# ── Import page modules (no circular import — they don't import app) ──────────
import pages.basis_monitor  as p_basis
import pages.dividend_shock as p_dividend

# ── App ───────────────────────────────────────────────────────────────────────

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Index Analytics Terminal · Nifty 50",
)

# ── Register all page callbacks ───────────────────────────────────────────────
p_basis.register(app)
p_dividend.register(app)

# ── Navbar ────────────────────────────────────────────────────────────────────

navbar = html.Div([html.Div([
    html.A(
        "INDEX ANALYTICS TERMINAL · NIFTY 50", href="/",
        style={"textDecoration":"none","marginRight":"2rem","color":A,
               "fontFamily":"IBM Plex Sans,sans-serif","fontWeight":"700",
               "fontSize":"0.78rem","letterSpacing":"0.12em","textTransform":"uppercase"},
    ),
    html.Div([
        dcc.Link("01 · BASIS MONITOR",  href="/",               className="nav-link", id="nav-1"),
        dcc.Link("02 · DIVIDEND SHOCK", href="/dividend-shock", className="nav-link", id="nav-2"),
        dcc.Link("03 · REBALANCING",    href="/rebalancing",    className="nav-link", id="nav-3"),
        dcc.Link("04 · METHODOLOGY",    href="/info",           className="nav-link", id="nav-4"),
    ], style={"display":"flex","alignItems":"center","flex":"1"}),
    html.Span("● NSE LIVE",
              style={"color":G,"fontSize":"0.6rem","letterSpacing":"0.12em","fontFamily":"IBM Plex Mono"}),
    html.Span(f"  {datetime.today().strftime('%d %b %Y').upper()}",
              style={"color":"#3A3A3A","fontSize":"0.6rem","fontFamily":"IBM Plex Mono"}),
], style={"display":"flex","alignItems":"center","maxWidth":"1500px","margin":"0 auto","width":"100%"})],
style={"background":"#000000","borderBottom":f"1px solid {A}","padding":"0 1.5rem",
       "height":"46px","display":"flex","alignItems":"center"})

# ── Routing callback ──────────────────────────────────────────────────────────

# ── Rebalancing placeholder ───────────────────────────────────────────────────

def render_rebalancing():
    from shared import page_footer, spot_g, days_g, expiry_g, fmt, kpi_card, A, GR
    from data.constituents import CANDIDATE_ADDITIONS
    spot   = spot_g
    days   = days_g
    expiry = expiry_g
    df     = __import__('shared').df_g
    prices = __import__('shared').prices_g

    symbols     = df.index.tolist()
    out_options = [{"label": f"{s}  —  {df.loc[s,'name']}  ({df.loc[s,'weight_pct']:.2f}%)", "value": s} for s in symbols]
    in_options  = [{"label": f"{s}  —  {v['name']}", "value": s} for s, v in CANDIDATE_ADDITIONS.items()]

    from shared import INPUT_STYLE, BTN_STYLE, CA, BO
    return html.Div([
        html.H1("REBALANCING SIMULATOR", className="page-title"),
        html.P("Constituent swap · Tracker flows · Futures impact", className="page-subtitle"),

        html.Div([
            kpi_card("NIFTY SPOT",    fmt(spot)),
            kpi_card("DAYS TO EXPIRY",str(days), expiry.strftime("%d %b %Y")),
            kpi_card("TRACKER AUM",   "₹2,500 bn", "default · editable"),
            kpi_card("NOTICE PERIOD", "4 WEEKS", "NSE advance notice"),
        ], style={"display":"grid","gridTemplateColumns":"repeat(4,1fr)",
                  "gap":"1px","marginBottom":"1.5rem","border":f"1px solid {A}"}),

        html.Div([
            html.Div([
                html.P("SWAP INPUTS", className="section-label"),
                html.Label("Stock to REMOVE", className="input-label"),
                dcc.Dropdown(id="r-out", options=out_options, value=symbols[-1],
                             clearable=False, style={"marginBottom":"0.8rem"}),
                html.Label("Stock to ADD", className="input-label"),
                dcc.Dropdown(id="r-in", options=in_options,
                             value=list(CANDIDATE_ADDITIONS.keys())[0],
                             clearable=False, style={"marginBottom":"0.8rem"}),
                html.Label("Price of incoming stock (₹)", className="input-label"),
                dcc.Input(id="r-price", type="number", value=3500, step=1, style=INPUT_STYLE),
                html.Label("Div yield of incoming stock (%)", className="input-label"),
                dcc.Input(id="r-div", type="number", value=0.20, step=0.05, style=INPUT_STYLE),
                html.Label("Futures Price", className="input-label"),
                dcc.Input(id="r-futures", type="number", value=round(spot), step=0.05, style=INPUT_STYLE),
                html.Label("Risk-Free Rate (%)", className="input-label"),
                dcc.Input(id="r-rfr", type="number", value=6.5, step=0.05, style=INPUT_STYLE),
                html.Label("Tracker AUM (₹ billion)", className="input-label"),
                dcc.Input(id="r-aum", type="number", value=2500, step=100, style=INPUT_STYLE),
                html.Button("RUN SIMULATION →", id="r-btn", n_clicks=0, style=BTN_STYLE),
                html.Div(id="r-results", style={"marginTop":"1rem"}),
            ], style={"flex":"0 0 300px"}),

            html.Div([
                html.P("WEIGHT REDISTRIBUTION — BEFORE vs AFTER", className="section-label"),
                html.Div(dcc.Graph(id="r-weights",
                                   figure=__import__('plotly.graph_objects', fromlist=['Figure']).Figure(
                                       layout={"paper_bgcolor":"#000000","plot_bgcolor":"#000000","height":300,
                                               "font":{"color":"#FF9900","family":"IBM Plex Mono"}}),
                                   config={"displayModeBar":False}),
                         style={"backgroundColor":"#000000"}),
                html.P("TRACKER FLOWS ON IMPLEMENTATION DAY", className="section-label"),
                html.Div(dcc.Graph(id="r-flows",
                                   figure=__import__('plotly.graph_objects', fromlist=['Figure']).Figure(
                                       layout={"paper_bgcolor":"#000000","plot_bgcolor":"#000000","height":220,
                                               "font":{"color":"#FF9900","family":"IBM Plex Mono"}}),
                                   config={"displayModeBar":False}),
                         style={"backgroundColor":"#000000"}),
            ], style={"flex":"1","minWidth":"0","paddingLeft":"2rem"}),
        ], style={"display":"flex","alignItems":"flex-start"}),

        page_footer("Tracker AUM source: AMFI"),
    ], className="page-container")


@app.callback(
    dash.Output("r-results", "children"),
    dash.Output("r-weights", "figure"),
    dash.Output("r-flows",   "figure"),
    dash.Input("r-btn",      "n_clicks"),
    dash.State("r-out",      "value"),
    dash.State("r-in",       "value"),
    dash.State("r-price",    "value"),
    dash.State("r-div",      "value"),
    dash.State("r-futures",  "value"),
    dash.State("r-rfr",      "value"),
    dash.State("r-aum",      "value"),
    prevent_initial_call=True,
)
def rebal_calc(n, sym_out, sym_in, price_in, div_in, futures_price, rfr, aum_bn):
    print(f">>> REBAL CALC: out={sym_out}, in={sym_in}")
    import plotly.graph_objects as go
    from shared import df_g, prices_g, spot_g, days_g, parse_num, result_row, fmt, A, G, R, GR, BO
    from data.index_math import simulate_constituent_swap

    spot   = spot_g
    days   = days_g
    df     = df_g
    prices = prices_g

    rfr_dec  = parse_num(rfr, 6.5) / 100.0
    futures  = parse_num(futures_price, float(round(spot)))
    price_in = parse_num(price_in, 3500)
    div_in   = parse_num(div_in, 0.0)
    aum_bn   = parse_num(aum_bn, 2500)

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
        result_row("Removed",      sym_out,                                        "result-neg"),
        result_row("Added",        sym_in,                                         "result-pos"),
        result_row("FV before",    fmt(result.old_fair_value)),
        result_row("FV after",     fmt(result.new_fair_value)),
        result_row("FV Δ",         f"{result.delta_future_points:+.2f} pts",       fv_cls),
        result_row(f"BUY {sym_in}",  f"₹{result.buy_stock_in_value/1e7:,.1f} Cr  ·  {result.buy_stock_in_shares:,.0f} shares",  "result-pos"),
        result_row(f"SELL {sym_out}", f"₹{result.sell_stock_out_value/1e7:,.1f} Cr  ·  {result.sell_stock_out_shares:,.0f} shares", "result-neg"),
        result_row("Tracker AUM",  f"₹{result.tracker_aum_bn:,.0f} bn"),
    ], className="result-box")

    # Weights chart
    top   = sorted(result.old_weights, key=lambda s: result.old_weights[s], reverse=True)[:15]
    wfig  = go.Figure()
    wfig.add_trace(go.Bar(name="BEFORE", x=top,
                          y=[result.old_weights.get(s,0) for s in top],
                          marker_color=BO, marker_line_width=0))
    wfig.add_trace(go.Bar(name="AFTER", x=top,
                          y=[result.new_weights.get(s,0) for s in top],
                          marker_color=A, marker_line_width=0, opacity=0.85))
    wfig.update_layout(barmode="group", paper_bgcolor="#000000", plot_bgcolor="#000000",
                       font=dict(family="IBM Plex Mono", color=A, size=11),
                       height=300, margin=dict(l=10,r=10,t=10,b=60),
                       xaxis=dict(showgrid=False, tickfont=dict(size=10,color=GR), tickangle=-45),
                       yaxis=dict(showgrid=True, gridcolor=BO, ticksuffix="%", tickfont=dict(size=10,color=GR)),
                       legend=dict(font=dict(size=10,color=GR), bgcolor="rgba(0,0,0,0)"))

    # Flows chart
    ffig = go.Figure(go.Bar(
        x=[sym_in, sym_out],
        y=[result.buy_stock_in_value/1e7, -result.sell_stock_out_value/1e7],
        marker_color=[G, R], marker_line_width=0,
        text=[f"₹{result.buy_stock_in_value/1e7:,.1f} Cr", f"-₹{result.sell_stock_out_value/1e7:,.1f} Cr"],
        textposition="outside",
        textfont=dict(family="IBM Plex Mono", size=13, color=A),
    ))
    ffig.add_hline(y=0, line_color=BO, line_width=1)
    ffig.update_layout(paper_bgcolor="#000000", plot_bgcolor="#000000",
                       font=dict(family="IBM Plex Mono", color=A, size=11),
                       height=220, margin=dict(l=10,r=10,t=10,b=40),
                       xaxis=dict(showgrid=False, tickfont=dict(size=12,color=GR)),
                       yaxis=dict(showgrid=True, gridcolor=BO, ticksuffix=" Cr", tickfont=dict(size=10,color=GR)),
                       showlegend=False)

    return results, wfig, ffig


@app.callback(
    dash.Output("page-content", "children"),
    dash.Output("nav-1", "className"),
    dash.Output("nav-2", "className"),
    dash.Output("nav-3", "className"),
    dash.Output("nav-4", "className"),
    dash.Input("url", "pathname"),
)
def route(pathname):
    print(f"ROUTE: {pathname}")
    paths = ["/", "/dividend-shock", "/rebalancing", "/info"]
    nav   = ["nav-link active" if pathname == p or (pathname in [None,"/",""] and p == "/")
             else "nav-link" for p in paths]
    if pathname in [None, "/", "/basis"]:
        return p_basis.layout(), *nav
    elif pathname == "/dividend-shock":
        nav[1] = "nav-link active"
        nav[0] = "nav-link"
        return p_dividend.layout(), *nav
    elif pathname == "/info":
        nav[3] = "nav-link active"
        nav[0] = "nav-link"
        from pages.info import layout as info_layout
        return info_layout(), *nav
    elif pathname == "/rebalancing":
        nav[2] = "nav-link active"
        nav[0] = "nav-link"
        return render_rebalancing(), *nav
    else:
        return p_basis.layout(), *nav

# ── Layout ────────────────────────────────────────────────────────────────────

app.layout = html.Div([
    dcc.Location(id="url"),
    navbar,
    html.Div(id="page-content"),
], style={"minHeight":"100vh","backgroundColor":"#000000"})


if __name__ == "__main__":
    app.run(debug=True, port=8050, use_reloader=False)