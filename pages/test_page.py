import dash
from dash import html, dcc, callback, Input, Output, State

dash.register_page(__name__, path="/test", name="Test", order=5)

# je veux tester le probmle de callback context et de store data qui ne se met pas à jour dans le callback, alors que je fais un print et que je vois que la nouvelle data est bien là, mais elle ne se reflète pas dans le composant dcc.Store... est-ce un problème de cache ? ou de compréhension de comment le store fonctionne ?
btn   = html.Button("CLICK ME", id="test-btn", n_clicks=0)
out   = html.Div("nothing yet", id="test-out")
inp   = dcc.Input(id="test-input", type="number", value=100)
store = dcc.Store(id="test-store", data={"spot": 23151})

def layout():
    return html.Div([
        inp,
        btn,
        out,
        store,
    ], style={"padding": "2rem", "color": "white"})

@callback(
    Output("test-out", "children"),
    Input("test-btn", "n_clicks"),
    State("test-input", "value"),
    State("test-store", "data"),
    prevent_initial_call=True,
)
def test_cb(n, val, data):
    print(f">>> TEST CALLBACK FIRED: n={n}, val={val}, data={data}")
    return f"n_clicks={n}, input={val}, store_spot={data['spot']}"
