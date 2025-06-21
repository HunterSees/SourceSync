"""
Drift Detector Module for SyncStream Receiver Node

This module measures audio drift by comparing microphone input
with reference audio from the transmitter using cross-correlation.
"""

import time
import logging
import numpy as np
import requests
import threading
from typing import Optional, Tuple, Dict, Any
from scipy import signal
from scipy.signal import correlate, find_peaks
import json

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Detects audio drift by correlating microphone input with reference audio.
    
    Uses cross-correlation to find the time offset between the local audio
    output (captured by microphone) and the reference audio from transmitter.
    """
    
    def __init__(self, transmitter_host: str = "localhost", 
                 transmitter_port: int = 8080, correlation_window: float = 2.0,
                 min_correlation: float = 0.7, max_drift_ms: float = 1000.0):
        """
        Initialize drift detector.
        
        Args:
            transmitter_host: Hostname of transmitter
            transmitter_port: Port of transmitter HTTP API
            correlation_window: Duration of audio to use for correlation (seconds)
            min_correlation: Minimum correlation coefficient for valid measurement
            max_drift_ms: Maximum expected drift in milliseconds
        """
        self.transmitter_host = transmitter_host
        self.transmitter_port = transmitter_port
        self.correlation_window = correlation_window
        self.min_correlation = min_correlation
        self.max_drift_ms = max_drift_ms
        
        # API endpoints
        self.base_url = f"http://{transmitter_host}:{transmitter_port}"
        self.audio_endpoint = f"{self.base_url}/api/audio/buffer"
        
        # Drift measurement state
        self.last_drift_ms = 0.0
        self.last_correlation = 0.0
        self.last_measurement_time = 0.0
        self.measurement_count = 0
        
        # Statistics
        self.drift_history = []
        self.correlation_history = []
        self.failed_measurements = 0
        
        # Threading
        self.measurement_lock = threading.Lock()
        
        logger.info(f"DriftDetector initialized: transmitter={transmitter_host}:{transmitter_port}, "
                   f"window={correlation_window}s, min_corr={min_correlation}")
    
    def _fetch_reference_audio(self, duration: float, offset: float = 0.0) -> Optional[np.ndarray]:
        """
        Fetch reference audio from transmitter.
        
        Args:
            duration: Duration of audio to fetch (seconds)
            offset: Time offset from current position (seconds, negative = past)
        
        Returns:
            Reference audio as numpy array, or None if fetch failed
        """
        try:
            params = {
                'duration': duration,
                'offset': offset,
                'format': 'raw'
            }
            
            response = requests.get(self.audio_endpoint, params=params, timeout=5.0)
            response.raise_for_status()
            
            # Parse response
            if response.headers.get('content-type') == 'application/octet-stream':
                # Raw audio data
                audio_data = np.frombuffer(response.content, dtype=np.float32)
                
                # Get metadata from headers
                sample_rate = int(response.headers.get('X-Sample-Rate', 44100))
                channels = int(response.headers.get('X-Channels', 2))
                
                # Reshape based on channels
                if channels == 2:
                    audio_data = audio_data.reshape(-1, 2)
                    # Convert to mono for correlation
                    audio_data = np.mean(audio_data, axis=1)
                
                return audio_data
            else:
                # JSON response with audio data
                data = response.json()
                audio_array = np.array(data['audio_data'], dtype=np.float32)
                
                if len(audio_array.shape) == 2 and audio_array.shape[1] == 2:
                    # Convert stereo to mono
                    audio_array = np.mean(audio_array, axis=1)
                
                return audio_array
                
        except requests.RequestException as e:
            logger.error(f"Failed to fetch reference audio: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing reference audio: {e}")
            return None
    
    def _preprocess_audio(self, audio: np.ndarray, sample_rate: int = 44100) -> np.ndarray:
        """
        Preprocess audio for correlation analysis.
        
        Args:
            audio: Input audio array
            sample_rate: Sample rate of audio
        
        Returns:
            Preprocessed audio array
        """
        # Ensure mono
        if len(audio.shape) == 2:
            audio = np.mean(audio, axis=1)
        
        # Apply high-pass filter to remove DC and low-frequency noise
        nyquist = sample_rate / 2
        high_cutoff = 100.0 / nyquist  # 100 Hz high-pass
        
        try:
            b, a = signal.butter(4, high_cutoff, btype='high')
            audio = signal.filtfilt(b, a, audio)
        except Exception as e:
            logger.warning(f"Failed to apply high-pass filter: {e}")
        
        # Normalize amplitude
        if np.max(np.abs(audio)) > 0:
            audio = audio / np.max(np.abs(audio))
        
        # Apply window function to reduce edge effects
        window = signal.windows.hann(len(audio))
        audio = audio * window
        
        return audio
    
    def _calculate_correlation(self, mic_audio: np.ndarray, ref_audio: np.ndarray,
                             sample_rate: int = 44100) -> Tuple[float, float]:
        """
        Calculate cross-correlation between microphone and reference audio.
        
        Args:
            mic_audio: Microphone audio array
            ref_audio: Reference audio array
            sample_rate: Sample rate of audio
        
        Returns:
            Tuple of (drift_ms, correlation_coefficient)
        """
        # Preprocess both signals
        mic_processed = self._preprocess_audio(mic_audio, sample_rate)
        ref_processed = self._preprocess_audio(ref_audio, sample_rate)
        
        # Ensure same length (use shorter length)
        min_length = min(len(mic_processed), len(ref_processed))
        mic_processed = mic_processed[:min_length]
        ref_processed = ref_processed[:min_length]
        
        # Calculate cross-correlation
        correlation = correlate(mic_processed, ref_processed, mode='full')
        
        # Find peak correlation
        peak_index = np.argmax(np.abs(correlation))
        peak_correlation = correlation[peak_index]
        
        # Calculate time offset
        offset_samples = peak_index - (len(ref_processed) - 1)
        offset_ms = (offset_samples / sample_rate) * 1000.0
        
        # Normalize correlation coefficient
        norm_factor = np.sqrt(np.sum(mic_processed**2) * np.sum(ref_processed**2))
        if norm_factor > 0:
            correlation_coeff = abs(peak_correlation) / norm_factor
        else:
            correlation_coeff = 0.0
        
        logger.debug(f"Correlation: offset={offset_ms:.1f}ms, coeff={correlation_coeff:.3f}")
        
        return offset_ms, correlation_coeff
    
    def _validate_drift_measurement(self, drift_ms: float, correlation: float) -> bool:
        """
        Validate drift measurement for reasonableness.
        
        Args:
            drift_ms: Measured drift in milliseconds
            correlation: Correlation coefficient
        
        Returns:
            True if measurement is valid
        """
        # Check correlation threshold
        if correlation < self.min_correlation:
            logger.debug(f"Correlation too low: {correlation:.3f} < {self.min_correlation}")
            return False
        
        # Check drift magnitude
        if abs(drift_ms) > self.max_drift_ms:
            logger.debug(f"Drift too large: {abs(drift_ms):.1f}ms > {self.max_drift_ms}ms")
            return False
        
        # Check for sudden jumps (if we have history)
        if len(self.drift_history) > 0:
            last_drift = self.drift_history[-1]
            drift_change = abs(drift_ms - last_drift)
            max_change = 100.0  # Maximum allowed change in ms
            
            if drift_change > max_change:
                logger.debug(f"Drift change too large: {drift_change:.1f}ms > {max_change}ms")
                return False
        
        return True
    
    def measure_drift(self, mic_audio: np.ndarray, sample_rate: int = 44100) -> Optional[Dict[str, Any]]:
        """
        Measure drift using microphone audio and reference from transmitter.
        
        Args:
            mic_audio: Microphone audio array
            sample_rate: Sample rate of microphone audio
        
        Returns:
            Dictionary with drift measurement results, or None if measurement failed
        """
        with self.measurement_lock:
            measurement_time = time.time()
            
            try:
                # Fetch reference audio from transmitter
                ref_audio = self._fetch_reference_audio(
                    duration=self.correlation_window,
                    offset=-0.5  # Fetch slightly in the past to account for network delay
                )
                
                if ref_audio is None:
                    self.failed_measurements += 1
                    logger.warning("Failed to fetch reference audio")
                    return None
                
                # Calculate correlation and drift
                drift_ms, correlation = self._calculate_correlation(
                    mic_audio, ref_audio, sample_rate
                )
                
                # Validate measurement
                if not self._validate_drift_measurement(drift_ms, correlation):
                    self.failed_measurements += 1
                    logger.debug("Drift measurement validation failed")
                    return None
                
                # Update state
                self.last_drift_ms = drift_ms
                self.last_correlation = correlation
                self.last_measurement_time = measurement_time
                self.measurement_count += 1
                
                # Update history
                self.drift_history.append(drift_ms)
                self.correlation_history.append(correlation)
                
                # Keep history limited
                max_history = 100
                if len(self.drift_history) > max_history:
                    self.drift_history = self.drift_history[-max_history:]
                    self.correlation_history = self.correlation_history[-max_history:]
                
                # Calculate statistics
                avg_drift = np.mean(self.drift_history[-10:])  # Average of last 10 measurements
                drift_variance = np.var(self.drift_history[-10:]) if len(self.drift_history) >= 2 else 0.0
                
                result = {
                    'drift_ms': drift_ms,
                    'correlation': correlation,
                    'avg_drift_ms': avg_drift,
                    'drift_variance': drift_variance,
                    'measurement_time': measurement_time,
                    'measurement_count': self.measurement_count,
                    'is_valid': True
                }
                
                logger.info(f"Drift measured: {drift_ms:.1f}ms (corr={correlation:.3f}, "
                           f"avg={avg_drift:.1f}ms)")
                
                return result
                
            except Exception as e:
                self.failed_measurements += 1
                logger.error(f"Error measuring drift: {e}")
                return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get drift detector statistics."""
        with self.measurement_lock:
            stats = {
                'transmitter_host': self.transmitter_host,
                'transmitter_port': self.transmitter_port,
                'correlation_window': self.correlation_window,
                'min_correlation': self.min_correlation,
                'last_drift_ms': self.last_drift_ms,
                'last_correlation': self.last_correlation,
                'last_measurement_time': self.last_measurement_time,
                'measurement_count': self.measurement_count,
                'failed_measurements': self.failed_measurements,
                'history_length': len(self.drift_history)
            }
            
            if len(self.drift_history) > 0:
                stats['avg_drift_ms'] = np.mean(self.drift_history)
                stats['drift_std_ms'] = np.std(self.drift_history)
                stats['min_drift_ms'] = np.min(self.drift_history)
                stats['max_drift_ms'] = np.max(self.drift_history)
                
            if len(self.correlation_history) > 0:
                stats['avg_correlation'] = np.mean(self.correlation_history)
                stats['min_correlation'] = np.min(self.correlation_history)
                
            return stats
    
    def reset_statistics(self) -> None:
        """Reset drift measurement statistics."""
        with self.measurement_lock:
            self.drift_history.clear()
            self.correlation_history.clear()
            self.measurement_count = 0
            self.failed_measurements = 0
            logger.info("Drift detector statistics reset")


if __name__ == "__main__":
    # Test drift detector
    logging.basicConfig(level=logging.DEBUG)
    
    # Create drift detector
    detector = DriftDetector(
        transmitter_host="localhost",
        transmitter_port=8080,
        correlation_window=2.0,
        min_correlation=0.5
    )
    
    # Generate test microphone audio (sine wave with noise)
    sample_rate = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create test signal: 440Hz sine wave + noise
    test_signal = (np.sin(2 * np.pi * 440 * t) + 
                   0.1 * np.random.randn(len(t))).astype(np.float32)
    
    print("Testing drift detector...")
    print("Note: This test requires a running transmitter with audio buffer API")
    
    # Attempt drift measurement
    result = detector.measure_drift(test_signal, sample_rate)
    
    if result:
        print(f"Drift measurement successful:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print("Drift measurement failed (transmitter not available)")
    
    # Print statistics
    stats = detector.get_statistics()
    print(f"\nDrift detector statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

