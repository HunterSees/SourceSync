"""
Shared Utilities for SyncStream

This module provides common utility functions for signal processing,
audio I/O, and other shared functionality used by both transmitter
and receiver components.
"""

import numpy as np
import time
import logging
import threading
from typing import Tuple, Optional, List, Dict, Any
from scipy import signal
from scipy.signal import butter, filtfilt, correlate
import json
import hashlib

logger = logging.getLogger(__name__)


class AudioUtils:
    """Utility functions for audio processing."""
    
    @staticmethod
    def normalize_audio(audio: np.ndarray, target_level: float = 0.9) -> np.ndarray:
        """
        Normalize audio to target level.
        
        Args:
            audio: Input audio array
            target_level: Target peak level (0.0 to 1.0)
        
        Returns:
            Normalized audio array
        """
        if len(audio) == 0:
            return audio
        
        # Find peak level
        peak = np.max(np.abs(audio))
        
        if peak > 0:
            # Scale to target level
            scale_factor = target_level / peak
            return audio * scale_factor
        else:
            return audio
    
    @staticmethod
    def apply_fade(audio: np.ndarray, fade_duration: float, 
                   sample_rate: int, fade_type: str = 'both') -> np.ndarray:
        """
        Apply fade in/out to audio.
        
        Args:
            audio: Input audio array
            fade_duration: Fade duration in seconds
            sample_rate: Audio sample rate
            fade_type: 'in', 'out', or 'both'
        
        Returns:
            Audio with fade applied
        """
        fade_samples = int(fade_duration * sample_rate)
        fade_samples = min(fade_samples, len(audio) // 2)
        
        if fade_samples <= 0:
            return audio
        
        result = audio.copy()
        
        # Create fade curve (cosine)
        fade_curve = 0.5 * (1 - np.cos(np.pi * np.arange(fade_samples) / fade_samples))
        
        if fade_type in ['in', 'both']:
            # Fade in
            if len(result.shape) == 1:
                result[:fade_samples] *= fade_curve
            else:
                result[:fade_samples] *= fade_curve.reshape(-1, 1)
        
        if fade_type in ['out', 'both']:
            # Fade out
            if len(result.shape) == 1:
                result[-fade_samples:] *= fade_curve[::-1]
            else:
                result[-fade_samples:] *= fade_curve[::-1].reshape(-1, 1)
        
        return result
    
    @staticmethod
    def convert_to_mono(audio: np.ndarray) -> np.ndarray:
        """
        Convert stereo audio to mono.
        
        Args:
            audio: Input audio array (mono or stereo)
        
        Returns:
            Mono audio array
        """
        if len(audio.shape) == 1:
            return audio  # Already mono
        elif audio.shape[1] == 1:
            return audio.flatten()  # Mono in 2D format
        else:
            # Convert stereo to mono by averaging channels
            return np.mean(audio, axis=1)
    
    @staticmethod
    def convert_to_stereo(audio: np.ndarray) -> np.ndarray:
        """
        Convert mono audio to stereo.
        
        Args:
            audio: Input audio array (mono)
        
        Returns:
            Stereo audio array
        """
        if len(audio.shape) == 2 and audio.shape[1] == 2:
            return audio  # Already stereo
        
        # Duplicate mono channel to create stereo
        mono = audio.flatten() if len(audio.shape) == 2 else audio
        return np.column_stack([mono, mono])
    
    @staticmethod
    def apply_highpass_filter(audio: np.ndarray, cutoff_hz: float, 
                             sample_rate: int, order: int = 4) -> np.ndarray:
        """
        Apply high-pass filter to audio.
        
        Args:
            audio: Input audio array
            cutoff_hz: Cutoff frequency in Hz
            sample_rate: Audio sample rate
            order: Filter order
        
        Returns:
            Filtered audio array
        """
        try:
            nyquist = sample_rate / 2
            normalized_cutoff = cutoff_hz / nyquist
            
            if normalized_cutoff >= 1.0:
                logger.warning(f"Cutoff frequency {cutoff_hz}Hz too high for sample rate {sample_rate}Hz")
                return audio
            
            b, a = butter(order, normalized_cutoff, btype='high')
            
            if len(audio.shape) == 1:
                return filtfilt(b, a, audio)
            else:
                # Apply filter to each channel
                filtered = np.zeros_like(audio)
                for ch in range(audio.shape[1]):
                    filtered[:, ch] = filtfilt(b, a, audio[:, ch])
                return filtered
                
        except Exception as e:
            logger.error(f"Failed to apply high-pass filter: {e}")
            return audio
    
    @staticmethod
    def apply_lowpass_filter(audio: np.ndarray, cutoff_hz: float,
                            sample_rate: int, order: int = 4) -> np.ndarray:
        """
        Apply low-pass filter to audio.
        
        Args:
            audio: Input audio array
            cutoff_hz: Cutoff frequency in Hz
            sample_rate: Audio sample rate
            order: Filter order
        
        Returns:
            Filtered audio array
        """
        try:
            nyquist = sample_rate / 2
            normalized_cutoff = cutoff_hz / nyquist
            
            if normalized_cutoff >= 1.0:
                logger.warning(f"Cutoff frequency {cutoff_hz}Hz too high for sample rate {sample_rate}Hz")
                return audio
            
            b, a = butter(order, normalized_cutoff, btype='low')
            
            if len(audio.shape) == 1:
                return filtfilt(b, a, audio)
            else:
                # Apply filter to each channel
                filtered = np.zeros_like(audio)
                for ch in range(audio.shape[1]):
                    filtered[:, ch] = filtfilt(b, a, audio[:, ch])
                return filtered
                
        except Exception as e:
            logger.error(f"Failed to apply low-pass filter: {e}")
            return audio
    
    @staticmethod
    def calculate_rms(audio: np.ndarray) -> float:
        """
        Calculate RMS (Root Mean Square) level of audio.
        
        Args:
            audio: Input audio array
        
        Returns:
            RMS level
        """
        if len(audio) == 0:
            return 0.0
        
        return np.sqrt(np.mean(audio**2))
    
    @staticmethod
    def calculate_peak(audio: np.ndarray) -> float:
        """
        Calculate peak level of audio.
        
        Args:
            audio: Input audio array
        
        Returns:
            Peak level
        """
        if len(audio) == 0:
            return 0.0
        
        return np.max(np.abs(audio))
    
    @staticmethod
    def generate_test_tone(frequency: float, duration: float, 
                          sample_rate: int = 44100, amplitude: float = 0.5) -> np.ndarray:
        """
        Generate a test tone.
        
        Args:
            frequency: Tone frequency in Hz
            duration: Duration in seconds
            sample_rate: Sample rate in Hz
            amplitude: Amplitude (0.0 to 1.0)
        
        Returns:
            Generated tone as numpy array
        """
        samples = int(duration * sample_rate)
        t = np.linspace(0, duration, samples, endpoint=False)
        tone = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # Apply fade to avoid clicks
        return AudioUtils.apply_fade(tone, 0.01, sample_rate, 'both')


class CorrelationUtils:
    """Utility functions for audio correlation and drift detection."""
    
    @staticmethod
    def cross_correlate(signal1: np.ndarray, signal2: np.ndarray,
                       max_lag: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute cross-correlation between two signals.
        
        Args:
            signal1: First signal
            signal2: Second signal
            max_lag: Maximum lag to compute (None for full correlation)
        
        Returns:
            Tuple of (correlation, lags)
        """
        # Ensure signals are 1D
        sig1 = AudioUtils.convert_to_mono(signal1)
        sig2 = AudioUtils.convert_to_mono(signal2)
        
        # Compute full cross-correlation
        correlation = correlate(sig1, sig2, mode='full')
        
        # Create lag array
        lags = np.arange(-len(sig2) + 1, len(sig1))
        
        # Limit to max_lag if specified
        if max_lag is not None:
            center = len(correlation) // 2
            start = max(0, center - max_lag)
            end = min(len(correlation), center + max_lag + 1)
            
            correlation = correlation[start:end]
            lags = lags[start:end]
        
        return correlation, lags
    
    @staticmethod
    def find_peak_correlation(correlation: np.ndarray, lags: np.ndarray,
                             min_correlation: float = 0.1) -> Tuple[int, float]:
        """
        Find peak correlation and corresponding lag.
        
        Args:
            correlation: Correlation array
            lags: Lag array
            min_correlation: Minimum correlation threshold
        
        Returns:
            Tuple of (lag, correlation_value)
        """
        # Find peak
        peak_idx = np.argmax(np.abs(correlation))
        peak_lag = lags[peak_idx]
        peak_correlation = correlation[peak_idx]
        
        # Normalize correlation
        max_possible = np.sqrt(np.sum(correlation**2))
        if max_possible > 0:
            normalized_correlation = abs(peak_correlation) / max_possible
        else:
            normalized_correlation = 0.0
        
        # Check threshold
        if normalized_correlation < min_correlation:
            logger.debug(f"Correlation {normalized_correlation:.3f} below threshold {min_correlation}")
            return 0, 0.0
        
        return peak_lag, normalized_correlation
    
    @staticmethod
    def estimate_drift(mic_audio: np.ndarray, ref_audio: np.ndarray,
                      sample_rate: int, max_drift_ms: float = 1000.0) -> Tuple[float, float]:
        """
        Estimate drift between microphone and reference audio.
        
        Args:
            mic_audio: Microphone audio
            ref_audio: Reference audio
            sample_rate: Sample rate
            max_drift_ms: Maximum expected drift in milliseconds
        
        Returns:
            Tuple of (drift_ms, correlation)
        """
        # Preprocess signals
        mic_processed = AudioUtils.apply_highpass_filter(mic_audio, 100, sample_rate)
        ref_processed = AudioUtils.apply_highpass_filter(ref_audio, 100, sample_rate)
        
        # Normalize
        mic_processed = AudioUtils.normalize_audio(mic_processed, 0.9)
        ref_processed = AudioUtils.normalize_audio(ref_processed, 0.9)
        
        # Calculate maximum lag in samples
        max_lag_samples = int((max_drift_ms / 1000.0) * sample_rate)
        
        # Compute cross-correlation
        correlation, lags = CorrelationUtils.cross_correlate(
            mic_processed, ref_processed, max_lag_samples
        )
        
        # Find peak
        lag_samples, corr_value = CorrelationUtils.find_peak_correlation(
            correlation, lags, min_correlation=0.1
        )
        
        # Convert lag to milliseconds
        drift_ms = (lag_samples / sample_rate) * 1000.0
        
        return drift_ms, corr_value


class NetworkUtils:
    """Utility functions for network operations."""
    
    @staticmethod
    def get_local_ip() -> Optional[str]:
        """Get local IP address."""
        import socket
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return None
    
    @staticmethod
    def check_port_open(host: str, port: int, timeout: float = 3.0) -> bool:
        """Check if a port is open on a host."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                result = s.connect_ex((host, port))
                return result == 0
        except Exception:
            return False
    
    @staticmethod
    def discover_devices(port: int, timeout: float = 5.0) -> List[str]:
        """Discover devices on local network by scanning for open ports."""
        import socket
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        local_ip = NetworkUtils.get_local_ip()
        if not local_ip:
            return []
        
        # Get network prefix (e.g., 192.168.1.)
        network_prefix = '.'.join(local_ip.split('.')[:-1]) + '.'
        
        devices = []
        
        def check_host(ip):
            if NetworkUtils.check_port_open(ip, port, timeout=1.0):
                return ip
            return None
        
        # Scan network range
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for i in range(1, 255):
                ip = network_prefix + str(i)
                futures.append(executor.submit(check_host, ip))
            
            for future in as_completed(futures, timeout=timeout):
                try:
                    result = future.result()
                    if result:
                        devices.append(result)
                except Exception:
                    pass
        
        return devices


class ConfigUtils:
    """Utility functions for configuration management."""
    
    @staticmethod
    def load_json_config(filename: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {filename}: {e}")
            return {}
    
    @staticmethod
    def save_json_config(config: Dict[str, Any], filename: str) -> bool:
        """Save configuration to JSON file."""
        try:
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save config to {filename}: {e}")
            return False
    
    @staticmethod
    def merge_configs(base_config: Dict[str, Any], 
                     override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configuration dictionaries."""
        result = base_config.copy()
        
        for key, value in override_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigUtils.merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def validate_config(config: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Validate configuration against schema."""
        errors = []
        
        def validate_recursive(cfg, sch, path=""):
            for key, expected_type in sch.items():
                current_path = f"{path}.{key}" if path else key
                
                if key not in cfg:
                    errors.append(f"Missing required key: {current_path}")
                    continue
                
                value = cfg[key]
                
                if isinstance(expected_type, dict):
                    if not isinstance(value, dict):
                        errors.append(f"Expected dict for {current_path}, got {type(value).__name__}")
                    else:
                        validate_recursive(value, expected_type, current_path)
                elif not isinstance(value, expected_type):
                    errors.append(f"Expected {expected_type.__name__} for {current_path}, "
                                f"got {type(value).__name__}")
        
        validate_recursive(config, schema)
        return errors


class TimingUtils:
    """Utility functions for timing and synchronization."""
    
    @staticmethod
    def get_timestamp_ms() -> int:
        """Get current timestamp in milliseconds."""
        return int(time.time() * 1000)
    
    @staticmethod
    def sleep_until(target_time: float) -> None:
        """Sleep until a specific time."""
        current_time = time.time()
        if target_time > current_time:
            time.sleep(target_time - current_time)
    
    @staticmethod
    def create_timer(interval: float, callback, *args, **kwargs) -> threading.Timer:
        """Create a repeating timer."""
        def timer_callback():
            callback(*args, **kwargs)
            # Schedule next execution
            timer = TimingUtils.create_timer(interval, callback, *args, **kwargs)
            timer.start()
        
        timer = threading.Timer(interval, timer_callback)
        return timer


class HashUtils:
    """Utility functions for hashing and checksums."""
    
    @staticmethod
    def calculate_audio_hash(audio: np.ndarray) -> str:
        """Calculate hash of audio data for comparison."""
        # Convert to bytes
        audio_bytes = audio.astype(np.float32).tobytes()
        
        # Calculate SHA-256 hash
        hash_obj = hashlib.sha256(audio_bytes)
        return hash_obj.hexdigest()
    
    @staticmethod
    def calculate_config_hash(config: Dict[str, Any]) -> str:
        """Calculate hash of configuration for change detection."""
        # Convert to JSON string with sorted keys
        config_str = json.dumps(config, sort_keys=True)
        
        # Calculate SHA-256 hash
        hash_obj = hashlib.sha256(config_str.encode('utf-8'))
        return hash_obj.hexdigest()


if __name__ == "__main__":
    # Test utilities
    logging.basicConfig(level=logging.DEBUG)
    
    print("Testing SyncStream utilities...")
    
    # Test audio utilities
    print("\n1. Testing audio utilities...")
    test_tone = AudioUtils.generate_test_tone(440, 1.0, 44100, 0.5)
    print(f"Generated test tone: {test_tone.shape}, RMS: {AudioUtils.calculate_rms(test_tone):.4f}")
    
    # Test correlation utilities
    print("\n2. Testing correlation utilities...")
    # Create two similar signals with offset
    signal1 = AudioUtils.generate_test_tone(440, 2.0, 44100, 0.5)
    signal2 = np.concatenate([np.zeros(1000), signal1[:-1000]])  # 1000 sample delay
    
    drift_ms, correlation = CorrelationUtils.estimate_drift(signal1, signal2, 44100)
    print(f"Estimated drift: {drift_ms:.1f}ms, correlation: {correlation:.3f}")
    
    # Test network utilities
    print("\n3. Testing network utilities...")
    local_ip = NetworkUtils.get_local_ip()
    print(f"Local IP: {local_ip}")
    
    # Test config utilities
    print("\n4. Testing config utilities...")
    test_config = {
        "device_id": "test",
        "audio": {
            "sample_rate": 44100,
            "channels": 2
        }
    }
    
    config_hash = HashUtils.calculate_config_hash(test_config)
    print(f"Config hash: {config_hash[:16]}...")
    
    print("\nAll utility tests completed!")

