# KrakenSDR Wideband Receiver

This software combines all five clock-synchronized RTL-SDR receivers in the KrakenSDR into a single super-wide bandwidth receiver for wideband spectrum monitoring. It uses the HeIMDALL DAQ Firmware for coherent data acquisition.

The application is broken down into two main modules: the DAQ Subsystem and the DSP Subsystem. These two modules can operate together either remotely through Ethernet connection or locally on the same host using shared-memory.

## Installation

### Prerequisites

``` bash
sudo apt -y update
sudo apt -y install jq
```

(**OPTIONAL** - for remote control file serving)
```bash
sudo apt -y install rustc cargo php-cli
cargo install miniserve
```

### Install Heimdall DAQ

Follow the instructions at https://github.com/krakenrf/heimdall_daq_fw/tree/main to install the Heimdall DAQ Firmware.

### Set up Miniconda environment

You will have created a Miniconda environment during the Heimdall DAQ install phase.

Please run the installs in this order as we need to ensure a specific version of dash and Werkzeug is installed because newer versions break compatibility with other libraries.

``` bash
conda activate kraken

conda install pandas
conda install orjson
conda install matplotlib
conda install requests

pip3 install dash_bootstrap_components==1.1.0
pip3 install quart_compress==0.2.1
pip3 install quart==0.17.0
pip3 install dash_devices==0.1.3
pip3 install pyargus

conda install dash==1.20.0
conda install werkzeug==2.0.2
conda install -y plotly==5.23.0
```

### Clone the repository

```bash
cd ~/krakensdr
git clone <REPO_URL>
```

Copy the startup/stop scripts into the krakensdr root folder:
```bash
cp krakensdr_doa/util/kraken_doa_start.sh .
cp krakensdr_doa/util/kraken_doa_stop.sh .
```

## Running

### Local operation (Recommended)

```bash
./kraken_doa_start.sh
```

### Remote operation

With remote operation you can run the DAQ on one machine on your network, and the DSP software on another.

1. Start the heimdall DAQ subsystem on your remote computing device. (Make sure that the `daq_chain_config.ini` contains the proper configuration)
    (See: https://github.com/krakenrf/heimdall_daq_fw/blob/main/Documentation/HDAQ_firmware_ver1.0.20201130.pdf)
2. Set the IP address of the DAQ Subsystem in the `settings.json`, `default_ip` field.
3. Start the DSP software by typing:
`./gui_run.sh`
4. To stop the server and the DSP processing chain run the following script:
`./kill.sh`

After starting the script a web based server opens at port number `8080`, which then can be accessed by typing `KRAKEN_IP:8080/` in the address bar of any web browser.

## For Contributors

If you plan to contribute code then it must follow certain formatting style. The easiest way to apply autoformatting and check for any [PEP8](https://peps.python.org/pep-0008/) violations is to install [`pre-commit`](https://pre-commit.com/) tool, e.g., with

```bash
pip3 install --user pre-commit
```

Then from within the project folder execute:

```bash
pre-commit install
```

This sets up git pre-commit hooks. Those will autoformat and check changed files on every consecutive commit. Once you create a PR for your changes, [GitHub Actions](https://github.com/features/actions) will be executed to perform the very same checks as the hooks to make sure your code follows the formatting style and does not violate PEP8 rules.
