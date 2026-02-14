import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from variables import DEFAULT_CENTER_FREQ_MHZ, DEFAULT_FFT_SIZE, DEFAULT_OVERLAP_MHZ, fig_layout

# ============================================================
#  Control Card — Center Frequency, Gain, FFT, Overlap
# ============================================================
control_card = dbc.Card(
    [
        dbc.CardHeader("Receiver Configuration"),
        dbc.CardBody(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Center Frequency [MHz]"),
                                dbc.Input(
                                    id="center_freq",
                                    type="number",
                                    value=DEFAULT_CENTER_FREQ_MHZ,
                                    step=0.001,
                                    min=24,
                                    max=1766,
                                ),
                            ],
                            width=3,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Gain [dB]"),
                                dbc.Input(
                                    id="uniform_gain",
                                    type="number",
                                    value=15.7,
                                    step=0.1,
                                    min=0,
                                    max=49.6,
                                ),
                            ],
                            width=2,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Overlap [MHz]"),
                                dbc.Input(
                                    id="overlap_mhz",
                                    type="number",
                                    value=DEFAULT_OVERLAP_MHZ,
                                    step=0.01,
                                    min=0,
                                    max=1.0,
                                ),
                            ],
                            width=2,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("FFT Size"),
                                dcc.Dropdown(
                                    id="fft_size",
                                    options=[{"label": str(2**n), "value": 2**n} for n in range(10, 16)],
                                    value=DEFAULT_FFT_SIZE,
                                    clearable=False,
                                ),
                            ],
                            width=2,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("\u00a0"),
                                dbc.Button("Apply", id="btn_apply_config", color="primary", className="w-100"),
                            ],
                            width=2,
                        ),
                    ],
                    className="mb-2",
                ),
            ]
        ),
    ],
    className="mb-3",
)

# ============================================================
#  Status Card — DAQ Status
# ============================================================
status_card = dbc.Card(
    [
        dbc.CardHeader("DAQ Status"),
        dbc.CardBody(
            dbc.Row(
                [
                    dbc.Col(html.Div(id="daq_status_info", children="Waiting for data..."), width=12),
                ]
            )
        ),
    ],
    className="mb-3",
)

# ============================================================
#  Spectrum Plot
# ============================================================
spectrum_fig = go.Figure(layout=fig_layout)
spectrum_fig.add_trace(go.Scattergl(x=[], y=[], mode="lines", name="Spectrum", line=dict(color="#00B5F7", width=1)))
spectrum_fig.update_layout(
    xaxis_title="Frequency [MHz]",
    yaxis_title="Power [dB]",
    height=350,
)

spectrum_card = dbc.Card(
    [
        dbc.CardHeader("Wideband Spectrum"),
        dbc.CardBody(dcc.Graph(id="spectrum_graph", figure=spectrum_fig, config={"displayModeBar": False})),
    ],
    className="mb-3",
)

# ============================================================
#  Waterfall Plot
# ============================================================
waterfall_fig = go.Figure(layout=fig_layout)
waterfall_fig.add_trace(go.Heatmap(z=[[]], colorscale="Jet", showscale=True, colorbar=dict(title="dB")))
waterfall_fig.update_layout(
    xaxis_title="Frequency [MHz]",
    yaxis_title="Time",
    height=300,
)

waterfall_card = dbc.Card(
    [
        dbc.CardHeader("Waterfall"),
        dbc.CardBody(dcc.Graph(id="waterfall_graph", figure=waterfall_fig, config={"displayModeBar": False})),
    ],
    className="mb-3",
)

# ============================================================
#  Main Layout
# ============================================================
layout = dbc.Container(
    [
        html.H3("KrakenSDR Wideband Receiver", className="mt-3 mb-3"),
        control_card,
        status_card,
        spectrum_card,
        waterfall_card,
        dcc.Interval(id="update_interval", interval=250, n_intervals=0),
    ],
    fluid=True,
)
