# =============================================================================
# pages/basis_monitor.py — Page 1: Basis Monitor
# layout() returns the page layout
# register(app) registers all callbacks — called from app.py after app creation
# =============================================================================

from dash import html, dcc, Input, Output, State
import dash

from shared import (
    A, GR, CA, BO,
    INPUT_STYLE, BTN_STYLE,
    df_g, prices_g, spot_g, days_g, expiry_g, default_div_g,
    fmt, parse_num, result_row, kpi_card, page_footer,
    build_decomp, build_rate_chart, build_sensi_table,
    compute_dividend_drag, compute_fair_value,
)


def layout():
    spot   = spot_g
    days   = days_g
    df     = df_g
    prices = prices_g
    expiry = expiry_g
    gdiv   = default_div_g

    overrides = {s: gdiv for s in df.index}
    drag = compute_dividend_drag(df, prices, spot, days, overrides=overrides)
    fv   = compute_fair_value(spot, days, drag, float(round(spot)), 0.065)

    basis_lbl = "FUTURES RICH ▲" if fv.basis > 1 else ("FUTURES CHEAP ▼" if fv.basis < -1 else "AT FAIR VALUE")
    basis_cls = "kpi-delta-pos" if fv.basis >= 0 else "kpi-delta-neg"

    return html.Div([
        html.H1("BASIS MONITOR", className="page-title"),
        html.P("Fair value · Basis decomposition · Rate sensitivity", className="page-subtitle"),

        html.Div([
            kpi_card("NIFTY SPOT",  fmt(spot)),
            kpi_card("FUTURES",     fmt(spot), "enter below"),
            kpi_card("FAIR VALUE",  fmt(fv.fair_value)),
            kpi_card("BASIS",       f"{fv.basis:+.2f} pts", basis_lbl, basis_cls),
            kpi_card("BASIS ANN.",  f"{fv.basis_annualized:+.4f}%", f"{days}d · +6.50%"),
        ], id="b-kpis", style={
            "display":"grid","gridTemplateColumns":"repeat(5,1fr)",
            "gap":"1px","marginBottom":"1.5rem","border":f"1px solid {A}",
        }),

        html.Div([
            html.Div([
                html.P("MARKET INPUTS", className="section-label"),
                html.Label("Futures Price", className="input-label"),
                dcc.Input(id="b-futures", type="number", value=round(spot),
                          step=0.05, style=INPUT_STYLE),
                html.Label("Risk-Free Rate (%)", className="input-label"),
                html.Div("Supports negative rates",
                         style={"color":GR,"fontSize":"0.6rem","marginBottom":"0.2rem"}),
                dcc.Input(id="b-rfr", type="number", value=6.5, step=0.25, style=INPUT_STYLE),
                html.Label("Global Div Yield (%)", className="input-label"),
                html.Div("Weighted avg of all 50 constituents",
                         style={"color":GR,"fontSize":"0.6rem","marginBottom":"0.2rem"}),
                html.Div([
                    html.Button("−", id="b-div-minus", n_clicks=0,
                                style={"background":CA,"border":f"1px solid {BO}","color":A,
                                       "fontFamily":"IBM Plex Mono","fontSize":"1rem",
                                       "width":"40px","height":"34px","cursor":"pointer"}),
                    dcc.Input(id="b-div", type="text",
                              value=str(gdiv).replace(".",","),
                              style={**INPUT_STYLE,"marginBottom":"0","flex":"1","textAlign":"center"}),
                    html.Button("+", id="b-div-plus", n_clicks=0,
                                style={"background":CA,"border":f"1px solid {BO}","color":A,
                                       "fontFamily":"IBM Plex Mono","fontSize":"1rem",
                                       "width":"40px","height":"34px","cursor":"pointer"}),
                ], style={"display":"flex","gap":"0","marginBottom":"1.5rem"}),
                html.Button("CALCULATE", id="b-btn", n_clicks=0, style=BTN_STYLE),
                html.Div(id="b-results"),
                html.P("RATE SENSITIVITY · 0.25% STEPS", className="section-label"),
                html.Div(build_sensi_table(spot, days, drag, float(round(spot)), 6.5), id="b-sensi"),
            ], style={"flex":"0 0 290px"}),

            html.Div([
                html.P("FAIR VALUE DECOMPOSITION", className="section-label"),
                html.Div(dcc.Graph(id="b-decomp",
                                   figure=build_decomp(spot, float(round(spot)), fv),
                                   config={"displayModeBar":False}),
                         style={"backgroundColor":"#000000"}),
                html.P("BASIS vs RISK-FREE RATE", className="section-label"),
                html.Div(dcc.Graph(id="b-rate",
                                   figure=build_rate_chart(spot, days, drag, float(round(spot)), 6.5),
                                   config={"displayModeBar":False}),
                         style={"backgroundColor":"#000000"}),
            ], style={"flex":"1","minWidth":"0","paddingLeft":"2rem"}),
        ], style={"display":"flex","alignItems":"flex-start"}),

        page_footer(f"Expiry: {expiry.strftime('%d %b %Y').upper()} · {days} days"),
    ], className="page-container")


def register(app):
    """Register all callbacks for this page. Called from app.py after app creation."""

    @app.callback(
        Output("b-div", "value"),
        Input("b-div-minus", "n_clicks"),
        Input("b-div-plus",  "n_clicks"),
        State("b-div", "value"),
        prevent_initial_call=True,
    )
    def adjust_div(n_minus, n_plus, current):
        triggered = dash.callback_context.triggered[0]["prop_id"]
        val = parse_num(current, default_div_g)
        if "plus"  in triggered: val = round(val + 0.05, 3)
        elif "minus" in triggered: val = round(max(0, val - 0.05), 3)
        return str(val).replace(".", ",")

    @app.callback(
        Output("b-kpis",    "children"),
        Output("b-results", "children"),
        Output("b-decomp",  "figure"),
        Output("b-rate",    "figure"),
        Output("b-sensi",   "children"),
        Input("b-btn",      "n_clicks"),
        State("b-futures",  "value"),
        State("b-rfr",      "value"),
        State("b-div",      "value"),
        prevent_initial_call=True,
    )
    def basis_calc(n, futures_price, rfr, div_input):
        print(f">>> BASIS CALC: futures={futures_price}, rfr={rfr}, div={div_input}")
        spot   = spot_g
        days   = days_g
        df     = df_g
        prices = prices_g

        rfr_val = parse_num(rfr, 6.5)
        futures = parse_num(futures_price, float(round(spot)))
        gdiv    = parse_num(div_input, default_div_g)

        overrides = {s: gdiv for s in df.index}
        drag = compute_dividend_drag(df, prices, spot, days, overrides=overrides)
        fv   = compute_fair_value(spot, days, drag, futures, rfr_val / 100.0)

        basis_lbl = "FUTURES RICH ▲" if fv.basis > 1 else ("FUTURES CHEAP ▼" if fv.basis < -1 else "AT FAIR VALUE")
        basis_cls = "kpi-delta-pos" if fv.basis >= 0 else "kpi-delta-neg"
        net = fv.cost_of_carry - fv.dividend_drag

        return (
            [kpi_card("NIFTY SPOT",  fmt(spot)),
             kpi_card("FUTURES",     fmt(futures)),
             kpi_card("FAIR VALUE",  fmt(fv.fair_value)),
             kpi_card("BASIS",       f"{fv.basis:+.2f} pts", basis_lbl, basis_cls),
             kpi_card("BASIS ANN.",  f"{fv.basis_annualized:+.4f}%", f"{days}d · {rfr_val:+.2f}%")],
            html.Div([
                result_row("Cost of carry",    f"+{fv.cost_of_carry:.4f} pts", "result-pos"),
                result_row("Dividend drag",    f"-{fv.dividend_drag:.4f} pts", "result-neg"),
                result_row("Net carry",        f"{net:+.4f} pts", "result-pos" if net >= 0 else "result-neg"),
                result_row("Global div yield", f"{gdiv:.3f}%", "result-amb"),
                result_row("Risk-free rate",   f"{rfr_val:+.2f}%"),
                result_row("Days to expiry",   str(days)),
            ], className="result-box"),
            build_decomp(spot, futures, fv),
            build_rate_chart(spot, days, drag, futures, rfr_val),
            build_sensi_table(spot, days, drag, futures, rfr_val),
        )