# =============================================================================
# shared.py — Common constants, helpers, and startup data
# Imported by app.py and all page modules
# =============================================================================

from dash import html
import plotly.graph_objects as go
import numpy as np

from data.constituents import get_constituent_df, get_prices_dict
from data.futures import get_nifty_spot, get_days_to_expiry, get_expiry_dates
from data.index_math import compute_dividend_drag, compute_fair_value

# ─── COLORS ───────────────────────────────────────────────────────────────────

A  = "#FF9900"
G  = "#00CC44"
R  = "#FF3333"
GR = "#888888"
BG = "#000000"
CA = "#111111"
BO = "#2A2A2A"

# ─── STYLES ───────────────────────────────────────────────────────────────────

INPUT_STYLE = {
    "width": "100%", "marginBottom": "1rem",
    "background": CA, "border": f"1px solid {BO}",
    "color": A, "fontFamily": "IBM Plex Mono",
    "fontSize": "0.88rem", "padding": "0.35rem 0.6rem",
}

BTN_STYLE = {
    "background": A, "color": "#000", "border": "none",
    "padding": "0.5rem", "fontFamily": "IBM Plex Mono",
    "fontSize": "0.72rem", "letterSpacing": "0.12em",
    "textTransform": "uppercase", "cursor": "pointer",
    "fontWeight": "700", "width": "100%", "marginBottom": "1rem",
}

# ─── STARTUP DATA (fetched once) ──────────────────────────────────────────────

print("Fetching live data from NSE...")
df_g      = get_constituent_df()
prices_g  = get_prices_dict()
spot_g    = get_nifty_spot()
days_g    = get_days_to_expiry()
expiry_g  = get_expiry_dates(1)[0]
default_div_g = round(
    sum(df_g.loc[s, "div_yield"] * df_g.loc[s, "weight_pct"] / 100
        for s in df_g.index), 3
)
print(f"Data loaded: spot={spot_g:.2f}, days={days_g}, constituents={len(df_g)}")

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def fmt(v, d=2, pre="", suf=""):
    if v is None: return "—"
    return f"{pre}{v:,.{d}f}{suf}"

def parse_num(v, default):
    """Parse number handling both comma and dot decimal separators (Mac locale)."""
    try:
        return float(str(v).replace(",", ".")) if v is not None else default
    except (ValueError, TypeError):
        return default

def result_row(label, value, cls="result-value"):
    return html.Div([
        html.Span(label, className="result-label"),
        html.Span(value, className=cls),
    ], className="result-row")

def kpi_card(label, value, sub=None, sub_cls="kpi-delta-neu"):
    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(value, className="kpi-value"),
        html.Div(sub, className=sub_cls) if sub else html.Div(),
    ], className="kpi-card")

def page_footer(note=""):
    return html.Div([
        html.Div([
            html.Div("INDEX ANALYTICS TERMINAL · NIFTY 50",
                     style={"color": A, "fontSize": "0.62rem", "letterSpacing": "0.12em"}),
            html.Div(f"NSE India API · {note}" if note else "NSE India API",
                     style={"color": "#3A3A3A", "fontSize": "0.6rem", "marginTop": "2px"}),
        ]),
        html.Div([
            html.Div("MOHAMED-ABDELLAHI MOHAMED-ABDELLAHI",
                     style={"color": GR, "fontWeight": "600", "fontSize": "0.65rem"}),
            html.Div("MSc 203 · Université Paris Dauphine–PSL",
                     style={"color": "#3A3A3A", "fontSize": "0.6rem", "marginTop": "2px"}),
            html.Div([
                html.A("📧 Email",
                       href="mailto:mohamed-abdellahi.mohamed-abdellahi@dauphine.eu",
                       style={"color": A, "fontSize": "0.62rem", "textDecoration": "none"}),
                html.Span("  ·  ", style={"color": "#3A3A3A"}),
                html.A("🔗 LinkedIn",
                       href="https://www.linkedin.com/in/mohamed-abdellahi-mohamed-abdellahi-4341a1205/",
                       target="_blank",
                       style={"color": A, "fontSize": "0.62rem", "textDecoration": "none"}),
                html.Span("  ·  +33 6 68 22 49 93",
                           style={"color": GR, "fontSize": "0.62rem"}),
            ], style={"marginTop": "3px"}),
        ], style={"textAlign": "right"}),
    ], style={
        "marginTop": "2rem", "paddingTop": "0.8rem",
        "borderTop": f"1px solid {BO}",
        "display": "flex", "justifyContent": "space-between", "alignItems": "flex-end",
        "fontFamily": "IBM Plex Mono",
    })

# ─── FIGURE BUILDERS ──────────────────────────────────────────────────────────

def build_decomp(spot, futures, fv):
    y_pad = max(abs(fv.cost_of_carry), abs(fv.dividend_drag)) * 3
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=["SPOT", "+ CARRY", "− DIV DRAG", "FAIR VALUE"],
        y=[spot, fv.cost_of_carry, -fv.dividend_drag, 0],
        connector=dict(line=dict(color=BO, width=1)),
        increasing=dict(marker_color=G, marker_line_width=0),
        decreasing=dict(marker_color=R, marker_line_width=0),
        totals=dict(marker_color=A, marker_line_width=0),
        text=[fmt(spot), f"+{fv.cost_of_carry:.2f}", f"-{fv.dividend_drag:.2f}", fmt(fv.fair_value)],
        textposition="outside",
        textfont=dict(family="IBM Plex Mono", size=13, color=A),
    ))
    fig.add_hline(y=futures, line_dash="dash", line_color="rgba(136,136,136,0.6)",
                  annotation_text=f"MKT  {fmt(futures)}",
                  annotation_font=dict(color=GR, size=11, family="IBM Plex Mono"),
                  annotation_position="bottom right")
    fig.update_layout(
        paper_bgcolor="#000000", plot_bgcolor="#000000",
        font=dict(family="IBM Plex Mono", color=A, size=12),
        height=400, margin=dict(l=20, r=60, t=60, b=20),
        xaxis=dict(showgrid=False, tickfont=dict(size=13, color=A)),
        yaxis=dict(showgrid=True, gridcolor=BO, tickfont=dict(size=11, color=GR),
                   tickformat=",.0f",
                   range=[min(spot, futures, fv.fair_value) - y_pad,
                          max(spot, futures, fv.fair_value) + y_pad]),
        showlegend=False,
    )
    return fig


def build_rate_chart(spot, days, drag, futures, rfr_val):
    rates = np.arange(rfr_val - 4.0, rfr_val + 4.25, 0.25)
    bases = [compute_fair_value(spot, days, drag, futures, r/100.0).basis for r in rates]
    fig = go.Figure(go.Scatter(
        x=list(rates), y=bases, mode="lines",
        line=dict(color=A, width=2),
        fill="tozeroy", fillcolor="rgba(255,153,0,0.06)",
        hovertemplate="Rate: %{x:.2f}%<br>Basis: %{y:+.2f} pts<extra></extra>",
    ))
    fig.add_vline(x=rfr_val, line_dash="dash", line_color="rgba(255,51,51,0.7)",
                  annotation_text=f"{rfr_val:+.2f}%",
                  annotation_font=dict(color=R, size=11, family="IBM Plex Mono"))
    fig.add_hline(y=0, line_color=BO, line_width=1)
    fig.update_layout(
        paper_bgcolor="#000000", plot_bgcolor="#000000",
        font=dict(family="IBM Plex Mono", color=A, size=11),
        height=260, margin=dict(l=20, r=20, t=20, b=40),
        xaxis=dict(showgrid=True, gridcolor=BO, ticksuffix="%",
                   tickfont=dict(size=11, color=GR), dtick=1.0),
        yaxis=dict(showgrid=True, gridcolor=BO, ticksuffix=" pts",
                   tickfont=dict(size=11, color=GR)),
        showlegend=False,
    )
    return fig


def build_sensi_table(spot, days, drag, futures, rfr_val):
    rates = [r for r in np.arange(rfr_val - 4.0, rfr_val + 4.25, 0.25)
             if abs(r - rfr_val) <= 2.01]
    rows = []
    for r in rates:
        fv_r   = compute_fair_value(spot, days, drag, futures, r/100.0)
        is_cur = abs(r - rfr_val) < 0.13
        b_cls  = "td-pos" if fv_r.basis >= 0 else "td-neg"
        rows.append(html.Tr([
            html.Td(f"{r:+.2f}%",                    className="td-amb" if is_cur else ""),
            html.Td(fmt(fv_r.fair_value)),
            html.Td(f"{fv_r.basis:+.2f}",             className=b_cls),
            html.Td(f"{fv_r.basis_annualized:+.3f}%", className=b_cls),
        ], style={"background": "rgba(255,153,0,0.06)" if is_cur else "transparent"}))
    header = html.Tr([
        html.Th("RATE %", style={"textAlign": "left"}),
        html.Th("FAIR VAL"), html.Th("BASIS"), html.Th("ANN %"),
    ])
    return html.Table([html.Thead(header), html.Tbody(rows)], className="data-table")


def build_drag_chart(df, spot, days, symbol=None):
    tf = days / 365.0
    items = sorted(
        [(s, spot * (df.loc[s,"weight_pct"]/100) * (df.loc[s,"div_yield"]/100) * tf)
         for s in df.index], key=lambda x: x[1])[-15:]
    fig = go.Figure(go.Bar(
        x=[x[1] for x in items], y=[x[0] for x in items], orientation="h",
        marker_color=[A if x[0] == symbol else "#2A2A2A" for x in items],
        marker_line_width=0,
        text=[f"{x[1]:.3f}" for x in items], textposition="outside",
        textfont=dict(family="IBM Plex Mono", size=11, color=A),
    ))
    fig.update_layout(
        paper_bgcolor="#000000", plot_bgcolor="#000000",
        font=dict(family="IBM Plex Mono", color=A, size=11),
        height=380, margin=dict(l=10, r=60, t=10, b=20),
        xaxis=dict(showgrid=True, gridcolor=BO, ticksuffix=" pts",
                   tickfont=dict(size=10, color=GR)),
        yaxis=dict(showgrid=False, tickfont=dict(size=11, color=GR)),
        bargap=0.3,
    )
    return fig