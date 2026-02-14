import json
import logging
import queue
import time

from variables import (
    AUTO_GAIN_VALUE,
    DEFAULT_CENTER_FREQ_MHZ,
    DEFAULT_CHANNEL_BW_MHZ,
    DEFAULT_FFT_SIZE,
    DEFAULT_OVERLAP_MHZ,
    DEFAULT_WATERFALL_DEPTH,
    INVALID_SETTINGS_FILE_TIMESTAMP,
    dsp_settings,
    settings_file_path,
)
from kraken_sdr_receiver import ReceiverRTLSDR
from wideband_processor import WidebandProcessor


class WebInterface:
    def __init__(self):
        self.logging_level = dsp_settings.get("logging_level", 5) * 10
        logging.basicConfig(level=self.logging_level)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.logging_level)
        self.logger.info("Initializing wideband receiver web interface")

        if dsp_settings.get("timestamp") == INVALID_SETTINGS_FILE_TIMESTAMP:
            self.logger.warning("Settings file not found or corrupted!")

        # Queues for inter-thread communication
        self.sp_data_que = queue.Queue(1)
        self.rx_data_que = queue.Queue(1)

        self.data_interface = dsp_settings.get("data_interface", "shmem")

        # Instantiate receiver
        self.module_receiver = ReceiverRTLSDR(
            data_que=self.rx_data_que, data_interface=self.data_interface, logging_level=self.logging_level
        )
        self.module_receiver.daq_center_freq = float(dsp_settings.get("center_freq", DEFAULT_CENTER_FREQ_MHZ)) * 1e6
        gain = dsp_settings.get("uniform_gain", 15.7)
        self.module_receiver.daq_rx_gain = float(gain) if gain != "Auto" else AUTO_GAIN_VALUE
        self.module_receiver.rec_ip_addr = dsp_settings.get("default_ip", "0.0.0.0")

        # Instantiate wideband processor
        self.module_signal_processor = WidebandProcessor(
            data_que=self.sp_data_que, module_receiver=self.module_receiver, logging_level=self.logging_level
        )
        self.module_signal_processor.center_freq = self.module_receiver.daq_center_freq
        self.module_signal_processor.overlap_bandwidth = float(dsp_settings.get("overlap_mhz", DEFAULT_OVERLAP_MHZ)) * 1e6
        self.module_signal_processor.fft_size = int(dsp_settings.get("fft_size", DEFAULT_FFT_SIZE))
        self.module_signal_processor.waterfall_depth = int(dsp_settings.get("waterfall_depth", DEFAULT_WATERFALL_DEPTH))

        self.module_signal_processor.start()

        # UI status variables
        self.daq_conn_status = 0
        self.daq_cfg_iface_status = 0
        self.daq_frame_index = 0
        self.daq_frame_type = "-"
        self.daq_frame_sync = 1
        self.daq_sample_delay_sync = 0
        self.daq_iq_sync = 0
        self.daq_noise_source_state = 0
        self.daq_center_freq = float(dsp_settings.get("center_freq", DEFAULT_CENTER_FREQ_MHZ))
        self.daq_adc_fs = 0
        self.daq_fs = 0
        self.daq_cpi = 0
        self.daq_if_gains = "[,,,,]"
        self.daq_power_level = 0
        self.daq_update_rate = 0
        self.daq_dsp_latency = 0
        self.max_amplitude = 0

        # Display state
        self.spectrum = None
        self.update_time = 9999
        self.pathname = ""

        self.save_configuration()
        self.logger.info("Web interface initialized")

    def save_configuration(self):
        data = {}
        data["center_freq"] = self.module_receiver.daq_center_freq / 1e6
        data["uniform_gain"] = (
            self.module_receiver.daq_rx_gain if self.module_receiver.daq_rx_gain != AUTO_GAIN_VALUE else "Auto"
        )
        data["data_interface"] = self.data_interface
        data["default_ip"] = dsp_settings.get("default_ip", "0.0.0.0")
        data["overlap_mhz"] = self.module_signal_processor.overlap_bandwidth / 1e6
        data["fft_size"] = self.module_signal_processor.fft_size
        data["waterfall_depth"] = self.module_signal_processor.waterfall_depth
        data["logging_level"] = dsp_settings.get("logging_level", 5)

        with open(settings_file_path, "w") as outfile:
            json.dump(data, outfile, indent=2)

    def start_processing(self):
        self.logger.info("Start processing request")
        self.module_signal_processor.run_processing = True

    def stop_processing(self):
        self.module_signal_processor.run_processing = False
        while self.module_signal_processor.is_running:
            time.sleep(0.01)

    def close_data_interfaces(self):
        self.module_receiver.eth_close()

    def close(self):
        pass

    def config_daq_rf(self, f0, gain):
        """Configure RF parameters: center frequency (MHz) and gain (dB)."""
        self.daq_cfg_iface_status = 1
        self.module_signal_processor.center_freq = f0 * 1e6
        self.module_receiver.set_center_freq(int(f0 * 1e6))
        self.module_receiver.set_if_gain(gain)
        self.logger.info("Center frequency: %.3f MHz, Gain: %.1f dB", f0, gain)
