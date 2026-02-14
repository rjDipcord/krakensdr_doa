# KrakenSDR Wideband Receiver
#
# Copyright (C) 2018-2021  Carl Laufer, Tamas Peto
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# isort: off
from maindash import app

# isort: on

from views import main

app.layout = main.layout

from callbacks import main as _callbacks  # noqa: E402, F401

if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0", port=8080)
