import dash
from dash import html, dcc, Input, Output, callback

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Input(id="my-input", type="number", value=100),
    html.Button("Click", id="my-btn", n_clicks=0),
    html.Div("nothing", id="my-output"),
])

@app.callback(
    Output("my-output", "children"),
    Input("my-btn", "n_clicks"),
    prevent_initial_call=True,
)
def update(n):
    print(f"FIRED: n={n}")
    return f"clicked {n} times"

if __name__ == "__main__":
    app.run(debug=True, port=8051)