# =============================================================================
# components/footer.py — shared footer for all pages
# =============================================================================

from dash import html
from datetime import datetime


def make_footer(page_note: str = ""):
    return html.Div([
        html.Div([
            html.Div("INDEX ANALYTICS TERMINAL · NIFTY 50", style={"color": "#FF9900", "fontSize": "0.62rem", "letterSpacing": "0.12em"}),
            html.Div(f"Data: NSE India API · Live prices · {page_note}" if page_note else "Data: NSE India API · Live prices", style={"marginTop": "2px"}),
            html.Div(f"Generated: {datetime.today().strftime('%d %b %Y %H:%M')} IST", style={"marginTop": "2px"}),
        ], style={"color": "#3A3A3A", "fontSize": "0.6rem", "fontFamily": "IBM Plex Mono"}),

        html.Div([
            html.Div("MOHAMED-ABDELLAHI MOHAMED-ABDELLAHI", className="footer-author", style={"color": "#888", "fontWeight": "600"}),
            html.Div([
                html.Span("MSc 203 · Université Paris Dauphine–PSL", style={"color": "#3A3A3A"}),
            ], style={"fontSize": "0.6rem", "fontFamily": "IBM Plex Mono", "marginTop": "2px"}),
            html.Div([
                html.A("mohamed-abdellahi.mohamed-abdellahi@dauphine.eu",
                       href="mailto:mohamed-abdellahi.mohamed-abdellahi@dauphine.eu",
                       className="footer-author"),
                html.Span("  ·  ", style={"color": "#3A3A3A"}),
                html.A(" LinkedIn",
                       href="https://www.linkedin.com/in/mohamed-abdellahi-mohamed-abdellahi-4341a1205/",
                       target="_blank", className="footer-author"),
                html.Span("  ·  ", style={"color": "#3A3A3A"}),
                html.Span("+33 6 68 22 49 93", style={"color": "#888", "fontSize": "0.62rem"}),
            ], style={"marginTop": "3px"}),
        ], style={"textAlign": "right"}),
    ], className="footer")
