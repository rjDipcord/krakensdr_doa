import time

import dash_core_components as dcc
import dash_devices as dash
import numpy as np
import plotly.graph_objects as go

# isort: off
from maindash import app, web_interface

# isort: on

from dash_devices.dependencies import Input, Output, State
from iq_header import IQHeader
from variables import AUTO_GAIN_VALUE, HZ_TO_MHZ, fig_layout


def fetch_dsp_data():
    """Pull one data packet from the signal processor queue."""
    que = web_interface.sp_data_que
    try:
        data_packet = que.get(False)
    except Exception:
        return

    for entry in data_packet:
        key = entry[0]
        val = entry[1]

        if key == "iq_header":
            web_interface.daq_frame_index = val.cpi_index
            web_interface.daq_frame_sync = not bool(val.check_sync_word())
            web_interface.daq_sample_delay_sync = bool(val.delay_sync_flag)
            web_interface.daq_iq_sync = bool(val.iq_sync_flag)
            web_interface.daq_noise_source_state = bool(val.noise_source_state)
            web_interface.daq_adc_fs = val.adc_sampling_freq
            web_interface.daq_fs = val.sampling_freq
            if val.sampling_freq > 0:
                web_interface.daq_cpi = int(val.cpi_length * 1000 / val.sampling_freq)
            if val.frame_type == IQHeader.FRAME_TYPE_DATA:
                web_interface.daq_conn_status = 1
            elif val.frame_type == IQHeader.FRAME_TYPE_EMPTY:
                web_interface.daq_conn_status = 0

        elif key == "spectrum":
            web_interface.spectrum = val

        elif key == "waterfall":
            web_interface.waterfall = val

        elif key == "update_rate":
            web_interface.update_time = val


# ============================================
#    Periodic UI Update
# ============================================
@app.callback_shared(
    [
        Output("spectrum_graph", "figure"),
        Output("waterfall_graph", "figure"),
        Output("daq_status_info", "children"),
    ],
    [Input("update_interval", "n_intervals")],
)
def update_display(_n):
    fetch_dsp_data()

    # --- Spectrum ---
    spectrum_data = getattr(web_interface, "spectrum", None)
    spec_fig = go.Figure(layout=fig_layout)

    if spectrum_data is not None:
        freqs_hz, power_db = spectrum_data
        freqs_mhz = freqs_hz * HZ_TO_MHZ
        spec_fig.add_trace(
            go.Scattergl(x=freqs_mhz, y=power_db, mode="lines", line=dict(color="#00B5F7", width=1))
        )
    else:
        spec_fig.add_trace(go.Scattergl(x=[], y=[], mode="lines"))

    spec_fig.update_layout(
        xaxis_title="Frequency [MHz]",
        yaxis_title="Power [dB]",
        height=350,
    )

    # --- Waterfall ---
    waterfall_data = getattr(web_interface, "waterfall", None)
    wf_fig = go.Figure(layout=fig_layout)

    if waterfall_data is not None and spectrum_data is not None:
        freqs_mhz = spectrum_data[0] * HZ_TO_MHZ
        wf_fig.add_trace(
            go.Heatmap(
                z=waterfall_data,
                x=freqs_mhz,
                colorscale="Jet",
                showscale=True,
                colorbar=dict(title="dB"),
                zmin=-120,
                zmax=-20,
            )
        )
    else:
        wf_fig.add_trace(go.Heatmap(z=[[]], colorscale="Jet", showscale=True, colorbar=dict(title="dB")))

    wf_fig.update_layout(
        xaxis_title="Frequency [MHz]",
        yaxis_title="Time",
        height=300,
    )

    # --- Status ---
    if web_interface.daq_conn_status == 1:
        status_str = (
            f"Connected | "
            f"Frame: {web_interface.daq_frame_index} | "
            f"Fs: {web_interface.daq_fs / 1e6:.3f} MHz | "
            f"CPI: {web_interface.daq_cpi} ms | "
            f"Sync: {'OK' if web_interface.daq_iq_sync else 'NO'} | "
            f"Update: {web_interface.update_time * 1000:.0f} ms"
        )
    else:
        status_str = "No DAQ data"

    return [spec_fig, wf_fig, status_str]


# ============================================
#    Apply Configuration
# ============================================
@app.callback(
    Output("daq_status_info", "style"),
    [Input("btn_apply_config", "n_clicks")],
    [
        State("center_freq", "value"),
        State("uniform_gain", "value"),
        State("overlap_mhz", "value"),
        State("fft_size", "value"),
    ],
)
def apply_config(n_clicks, center_freq, gain, overlap_mhz, fft_size):
    if n_clicks is None:
        return dash.no_update

    if center_freq is not None and gain is not None:
        web_interface.config_daq_rf(float(center_freq), float(gain))
        web_interface.daq_center_freq = float(center_freq)

    if overlap_mhz is not None:
        web_interface.module_signal_processor.overlap_bandwidth = float(overlap_mhz) * 1e6

    if fft_size is not None:
        web_interface.module_signal_processor.fft_size = int(fft_size)

    web_interface.save_configuration()
    return {}
