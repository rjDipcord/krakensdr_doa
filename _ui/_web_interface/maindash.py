import dash_devices as dash
from kraken_web_interface import WebInterface

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "KrakenSDR Wideband"
app.config.suppress_callback_exceptions = True

web_interface = WebInterface()
