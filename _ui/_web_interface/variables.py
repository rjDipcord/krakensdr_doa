import json
import os
import platform
import sys

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

trace_colors = px.colors.qualitative.Plotly

current_path = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.dirname(os.path.dirname(current_path))
shared_path = os.path.join(root_path, "_share")

INVALID_SETTINGS_FILE_TIMESTAMP = -np.inf

settings_file_path = os.path.join(shared_path, "settings.json")
try:
    with open(settings_file_path, "r", encoding="utf-8") as myfile:
        dsp_settings = json.load(myfile)
except Exception:
    dsp_settings = dict()
    dsp_settings["timestamp"] = INVALID_SETTINGS_FILE_TIMESTAMP
else:
    dsp_settings["timestamp"] = os.stat(settings_file_path).st_mtime

try:
    import git

    SOFTWARE_GIT_SHORT_HASH = git.Repo().head.object.hexsha[:7]
except Exception:
    SOFTWARE_GIT_SHORT_HASH = "0000000"

SOFTWARE_VERSION = "0.1.0"
SYSTEM_UNAME = platform.uname()

status_file_path = os.path.join(shared_path, "status.json")

# Import paths for KrakenSDR modules
receiver_path = os.path.join(root_path, "_sdr/_receiver")
signal_processor_path = os.path.join(root_path, "_sdr/_signal_processing")
ui_path = os.path.join(root_path, "_ui")

sys.path.insert(0, receiver_path)
sys.path.insert(0, signal_processor_path)
sys.path.insert(0, ui_path)

# Wideband receiver constants
NUM_CHANNELS = 5
DEFAULT_CENTER_FREQ_MHZ = 100.0
DEFAULT_CHANNEL_BW_MHZ = 2.4
DEFAULT_OVERLAP_MHZ = 0.2
DEFAULT_FFT_SIZE = 4096
DEFAULT_WATERFALL_DEPTH = 100
HZ_TO_MHZ = 1.0e-6
AUTO_GAIN_VALUE = -100.0

# Plotly figure layout
fig_layout = go.Layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    template="plotly_dark",
    showlegend=False,
    margin=go.layout.Margin(t=0),
)
