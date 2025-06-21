"""
Ecosystem Driver Module for SyncStream Receiver Node

This module provides drivers for various smart audio ecosystems
including Chromecast, AirPlay, Alexa, and other connected devices.
"""

import time
import logging
import subprocess
import threading
from typing import Optional, Dict, Any, List
import json
import requests

logger = logging.getLogger(__name__)


class EcosystemDriver:
    """Base class for ecosystem drivers."""
    
    def __init__(self, device_config: Dict[str, Any]):
        """
        Initialize ecosystem driver.
        
        Args:
            device_config: Device configuration dictionary
        """
        self.device_config = device_config
        self.device_name = device_config.get('target', 'unknown')
        self.is_connected = False
        self.is_streaming = False
        self.buffer_delay_ms = 0.0
        
        logger.info(f"EcosystemDriver initialized for {self.device_name}")
    
    def connect(self) -> bool:
        """Connect to the target device."""
        raise NotImplementedError
    
    def disconnect(self) -> None:
        """Disconnect from the target device."""
        raise NotImplementedError
    
    def start_stream(self, stream_url: str) -> bool:
        """Start streaming audio to the device."""
        raise NotImplementedError
    
    def stop_stream(self) -> None:
        """Stop streaming audio to the device."""
        raise NotImplementedError
    
    def set_volume(self, volume: float) -> bool:
        """Set device volume (0.0 to 1.0)."""
        raise NotImplementedError
    
    def set_buffer_delay(self, delay_ms: float) -> None:
        """Set buffer delay for synchronization."""
        self.buffer_delay_ms = delay_ms
        logger.debug(f"Buffer delay set to {delay_ms:.1f}ms for {self.device_name}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get device status."""
        return {
            'device_name': self.device_name,
            'is_connected': self.is_connected,
            'is_streaming': self.is_streaming,
            'buffer_delay_ms': self.buffer_delay_ms
        }


class ChromecastDriver(EcosystemDriver):
    """Driver for Google Chromecast and Cast-enabled devices."""
    
    def __init__(self, device_config: Dict[str, Any]):
        super().__init__(device_config)
        self.cast_process = None
        self.device_ip = device_config.get('ip_address')
        
    def _discover_device(self) -> Optional[str]:
        """Discover Chromecast device IP address."""
        try:
            # Use mkchromecast to discover devices
            result = subprocess.run(
                ['mkchromecast', '--discover'],
                capture_output=True, text=True, timeout=10
            )
            
            # Parse output to find device
            for line in result.stdout.split('\n'):
                if self.device_name.lower() in line.lower():
                    # Extract IP address from line
                    parts = line.split()
                    for part in parts:
                        if '.' in part and part.count('.') == 3:
                            return part
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to discover Chromecast device: {e}")
            return None
    
    def connect(self) -> bool:
        """Connect to Chromecast device."""
        if self.is_connected:
            return True
        
        # Discover device if IP not provided
        if not self.device_ip:
            self.device_ip = self._discover_device()
            if not self.device_ip:
                logger.error(f"Could not find Chromecast device: {self.device_name}")
                return False
        
        try:
            # Test connection by pinging device
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '3', self.device_ip],
                capture_output=True
            )
            
            if result.returncode == 0:
                self.is_connected = True
                logger.info(f"Connected to Chromecast: {self.device_name} ({self.device_ip})")
                return True
            else:
                logger.error(f"Cannot reach Chromecast device: {self.device_ip}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Chromecast: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from Chromecast device."""
        self.stop_stream()
        self.is_connected = False
        logger.info(f"Disconnected from Chromecast: {self.device_name}")
    
    def start_stream(self, stream_url: str) -> bool:
        """Start streaming to Chromecast."""
        if not self.is_connected:
            if not self.connect():
                return False
        
        if self.is_streaming:
            return True
        
        try:
            # Use mkchromecast to stream audio
            cmd = [
                'mkchromecast',
                '--cast', self.device_ip,
                '--source-url', stream_url,
                '--codec', 'mp3',
                '--bitrate', '320'
            ]
            
            self.cast_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait a moment for stream to start
            time.sleep(2)
            
            if self.cast_process.poll() is None:
                self.is_streaming = True
                logger.info(f"Started Chromecast stream: {self.device_name}")
                return True
            else:
                logger.error("Chromecast streaming process failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start Chromecast stream: {e}")
            return False
    
    def stop_stream(self) -> None:
        """Stop streaming to Chromecast."""
        if self.cast_process:
            self.cast_process.terminate()
            self.cast_process.wait()
            self.cast_process = None
        
        self.is_streaming = False
        logger.info(f"Stopped Chromecast stream: {self.device_name}")
    
    def set_volume(self, volume: float) -> bool:
        """Set Chromecast volume."""
        if not self.is_connected:
            return False
        
        try:
            # Use mkchromecast to set volume
            volume_percent = int(volume * 100)
            subprocess.run(
                ['mkchromecast', '--cast', self.device_ip, '--volume', str(volume_percent)],
                check=True, capture_output=True
            )
            
            logger.debug(f"Set Chromecast volume to {volume_percent}%")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set Chromecast volume: {e}")
            return False


class AirPlayDriver(EcosystemDriver):
    """Driver for Apple AirPlay devices."""
    
    def __init__(self, device_config: Dict[str, Any]):
        super().__init__(device_config)
        self.airplay_process = None
        self.device_ip = device_config.get('ip_address')
        
    def _discover_device(self) -> Optional[str]:
        """Discover AirPlay device."""
        try:
            # Use avahi-browse to discover AirPlay devices
            result = subprocess.run(
                ['avahi-browse', '-t', '_airplay._tcp', '-r'],
                capture_output=True, text=True, timeout=10
            )
            
            # Parse output to find device
            for line in result.stdout.split('\n'):
                if self.device_name.lower() in line.lower() and 'address' in line.lower():
                    # Extract IP address
                    parts = line.split()
                    for part in parts:
                        if '.' in part and part.count('.') == 3:
                            return part.strip('[]')
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to discover AirPlay device: {e}")
            return None
    
    def connect(self) -> bool:
        """Connect to AirPlay device."""
        if self.is_connected:
            return True
        
        # Discover device if IP not provided
        if not self.device_ip:
            self.device_ip = self._discover_device()
            if not self.device_ip:
                logger.error(f"Could not find AirPlay device: {self.device_name}")
                return False
        
        try:
            # Test connection
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '3', self.device_ip],
                capture_output=True
            )
            
            if result.returncode == 0:
                self.is_connected = True
                logger.info(f"Connected to AirPlay: {self.device_name} ({self.device_ip})")
                return True
            else:
                logger.error(f"Cannot reach AirPlay device: {self.device_ip}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to AirPlay: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from AirPlay device."""
        self.stop_stream()
        self.is_connected = False
        logger.info(f"Disconnected from AirPlay: {self.device_name}")
    
    def start_stream(self, stream_url: str) -> bool:
        """Start streaming to AirPlay device."""
        if not self.is_connected:
            if not self.connect():
                return False
        
        if self.is_streaming:
            return True
        
        try:
            # Use ffmpeg with AirPlay output
            cmd = [
                'ffmpeg',
                '-i', stream_url,
                '-f', 'rtp',
                '-acodec', 'pcm_s16be',
                '-ar', '44100',
                '-ac', '2',
                f'rtp://{self.device_ip}:5000'
            ]
            
            self.airplay_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for stream to start
            time.sleep(2)
            
            if self.airplay_process.poll() is None:
                self.is_streaming = True
                logger.info(f"Started AirPlay stream: {self.device_name}")
                return True
            else:
                logger.error("AirPlay streaming process failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start AirPlay stream: {e}")
            return False
    
    def stop_stream(self) -> None:
        """Stop streaming to AirPlay device."""
        if self.airplay_process:
            self.airplay_process.terminate()
            self.airplay_process.wait()
            self.airplay_process = None
        
        self.is_streaming = False
        logger.info(f"Stopped AirPlay stream: {self.device_name}")
    
    def set_volume(self, volume: float) -> bool:
        """Set AirPlay volume."""
        # AirPlay volume control is typically handled by the device itself
        logger.debug(f"AirPlay volume control not implemented")
        return True


class AlexaDriver(EcosystemDriver):
    """Driver for Amazon Alexa devices via Bluetooth."""
    
    def __init__(self, device_config: Dict[str, Any]):
        super().__init__(device_config)
        self.device_address = device_config.get('bluetooth_address')
        self.bluetooth_process = None
        
    def connect(self) -> bool:
        """Connect to Alexa device via Bluetooth."""
        if self.is_connected:
            return True
        
        if not self.device_address:
            logger.error("Bluetooth address required for Alexa device")
            return False
        
        try:
            # Pair and connect via bluetoothctl
            commands = [
                f'pair {self.device_address}',
                f'trust {self.device_address}',
                f'connect {self.device_address}'
            ]
            
            for cmd in commands:
                result = subprocess.run(
                    ['bluetoothctl'] + cmd.split(),
                    capture_output=True, text=True, timeout=10
                )
                
                if result.returncode != 0:
                    logger.warning(f"Bluetooth command failed: {cmd}")
            
            # Check connection status
            result = subprocess.run(
                ['bluetoothctl', 'info', self.device_address],
                capture_output=True, text=True
            )
            
            if 'Connected: yes' in result.stdout:
                self.is_connected = True
                logger.info(f"Connected to Alexa via Bluetooth: {self.device_name}")
                return True
            else:
                logger.error("Failed to connect to Alexa device")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Alexa: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from Alexa device."""
        self.stop_stream()
        
        if self.device_address:
            try:
                subprocess.run(
                    ['bluetoothctl', 'disconnect', self.device_address],
                    capture_output=True
                )
            except Exception:
                pass
        
        self.is_connected = False
        logger.info(f"Disconnected from Alexa: {self.device_name}")
    
    def start_stream(self, stream_url: str) -> bool:
        """Start streaming to Alexa via Bluetooth."""
        if not self.is_connected:
            if not self.connect():
                return False
        
        if self.is_streaming:
            return True
        
        try:
            # Use PulseAudio to stream to Bluetooth device
            bt_sink = f"bluez_sink.{self.device_address.replace(':', '_')}.a2dp_sink"
            
            cmd = [
                'ffmpeg',
                '-i', stream_url,
                '-f', 'pulse',
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '2',
                bt_sink
            ]
            
            self.bluetooth_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            time.sleep(2)
            
            if self.bluetooth_process.poll() is None:
                self.is_streaming = True
                logger.info(f"Started Alexa Bluetooth stream: {self.device_name}")
                return True
            else:
                logger.error("Alexa Bluetooth streaming failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start Alexa stream: {e}")
            return False
    
    def stop_stream(self) -> None:
        """Stop streaming to Alexa."""
        if self.bluetooth_process:
            self.bluetooth_process.terminate()
            self.bluetooth_process.wait()
            self.bluetooth_process = None
        
        self.is_streaming = False
        logger.info(f"Stopped Alexa stream: {self.device_name}")
    
    def set_volume(self, volume: float) -> bool:
        """Set Alexa volume."""
        # Volume is typically controlled on the Alexa device itself
        logger.debug("Alexa volume control handled by device")
        return True


def create_ecosystem_driver(device_config: Dict[str, Any]) -> Optional[EcosystemDriver]:
    """
    Create appropriate ecosystem driver based on device configuration.
    
    Args:
        device_config: Device configuration dictionary
    
    Returns:
        EcosystemDriver instance or None if creation failed
    """
    device_type = device_config.get('type', '').lower()
    
    try:
        if device_type == 'chromecast':
            return ChromecastDriver(device_config)
        elif device_type == 'airplay':
            return AirPlayDriver(device_config)
        elif device_type == 'alexa':
            return AlexaDriver(device_config)
        else:
            logger.error(f"Unknown ecosystem device type: {device_type}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to create ecosystem driver: {e}")
        return None


if __name__ == "__main__":
    # Test ecosystem drivers
    logging.basicConfig(level=logging.DEBUG)
    
    # Test Chromecast driver
    print("Testing Chromecast driver...")
    
    chromecast_config = {
        'type': 'chromecast',
        'target': 'Living Room Speaker',
        'ip_address': '192.168.1.100'  # Example IP
    }
    
    chromecast = create_ecosystem_driver(chromecast_config)
    
    if chromecast:
        print("Chromecast driver created")
        
        # Test connection (will fail without actual device)
        if chromecast.connect():
            print("Connected to Chromecast")
            
            # Test streaming
            test_url = "http://localhost:8080/stream"
            if chromecast.start_stream(test_url):
                print("Chromecast streaming started")
                time.sleep(3)
                chromecast.stop_stream()
                print("Chromecast streaming stopped")
            
            chromecast.disconnect()
        else:
            print("Failed to connect to Chromecast (device not available)")
    
    # Test AirPlay driver
    print("\nTesting AirPlay driver...")
    
    airplay_config = {
        'type': 'airplay',
        'target': 'HomePod',
        'ip_address': '192.168.1.101'  # Example IP
    }
    
    airplay = create_ecosystem_driver(airplay_config)
    
    if airplay:
        print("AirPlay driver created")
        print("Note: AirPlay testing requires actual device")
    
    # Test Alexa driver
    print("\nTesting Alexa driver...")
    
    alexa_config = {
        'type': 'alexa',
        'target': 'Echo Dot',
        'bluetooth_address': '00:11:22:33:44:55'  # Example address
    }
    
    alexa = create_ecosystem_driver(alexa_config)
    
    if alexa:
        print("Alexa driver created")
        print("Note: Alexa testing requires Bluetooth pairing")

