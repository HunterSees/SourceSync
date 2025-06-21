"""
Audio Output Module for SyncStream Receiver Node

This module handles audio output with buffer delay compensation
for synchronization across multiple devices.
"""

import time
import logging
import threading
import subprocess
import numpy as np
from typing import Optional, Dict, Any
import queue
import tempfile
import os

logger = logging.getLogger(__name__)


class AudioOutput:
    """
    Base class for audio output with synchronization delay.
    """
    
    def __init__(self, sample_rate: int = 44100, channels: int = 2,
                 buffer_delay_ms: float = 0.0):
        """
        Initialize audio output.
        
        Args:
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels
            buffer_delay_ms: Initial buffer delay in milliseconds
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer_delay_ms = buffer_delay_ms
        
        # Output state
        self.is_playing = False
        self.is_muted = False
        self.volume = 1.0
        
        # Statistics
        self.bytes_played = 0
        self.start_time = 0.0
        
        logger.info(f"AudioOutput initialized: {sample_rate}Hz, {channels}ch, "
                   f"delay={buffer_delay_ms}ms")
    
    def set_buffer_delay(self, delay_ms: float) -> None:
        """Set buffer delay for synchronization."""
        self.buffer_delay_ms = delay_ms
        logger.debug(f"Buffer delay set to {delay_ms:.1f}ms")
    
    def set_volume(self, volume: float) -> None:
        """Set output volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        logger.debug(f"Volume set to {self.volume:.2f}")
    
    def set_mute(self, muted: bool) -> None:
        """Set mute state."""
        self.is_muted = muted
        logger.debug(f"Mute set to {muted}")
    
    def start_playback(self, stream_url: str) -> bool:
        """Start audio playback from stream URL."""
        raise NotImplementedError
    
    def stop_playback(self) -> None:
        """Stop audio playback."""
        raise NotImplementedError
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get playback statistics."""
        current_time = time.time()
        uptime = current_time - self.start_time if self.start_time > 0 else 0
        
        return {
            'is_playing': self.is_playing,
            'is_muted': self.is_muted,
            'volume': self.volume,
            'buffer_delay_ms': self.buffer_delay_ms,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'bytes_played': self.bytes_played,
            'uptime': uptime
        }


class SnapcastOutput(AudioOutput):
    """Audio output using Snapcast client."""
    
    def __init__(self, server_host: str = "localhost", server_port: int = 1704,
                 sample_rate: int = 44100, channels: int = 2):
        super().__init__(sample_rate, channels)
        self.server_host = server_host
        self.server_port = server_port
        self.snapclient_process = None
        
    def start_playback(self, stream_url: str = None) -> bool:
        """Start Snapcast client."""
        if self.is_playing:
            return True
        
        try:
            # Snapcast client command
            cmd = [
                'snapclient',
                '-h', self.server_host,
                '-p', str(self.server_port),
                '--latency', str(int(self.buffer_delay_ms))
            ]
            
            self.snapclient_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_playing = True
            self.start_time = time.time()
            
            logger.info(f"Started Snapcast client: {self.server_host}:{self.server_port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Snapcast client: {e}")
            return False
    
    def stop_playback(self) -> None:
        """Stop Snapcast client."""
        if self.snapclient_process:
            self.snapclient_process.terminate()
            self.snapclient_process.wait()
            self.snapclient_process = None
        
        self.is_playing = False
        logger.info("Stopped Snapcast client")
    
    def set_buffer_delay(self, delay_ms: float) -> None:
        """Update Snapcast latency."""
        super().set_buffer_delay(delay_ms)
        
        # Restart client with new latency if playing
        if self.is_playing:
            self.stop_playback()
            self.start_playback()


class ALSAOutput(AudioOutput):
    """Audio output using ALSA (analog/HDMI)."""
    
    def __init__(self, device_name: str = "default", sample_rate: int = 44100,
                 channels: int = 2):
        super().__init__(sample_rate, channels)
        self.device_name = device_name
        self.ffmpeg_process = None
        self.delay_fifo = None
        
    def start_playback(self, stream_url: str) -> bool:
        """Start ALSA playback with delay compensation."""
        if self.is_playing:
            return True
        
        try:
            # Create temporary FIFO for delay buffer
            self.delay_fifo = tempfile.mktemp(suffix='.fifo')
            os.mkfifo(self.delay_fifo)
            
            # Calculate delay in samples
            delay_samples = int((self.buffer_delay_ms / 1000.0) * self.sample_rate)
            
            # FFmpeg command with delay and ALSA output
            cmd = [
                'ffmpeg',
                '-i', stream_url,
                '-f', 'alsa',
                '-acodec', 'pcm_s16le',
                '-ar', str(self.sample_rate),
                '-ac', str(self.channels),
                '-af', f'adelay={int(self.buffer_delay_ms)}|{int(self.buffer_delay_ms)}',
                self.device_name
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_playing = True
            self.start_time = time.time()
            
            logger.info(f"Started ALSA playback: {self.device_name}, delay={self.buffer_delay_ms}ms")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start ALSA playback: {e}")
            return False
    
    def stop_playback(self) -> None:
        """Stop ALSA playback."""
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
            self.ffmpeg_process = None
        
        if self.delay_fifo and os.path.exists(self.delay_fifo):
            os.unlink(self.delay_fifo)
            self.delay_fifo = None
        
        self.is_playing = False
        logger.info("Stopped ALSA playback")


class PulseAudioOutput(AudioOutput):
    """Audio output using PulseAudio."""
    
    def __init__(self, sink_name: str = None, sample_rate: int = 44100,
                 channels: int = 2):
        super().__init__(sample_rate, channels)
        self.sink_name = sink_name or self._get_default_sink()
        self.ffmpeg_process = None
        
    def _get_default_sink(self) -> str:
        """Get default PulseAudio sink."""
        try:
            result = subprocess.run(['pactl', 'info'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'Default Sink:' in line:
                    return line.split(':')[1].strip()
        except Exception:
            pass
        return 'default'
    
    def start_playback(self, stream_url: str) -> bool:
        """Start PulseAudio playback."""
        if self.is_playing:
            return True
        
        try:
            # FFmpeg command with PulseAudio output and delay
            cmd = [
                'ffmpeg',
                '-i', stream_url,
                '-f', 'pulse',
                '-acodec', 'pcm_s16le',
                '-ar', str(self.sample_rate),
                '-ac', str(self.channels),
                '-af', f'adelay={int(self.buffer_delay_ms)}|{int(self.buffer_delay_ms)}',
                self.sink_name
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_playing = True
            self.start_time = time.time()
            
            logger.info(f"Started PulseAudio playback: {self.sink_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start PulseAudio playback: {e}")
            return False
    
    def stop_playback(self) -> None:
        """Stop PulseAudio playback."""
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
            self.ffmpeg_process = None
        
        self.is_playing = False
        logger.info("Stopped PulseAudio playback")


class BluetoothOutput(AudioOutput):
    """Audio output using Bluetooth."""
    
    def __init__(self, device_address: str, sample_rate: int = 44100,
                 channels: int = 2):
        super().__init__(sample_rate, channels)
        self.device_address = device_address
        self.ffmpeg_process = None
        
    def _connect_bluetooth_device(self) -> bool:
        """Connect to Bluetooth audio device."""
        try:
            # Connect using bluetoothctl
            subprocess.run(['bluetoothctl', 'connect', self.device_address], 
                         check=True, capture_output=True)
            
            # Wait for connection
            time.sleep(2)
            
            # Check if connected
            result = subprocess.run(['bluetoothctl', 'info', self.device_address],
                                  capture_output=True, text=True)
            
            return 'Connected: yes' in result.stdout
            
        except Exception as e:
            logger.error(f"Failed to connect Bluetooth device: {e}")
            return False
    
    def start_playback(self, stream_url: str) -> bool:
        """Start Bluetooth playback."""
        if self.is_playing:
            return True
        
        # Connect Bluetooth device first
        if not self._connect_bluetooth_device():
            logger.error("Failed to connect Bluetooth device")
            return False
        
        try:
            # Use PulseAudio with Bluetooth sink
            bt_sink = f"bluez_sink.{self.device_address.replace(':', '_')}.a2dp_sink"
            
            cmd = [
                'ffmpeg',
                '-i', stream_url,
                '-f', 'pulse',
                '-acodec', 'pcm_s16le',
                '-ar', str(self.sample_rate),
                '-ac', str(self.channels),
                '-af', f'adelay={int(self.buffer_delay_ms)}|{int(self.buffer_delay_ms)}',
                bt_sink
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_playing = True
            self.start_time = time.time()
            
            logger.info(f"Started Bluetooth playback: {self.device_address}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Bluetooth playback: {e}")
            return False
    
    def stop_playback(self) -> None:
        """Stop Bluetooth playback."""
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
            self.ffmpeg_process = None
        
        self.is_playing = False
        logger.info("Stopped Bluetooth playback")


def create_audio_output(config: Dict[str, Any]) -> Optional[AudioOutput]:
    """
    Create appropriate audio output instance based on configuration.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        AudioOutput instance or None if creation failed
    """
    output_type = config.get('type', 'alsa')
    sample_rate = config.get('sample_rate', 44100)
    channels = config.get('channels', 2)
    
    try:
        if output_type == 'snapcast':
            server_host = config.get('server_host', 'localhost')
            server_port = config.get('server_port', 1704)
            return SnapcastOutput(server_host, server_port, sample_rate, channels)
            
        elif output_type == 'alsa':
            device_name = config.get('device_name', 'default')
            return ALSAOutput(device_name, sample_rate, channels)
            
        elif output_type == 'pulse':
            sink_name = config.get('sink_name')
            return PulseAudioOutput(sink_name, sample_rate, channels)
            
        elif output_type == 'bluetooth':
            device_address = config.get('device_address')
            if not device_address:
                logger.error("Bluetooth device address required")
                return None
            return BluetoothOutput(device_address, sample_rate, channels)
            
        else:
            logger.error(f"Unknown audio output type: {output_type}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to create audio output: {e}")
        return None


if __name__ == "__main__":
    # Test audio output
    logging.basicConfig(level=logging.DEBUG)
    
    # Test ALSA output
    print("Testing ALSA audio output...")
    
    alsa_config = {
        'type': 'alsa',
        'device_name': 'default',
        'sample_rate': 44100,
        'channels': 2
    }
    
    audio_output = create_audio_output(alsa_config)
    
    if audio_output:
        # Set buffer delay
        audio_output.set_buffer_delay(100.0)  # 100ms delay
        
        # Test with a stream URL (would need actual stream)
        test_url = "http://localhost:8080/stream"
        
        print(f"Starting playback with {audio_output.buffer_delay_ms}ms delay...")
        print("Note: This test requires a valid audio stream URL")
        
        if audio_output.start_playback(test_url):
            print("Playback started successfully")
            
            # Run for a few seconds
            time.sleep(5)
            
            # Get statistics
            stats = audio_output.get_statistics()
            print(f"Statistics: {stats}")
            
            # Stop playback
            audio_output.stop_playback()
            print("Playback stopped")
        else:
            print("Failed to start playback (stream not available)")
    else:
        print("Failed to create audio output")
    
    # Test Snapcast output
    print("\nTesting Snapcast audio output...")
    
    snapcast_config = {
        'type': 'snapcast',
        'server_host': 'localhost',
        'server_port': 1704,
        'sample_rate': 44100,
        'channels': 2
    }
    
    snapcast_output = create_audio_output(snapcast_config)
    
    if snapcast_output:
        snapcast_output.set_buffer_delay(50.0)  # 50ms delay
        
        print("Note: This test requires a running Snapcast server")
        if snapcast_output.start_playback():
            print("Snapcast client started")
            time.sleep(3)
            snapcast_output.stop_playback()
            print("Snapcast client stopped")
        else:
            print("Failed to start Snapcast client (server not available)")
    else:
        print("Failed to create Snapcast output")

