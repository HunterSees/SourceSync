"""
Microphone Capture Module for SyncStream Receiver Node

This module captures audio from an I²S digital microphone (INMP441 or SPH0645)
connected to the Raspberry Pi GPIO pins for drift detection.
"""

import time
import logging
import threading
import numpy as np
from typing import Optional, Callable
import queue
import subprocess
import os

logger = logging.getLogger(__name__)


class I2SMicCapture:
    """
    Captures audio from I²S digital microphone using ALSA.
    
    Supports INMP441 and SPH0645 microphones connected via GPIO.
    """
    
    def __init__(self, sample_rate: int = 44100, channels: int = 1, 
                 device_name: str = "hw:1,0", chunk_duration: float = 0.1):
        """
        Initialize I²S microphone capture.
        
        Args:
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels (1 for mono, 2 for stereo)
            device_name: ALSA device name for I²S microphone
            chunk_duration: Duration of each audio chunk in seconds
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_name = device_name
        self.chunk_duration = chunk_duration
        self.chunk_frames = int(sample_rate * chunk_duration)
        
        # Capture state
        self.is_capturing = False
        self.capture_process = None
        self.audio_queue = queue.Queue(maxsize=50)
        self.reader_thread = None
        
        # Statistics
        self.chunks_captured = 0
        self.bytes_captured = 0
        self.start_time = 0.0
        self.last_capture_time = 0.0
        
        logger.info(f"I2SMicCapture initialized: {sample_rate}Hz, {channels}ch, "
                   f"device={device_name}, chunk_duration={chunk_duration}s")
    
    def _check_i2s_setup(self) -> bool:
        """Check if I²S is properly configured."""
        try:
            # Check if I²S device exists
            result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
            if self.device_name.replace('hw:', '') not in result.stdout:
                logger.warning(f"I²S device {self.device_name} not found in audio devices")
                return False
            
            # Check if I²S overlay is loaded
            if os.path.exists('/proc/device-tree/soc/i2s@7e203000/status'):
                with open('/proc/device-tree/soc/i2s@7e203000/status', 'r') as f:
                    status = f.read().strip()
                    if status != 'okay':
                        logger.warning("I²S overlay not properly loaded")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking I²S setup: {e}")
            return False
    
    def start_capture(self) -> bool:
        """Start microphone capture."""
        if self.is_capturing:
            logger.warning("Microphone capture already running")
            return True
        
        # Check I²S setup
        if not self._check_i2s_setup():
            logger.error("I²S not properly configured")
            return False
        
        try:
            # Start arecord process to capture audio
            cmd = [
                'arecord',
                '-D', self.device_name,
                '-f', 'S32_LE',  # 32-bit signed little-endian
                '-r', str(self.sample_rate),
                '-c', str(self.channels),
                '-t', 'raw'
            ]
            
            self.capture_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            # Start reader thread
            self.is_capturing = True
            self.start_time = time.time()
            self.chunks_captured = 0
            self.bytes_captured = 0
            
            self.reader_thread = threading.Thread(target=self._read_audio_data)
            self.reader_thread.daemon = True
            self.reader_thread.start()
            
            logger.info(f"Started I²S microphone capture: {self.device_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start microphone capture: {e}")
            return False
    
    def stop_capture(self) -> None:
        """Stop microphone capture."""
        if not self.is_capturing:
            return
        
        self.is_capturing = False
        
        # Terminate capture process
        if self.capture_process:
            self.capture_process.terminate()
            self.capture_process.wait()
            self.capture_process = None
        
        # Wait for reader thread
        if self.reader_thread:
            self.reader_thread.join(timeout=5.0)
        
        logger.info("Stopped I²S microphone capture")
    
    def _read_audio_data(self) -> None:
        """Read audio data from capture process in background thread."""
        chunk_size = self.chunk_frames * self.channels * 4  # 4 bytes per 32-bit sample
        
        while self.is_capturing and self.capture_process:
            try:
                data = self.capture_process.stdout.read(chunk_size)
                if not data:
                    break
                
                # Convert to numpy array (32-bit int to float32)
                audio_array = np.frombuffer(data, dtype=np.int32).astype(np.float32) / (2**31)
                
                if self.channels == 2:
                    audio_array = audio_array.reshape(-1, 2)
                else:
                    audio_array = audio_array.reshape(-1, 1)
                
                # Add timestamp
                timestamp = time.time()
                audio_chunk = {
                    'data': audio_array,
                    'timestamp': timestamp,
                    'sample_rate': self.sample_rate,
                    'channels': self.channels
                }
                
                # Add to queue (drop oldest if full)
                try:
                    self.audio_queue.put(audio_chunk, block=False)
                    self.chunks_captured += 1
                    self.bytes_captured += len(data)
                    self.last_capture_time = timestamp
                except queue.Full:
                    # Drop oldest chunk
                    try:
                        self.audio_queue.get(block=False)
                        self.audio_queue.put(audio_chunk, block=False)
                    except queue.Empty:
                        pass
                        
            except Exception as e:
                logger.error(f"Error reading microphone data: {e}")
                break
    
    def get_latest_chunk(self, timeout: float = 1.0) -> Optional[dict]:
        """
        Get the most recent audio chunk.
        
        Args:
            timeout: Maximum time to wait for audio data
        
        Returns:
            Dictionary with audio data and metadata, or None if no data
        """
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_audio_buffer(self, duration: float) -> Optional[np.ndarray]:
        """
        Get audio buffer of specified duration.
        
        Args:
            duration: Duration of audio to collect in seconds
        
        Returns:
            Numpy array with audio data, or None if insufficient data
        """
        if not self.is_capturing:
            return None
        
        target_chunks = int(duration / self.chunk_duration)
        audio_chunks = []
        
        # Collect chunks from queue
        for _ in range(target_chunks):
            chunk = self.get_latest_chunk(timeout=0.1)
            if chunk is None:
                break
            audio_chunks.append(chunk['data'])
        
        if not audio_chunks:
            return None
        
        # Concatenate chunks
        audio_buffer = np.concatenate(audio_chunks, axis=0)
        
        # Trim to exact duration
        target_samples = int(duration * self.sample_rate)
        if len(audio_buffer) > target_samples:
            audio_buffer = audio_buffer[:target_samples]
        
        return audio_buffer
    
    def get_statistics(self) -> dict:
        """Get capture statistics."""
        current_time = time.time()
        uptime = current_time - self.start_time if self.start_time > 0 else 0
        
        stats = {
            'is_capturing': self.is_capturing,
            'device_name': self.device_name,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'chunk_duration': self.chunk_duration,
            'chunks_captured': self.chunks_captured,
            'bytes_captured': self.bytes_captured,
            'uptime': uptime,
            'last_capture_time': self.last_capture_time,
            'queue_size': self.audio_queue.qsize()
        }
        
        if uptime > 0 and self.chunks_captured > 0:
            stats['chunks_per_second'] = self.chunks_captured / uptime
            stats['bytes_per_second'] = self.bytes_captured / uptime
        
        return stats


class USBMicCapture:
    """
    Fallback microphone capture using USB microphone or built-in audio.
    
    Used when I²S microphone is not available.
    """
    
    def __init__(self, sample_rate: int = 44100, channels: int = 1,
                 device_name: str = "default", chunk_duration: float = 0.1):
        """Initialize USB microphone capture."""
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_name = device_name
        self.chunk_duration = chunk_duration
        self.chunk_frames = int(sample_rate * chunk_duration)
        
        # Capture state
        self.is_capturing = False
        self.capture_process = None
        self.audio_queue = queue.Queue(maxsize=50)
        self.reader_thread = None
        
        # Statistics
        self.chunks_captured = 0
        self.bytes_captured = 0
        self.start_time = 0.0
        
        logger.info(f"USBMicCapture initialized: {sample_rate}Hz, {channels}ch, "
                   f"device={device_name}")
    
    def start_capture(self) -> bool:
        """Start USB microphone capture."""
        if self.is_capturing:
            return True
        
        try:
            # Use arecord for USB microphone
            cmd = [
                'arecord',
                '-D', self.device_name,
                '-f', 'S16_LE',  # 16-bit signed little-endian
                '-r', str(self.sample_rate),
                '-c', str(self.channels),
                '-t', 'raw'
            ]
            
            self.capture_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            # Start reader thread
            self.is_capturing = True
            self.start_time = time.time()
            
            self.reader_thread = threading.Thread(target=self._read_audio_data)
            self.reader_thread.daemon = True
            self.reader_thread.start()
            
            logger.info(f"Started USB microphone capture: {self.device_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start USB microphone capture: {e}")
            return False
    
    def stop_capture(self) -> None:
        """Stop USB microphone capture."""
        self.is_capturing = False
        
        if self.capture_process:
            self.capture_process.terminate()
            self.capture_process.wait()
            self.capture_process = None
        
        if self.reader_thread:
            self.reader_thread.join(timeout=5.0)
        
        logger.info("Stopped USB microphone capture")
    
    def _read_audio_data(self) -> None:
        """Read audio data from USB microphone."""
        chunk_size = self.chunk_frames * self.channels * 2  # 2 bytes per 16-bit sample
        
        while self.is_capturing and self.capture_process:
            try:
                data = self.capture_process.stdout.read(chunk_size)
                if not data:
                    break
                
                # Convert to numpy array (16-bit int to float32)
                audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                
                if self.channels == 2:
                    audio_array = audio_array.reshape(-1, 2)
                else:
                    audio_array = audio_array.reshape(-1, 1)
                
                # Add to queue
                audio_chunk = {
                    'data': audio_array,
                    'timestamp': time.time(),
                    'sample_rate': self.sample_rate,
                    'channels': self.channels
                }
                
                try:
                    self.audio_queue.put(audio_chunk, block=False)
                    self.chunks_captured += 1
                    self.bytes_captured += len(data)
                except queue.Full:
                    try:
                        self.audio_queue.get(block=False)
                        self.audio_queue.put(audio_chunk, block=False)
                    except queue.Empty:
                        pass
                        
            except Exception as e:
                logger.error(f"Error reading USB microphone data: {e}")
                break
    
    def get_latest_chunk(self, timeout: float = 1.0) -> Optional[dict]:
        """Get the most recent audio chunk."""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_audio_buffer(self, duration: float) -> Optional[np.ndarray]:
        """Get audio buffer of specified duration."""
        if not self.is_capturing:
            return None
        
        target_chunks = int(duration / self.chunk_duration)
        audio_chunks = []
        
        for _ in range(target_chunks):
            chunk = self.get_latest_chunk(timeout=0.1)
            if chunk is None:
                break
            audio_chunks.append(chunk['data'])
        
        if not audio_chunks:
            return None
        
        audio_buffer = np.concatenate(audio_chunks, axis=0)
        target_samples = int(duration * self.sample_rate)
        if len(audio_buffer) > target_samples:
            audio_buffer = audio_buffer[:target_samples]
        
        return audio_buffer
    
    def get_statistics(self) -> dict:
        """Get capture statistics."""
        current_time = time.time()
        uptime = current_time - self.start_time if self.start_time > 0 else 0
        
        return {
            'is_capturing': self.is_capturing,
            'device_name': self.device_name,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'chunks_captured': self.chunks_captured,
            'bytes_captured': self.bytes_captured,
            'uptime': uptime,
            'queue_size': self.audio_queue.qsize()
        }


def create_mic_capture(config: dict) -> Optional[object]:
    """
    Create appropriate microphone capture instance based on configuration.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Microphone capture instance or None if creation failed
    """
    mic_type = config.get('type', 'i2s')
    sample_rate = config.get('sample_rate', 44100)
    channels = config.get('channels', 1)
    device_name = config.get('device_name', 'hw:1,0' if mic_type == 'i2s' else 'default')
    
    try:
        if mic_type == 'i2s':
            return I2SMicCapture(sample_rate, channels, device_name)
        elif mic_type == 'usb':
            return USBMicCapture(sample_rate, channels, device_name)
        else:
            logger.error(f"Unknown microphone type: {mic_type}")
            return None
    except Exception as e:
        logger.error(f"Failed to create microphone capture: {e}")
        return None


if __name__ == "__main__":
    # Test microphone capture
    logging.basicConfig(level=logging.DEBUG)
    
    # Test I²S microphone first
    print("Testing I²S microphone...")
    i2s_mic = I2SMicCapture(sample_rate=44100, channels=1)
    
    if i2s_mic.start_capture():
        print("I²S microphone capture started. Recording for 5 seconds...")
        time.sleep(5)
        
        # Get audio buffer
        audio_data = i2s_mic.get_audio_buffer(2.0)
        if audio_data is not None:
            print(f"Captured audio: {audio_data.shape}, "
                  f"RMS: {np.sqrt(np.mean(audio_data**2)):.4f}")
        
        stats = i2s_mic.get_statistics()
        print(f"Statistics: {stats}")
        
        i2s_mic.stop_capture()
    else:
        print("I²S microphone not available, testing USB microphone...")
        
        # Fallback to USB microphone
        usb_mic = USBMicCapture(sample_rate=44100, channels=1)
        
        if usb_mic.start_capture():
            print("USB microphone capture started. Recording for 5 seconds...")
            time.sleep(5)
            
            audio_data = usb_mic.get_audio_buffer(2.0)
            if audio_data is not None:
                print(f"Captured audio: {audio_data.shape}, "
                      f"RMS: {np.sqrt(np.mean(audio_data**2)):.4f}")
            
            usb_mic.stop_capture()
        else:
            print("No microphone available for testing")

