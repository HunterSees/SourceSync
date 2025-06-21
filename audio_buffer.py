"""
Audio Buffer Module for SyncStream Transmitter Host

This module provides a rolling memory buffer for audio data that allows
receivers to fetch historical audio samples for drift detection and synchronization.
"""

import threading
import time
import numpy as np
from collections import deque
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class AudioBuffer:
    """
    Rolling audio buffer that stores the last N seconds of audio data in memory.
    
    This buffer is thread-safe and allows multiple receivers to fetch
    historical audio samples for drift detection.
    """
    
    def __init__(self, sample_rate: int = 44100, buffer_duration: float = 10.0, 
                 channels: int = 2, dtype=np.float32):
        """
        Initialize the audio buffer.
        
        Args:
            sample_rate: Audio sample rate in Hz
            buffer_duration: Duration of audio to keep in buffer (seconds)
            channels: Number of audio channels
            dtype: NumPy data type for audio samples
        """
        self.sample_rate = sample_rate
        self.buffer_duration = buffer_duration
        self.channels = channels
        self.dtype = dtype
        
        # Calculate buffer size in samples
        self.buffer_size = int(sample_rate * buffer_duration)
        
        # Initialize circular buffer
        self.buffer = np.zeros((self.buffer_size, channels), dtype=dtype)
        self.write_index = 0
        self.samples_written = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Timing information
        self.start_time = time.time()
        self.last_write_time = self.start_time
        
        logger.info(f"AudioBuffer initialized: {sample_rate}Hz, {buffer_duration}s, "
                   f"{channels} channels, {self.buffer_size} samples")
    
    def write(self, audio_data: np.ndarray) -> None:
        """
        Write audio data to the buffer.
        
        Args:
            audio_data: Audio samples as numpy array, shape (samples, channels)
        """
        with self.lock:
            current_time = time.time()
            
            # Ensure audio_data has correct shape
            if audio_data.ndim == 1:
                audio_data = audio_data.reshape(-1, 1)
            if audio_data.shape[1] != self.channels:
                # Convert mono to stereo or vice versa as needed
                if self.channels == 2 and audio_data.shape[1] == 1:
                    audio_data = np.repeat(audio_data, 2, axis=1)
                elif self.channels == 1 and audio_data.shape[1] == 2:
                    audio_data = np.mean(audio_data, axis=1, keepdims=True)
            
            num_samples = audio_data.shape[0]
            
            # Write samples to circular buffer
            for i in range(num_samples):
                self.buffer[self.write_index] = audio_data[i]
                self.write_index = (self.write_index + 1) % self.buffer_size
                self.samples_written += 1
            
            self.last_write_time = current_time
            
            logger.debug(f"Wrote {num_samples} samples to buffer, "
                        f"total written: {self.samples_written}")
    
    def read(self, duration: float, offset: float = 0.0) -> Tuple[np.ndarray, float]:
        """
        Read audio data from the buffer.
        
        Args:
            duration: Duration of audio to read (seconds)
            offset: Time offset from current position (seconds, negative = past)
        
        Returns:
            Tuple of (audio_data, timestamp) where timestamp is the start time
            of the returned audio data relative to buffer start
        """
        with self.lock:
            num_samples = int(duration * self.sample_rate)
            offset_samples = int(offset * self.sample_rate)
            
            # Calculate start position in buffer
            current_pos = self.write_index
            start_pos = (current_pos - num_samples + offset_samples) % self.buffer_size
            
            # Check if we have enough data
            available_samples = min(self.samples_written, self.buffer_size)
            if num_samples > available_samples:
                logger.warning(f"Requested {num_samples} samples but only "
                             f"{available_samples} available")
                num_samples = available_samples
            
            # Read samples from circular buffer
            audio_data = np.zeros((num_samples, self.channels), dtype=self.dtype)
            
            for i in range(num_samples):
                read_pos = (start_pos + i) % self.buffer_size
                audio_data[i] = self.buffer[read_pos]
            
            # Calculate timestamp
            samples_from_start = self.samples_written - num_samples + offset_samples
            timestamp = samples_from_start / self.sample_rate
            
            logger.debug(f"Read {num_samples} samples from buffer, "
                        f"timestamp: {timestamp:.3f}s")
            
            return audio_data, timestamp
    
    def get_latest(self, duration: float) -> Tuple[np.ndarray, float]:
        """
        Get the most recent audio data from the buffer.
        
        Args:
            duration: Duration of audio to read (seconds)
        
        Returns:
            Tuple of (audio_data, timestamp)
        """
        return self.read(duration, offset=0.0)
    
    def get_buffer_info(self) -> dict:
        """
        Get information about the current buffer state.
        
        Returns:
            Dictionary with buffer statistics
        """
        with self.lock:
            current_time = time.time()
            buffer_fill = min(self.samples_written, self.buffer_size) / self.buffer_size
            
            return {
                'sample_rate': self.sample_rate,
                'channels': self.channels,
                'buffer_duration': self.buffer_duration,
                'buffer_size': self.buffer_size,
                'samples_written': self.samples_written,
                'buffer_fill': buffer_fill,
                'uptime': current_time - self.start_time,
                'last_write_time': self.last_write_time,
                'time_since_last_write': current_time - self.last_write_time
            }
    
    def clear(self) -> None:
        """Clear the buffer and reset counters."""
        with self.lock:
            self.buffer.fill(0)
            self.write_index = 0
            self.samples_written = 0
            self.start_time = time.time()
            self.last_write_time = self.start_time
            logger.info("Audio buffer cleared")


if __name__ == "__main__":
    # Test the audio buffer
    logging.basicConfig(level=logging.DEBUG)
    
    # Create buffer
    buffer = AudioBuffer(sample_rate=44100, buffer_duration=5.0, channels=2)
    
    # Generate test audio (sine wave)
    duration = 2.0
    t = np.linspace(0, duration, int(44100 * duration))
    test_audio = np.column_stack([
        np.sin(2 * np.pi * 440 * t),  # 440 Hz sine wave
        np.sin(2 * np.pi * 880 * t)   # 880 Hz sine wave
    ]).astype(np.float32)
    
    # Write test audio
    buffer.write(test_audio)
    
    # Read back audio
    read_audio, timestamp = buffer.get_latest(1.0)
    print(f"Read audio shape: {read_audio.shape}, timestamp: {timestamp}")
    
    # Print buffer info
    info = buffer.get_buffer_info()
    for key, value in info.items():
        print(f"{key}: {value}")

