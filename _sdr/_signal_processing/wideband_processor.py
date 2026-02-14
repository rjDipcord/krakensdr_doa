import json
import logging
import threading
import time

import numpy as np
from iq_header import IQHeader
from kraken_sdr_receiver import ReceiverRTLSDR
from scipy import fft, signal
from variables import (
    DEFAULT_CHANNEL_BW_MHZ,
    DEFAULT_FFT_SIZE,
    DEFAULT_OVERLAP_MHZ,
    DEFAULT_WATERFALL_DEPTH,
    NUM_CHANNELS,
    SOFTWARE_GIT_SHORT_HASH,
    SOFTWARE_VERSION,
    SYSTEM_UNAME,
    status_file_path,
)


class WidebandProcessor(threading.Thread):
    def __init__(self, data_que, module_receiver: ReceiverRTLSDR, logging_level=10):
        super().__init__(daemon=True)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging_level)

        self.module_receiver = module_receiver
        self.data_que = data_que

        # Processing control
        self.run_processing = True
        self.is_running = False
        self.first_frame = True

        # Channel configuration
        self.num_channels = NUM_CHANNELS
        self.center_freq = 100e6  # Hz — center of the wideband span
        self.channel_bandwidth = DEFAULT_CHANNEL_BW_MHZ * 1e6  # Hz per channel
        self.overlap_bandwidth = DEFAULT_OVERLAP_MHZ * 1e6  # Hz overlap between adjacent channels

        # FFT and display parameters
        self.fft_size = DEFAULT_FFT_SIZE
        self.spectrum_averaging = 1
        self.waterfall_depth = DEFAULT_WATERFALL_DEPTH

        # State
        self.channel_number = 0  # Updated from IQ header
        self.waterfall_buffer = None
        self.wideband_spectrum = None
        self.wideband_freqs = None

        # Timing
        self.latency = 0
        self.processing_time = 0
        self.dropped_frames = 0

    @property
    def channel_step(self):
        """Frequency step between adjacent channel centers."""
        return self.channel_bandwidth - self.overlap_bandwidth

    @property
    def channel_frequencies(self):
        """Center frequency for each of the 5 receivers."""
        freqs = np.zeros(self.num_channels)
        for i in range(self.num_channels):
            freqs[i] = self.center_freq + (i - self.num_channels // 2) * self.channel_step
        return freqs

    @property
    def total_bandwidth(self):
        """Total wideband coverage in Hz."""
        return self.num_channels * self.channel_bandwidth - (self.num_channels - 1) * self.overlap_bandwidth

    def compute_channel_spectrum(self, iq_data):
        """Compute power spectrum (dB) for a single channel's IQ data."""
        N = min(self.fft_size, len(iq_data))
        f, Pxx = signal.welch(
            iq_data,
            fs=self.channel_bandwidth,
            nperseg=N,
            nfft=N,
            detrend=False,
            return_onesided=False,
            window="blackman",
            scaling="spectrum",
        )
        # fftshift to put DC in center
        f = fft.fftshift(f)
        Pxx = fft.fftshift(Pxx)
        Pxx_dB = 10.0 * np.log10(np.maximum(Pxx, 1e-20))
        return f, Pxx_dB

    def stitch_spectra(self, channel_spectra, channel_rel_freqs, channel_center_freqs):
        """
        Stitch 5 per-channel spectra into one wideband spectrum.

        Uses linear crossfade blending in overlap regions between adjacent channels.
        """
        # Build the full frequency axis
        total_bw = self.total_bandwidth
        lowest_freq = self.center_freq - total_bw / 2
        highest_freq = self.center_freq + total_bw / 2

        # Output resolution: use the same bin spacing as individual channels
        bin_spacing = self.channel_bandwidth / self.fft_size
        num_bins = int(total_bw / bin_spacing)
        wideband_freqs = np.linspace(lowest_freq, highest_freq, num_bins)
        wideband_spectrum = np.full(num_bins, -200.0, dtype=np.float64)
        weight_sum = np.zeros(num_bins, dtype=np.float64)

        for ch_idx in range(self.num_channels):
            ch_center = channel_center_freqs[ch_idx]
            rel_freqs = channel_rel_freqs[ch_idx]
            spectrum = channel_spectra[ch_idx]

            # Absolute frequencies for this channel's bins
            abs_freqs = ch_center + rel_freqs

            # Create blend weights: taper the edges of each channel
            half_bw = self.channel_bandwidth / 2
            half_overlap = self.overlap_bandwidth / 2
            blend = np.ones(len(rel_freqs))

            if self.overlap_bandwidth > 0:
                # Taper left edge (except for leftmost channel)
                if ch_idx > 0:
                    left_taper_start = -half_bw
                    left_taper_end = -half_bw + self.overlap_bandwidth
                    mask = (rel_freqs >= left_taper_start) & (rel_freqs < left_taper_end)
                    if np.any(mask):
                        blend[mask] = np.linspace(0, 1, np.sum(mask))

                # Taper right edge (except for rightmost channel)
                if ch_idx < self.num_channels - 1:
                    right_taper_start = half_bw - self.overlap_bandwidth
                    right_taper_end = half_bw
                    mask = (rel_freqs > right_taper_start) & (rel_freqs <= right_taper_end)
                    if np.any(mask):
                        blend[mask] = np.linspace(1, 0, np.sum(mask))

            # Map channel bins into the wideband array
            for i in range(len(abs_freqs)):
                # Find nearest wideband bin
                idx = int((abs_freqs[i] - lowest_freq) / bin_spacing)
                if 0 <= idx < num_bins:
                    power_linear = 10.0 ** (spectrum[i] / 10.0) * blend[i]
                    if weight_sum[idx] == 0:
                        wideband_spectrum[idx] = power_linear
                    else:
                        wideband_spectrum[idx] += power_linear
                    weight_sum[idx] += blend[i]

        # Convert back to dB, avoiding division by zero
        valid = weight_sum > 0
        wideband_spectrum[valid] = 10.0 * np.log10(np.maximum(wideband_spectrum[valid] / weight_sum[valid], 1e-20))
        wideband_spectrum[~valid] = -200.0

        return wideband_freqs, wideband_spectrum

    def update_waterfall(self, spectrum):
        """Append new spectrum row to waterfall buffer."""
        if self.waterfall_buffer is None or self.waterfall_buffer.shape[1] != len(spectrum):
            self.waterfall_buffer = np.full((self.waterfall_depth, len(spectrum)), -200.0)

        self.waterfall_buffer = np.roll(self.waterfall_buffer, -1, axis=0)
        self.waterfall_buffer[-1, :] = spectrum

    def save_processing_status(self):
        """Serialize system status to JSON file."""
        status = {}
        status["timestamp_ms"] = int(time.time() * 1e3)
        status["hardware_id"] = self.module_receiver.iq_header.hardware_id.rstrip("\x00")
        status["unit_id"] = self.module_receiver.iq_header.unit_id
        status["host_os_type"] = SYSTEM_UNAME.system
        status["host_os_version"] = SYSTEM_UNAME.release
        status["host_os_architecture"] = SYSTEM_UNAME.machine
        status["software_version"] = SOFTWARE_VERSION
        status["software_git_short_hash"] = SOFTWARE_GIT_SHORT_HASH
        status["uptime_ms"] = int(time.monotonic() * 1e3)

        iq_header_empty = self.module_receiver.iq_header.frame_type == IQHeader.FRAME_TYPE_EMPTY

        daq_status = {}
        if not iq_header_empty:
            status["timestamp_ms"] = self.module_receiver.iq_header.time_stamp
            daq_status["data_frame_index"] = self.module_receiver.iq_header.cpi_index
            daq_status["frame_sync"] = not bool(self.module_receiver.iq_header.check_sync_word())
            daq_status["sample_delay_sync"] = bool(self.module_receiver.iq_header.delay_sync_flag)
            daq_status["iq_sync"] = bool(self.module_receiver.iq_header.iq_sync_flag)
            daq_status["noise_source_enabled"] = bool(self.module_receiver.iq_header.noise_source_state)
            daq_status["adc_overdrive"] = bool(self.module_receiver.iq_header.adc_overdrive_flags)
            daq_status["sampling_frequency_hz"] = self.module_receiver.iq_header.adc_sampling_freq
            daq_status["bandwidth_hz"] = self.module_receiver.iq_header.sampling_freq

        status["daq_status"] = daq_status
        status["daq_ok"] = (
            not iq_header_empty
            and daq_status.get("frame_sync", False)
            and daq_status.get("sample_delay_sync", False)
            and daq_status.get("iq_sync", False)
        )
        status["daq_num_dropped_frames"] = self.dropped_frames

        try:
            with open(status_file_path, "w", encoding="utf-8") as f:
                json.dump(status, f)
        except Exception:
            pass

    def run(self):
        """Main processing loop."""
        while True:
            self.is_running = False
            time.sleep(1)
            while self.run_processing:
                self.is_running = True
                que_data_packet = []

                # Acquire IQ data
                get_iq_failed = self.module_receiver.get_iq_online()
                start_time = time.time()

                self.save_processing_status()
                que_data_packet.append(["iq_header", self.module_receiver.iq_header])

                en_proc = self.module_receiver.iq_header.frame_type == IQHeader.FRAME_TYPE_DATA

                if not self.module_receiver.iq_samples.size and get_iq_failed:
                    if not self.dropped_frames:
                        self.logger.error("Data frame lost! Check USB, power supply, or CPU load.")
                    self.dropped_frames += 1
                elif en_proc:
                    # Initialize on first valid frame
                    if self.first_frame:
                        self.channel_number = self.module_receiver.iq_header.active_ant_chs
                        self.channel_bandwidth = float(self.module_receiver.iq_header.sampling_freq)
                        self.first_frame = False

                    iq_samples = np.ascontiguousarray(self.module_receiver.iq_samples)
                    sampling_freq = self.module_receiver.iq_header.sampling_freq

                    # Use actual sampling freq as channel bandwidth
                    self.channel_bandwidth = float(sampling_freq)
                    channel_center_freqs = self.channel_frequencies
                    active_channels = min(self.channel_number, self.num_channels)

                    # Compute per-channel spectra
                    channel_spectra = []
                    channel_rel_freqs = []
                    for ch in range(active_channels):
                        f, Pxx_dB = self.compute_channel_spectrum(iq_samples[ch, :])
                        channel_rel_freqs.append(f)
                        channel_spectra.append(Pxx_dB)

                    # Stitch into wideband spectrum
                    if active_channels > 1:
                        wideband_freqs, wideband_spectrum = self.stitch_spectra(
                            channel_spectra, channel_rel_freqs, channel_center_freqs[:active_channels]
                        )
                    else:
                        # Single channel fallback
                        wideband_freqs = channel_center_freqs[0] + channel_rel_freqs[0]
                        wideband_spectrum = channel_spectra[0]

                    self.wideband_freqs = wideband_freqs
                    self.wideband_spectrum = wideband_spectrum

                    # Update waterfall
                    self.update_waterfall(wideband_spectrum)

                    # Package results
                    que_data_packet.append(["spectrum", (wideband_freqs, wideband_spectrum)])
                    que_data_packet.append(["waterfall", self.waterfall_buffer.copy()])

                stop_time = time.time()
                self.processing_time = int(1000 * (stop_time - start_time))
                que_data_packet.append(["update_rate", stop_time - start_time])

                try:
                    self.data_que.put(que_data_packet, False)
                except Exception:
                    pass
