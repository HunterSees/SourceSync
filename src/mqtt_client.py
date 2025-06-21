"""
MQTT Client Module for SyncStream Receiver Node

This module handles MQTT communication between receiver nodes
and the transmitter host for synchronization protocol.
"""

import json
import logging
import threading
import time
from typing import Dict, Callable, Optional, Any
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    """
    MQTT client for SyncStream receiver nodes.
    
    Handles communication with transmitter host including:
    - Device registration
    - Drift reporting
    - Buffer offset reception
    - Command handling
    """
    
    def __init__(self, device_id: str, broker_host: str = "localhost", 
                 broker_port: int = 1883, device_config: Optional[Dict] = None):
        """
        Initialize MQTT client.
        
        Args:
            device_id: Unique identifier for this receiver device
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
            device_config: Device configuration dictionary
        """
        self.device_id = device_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.device_config = device_config or {}
        
        # MQTT client setup
        client_id = f"syncstream_receiver_{device_id}"
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Connection state
        self.is_connected = False
        self.connection_lock = threading.Lock()
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        self.command_handlers: Dict[str, Callable] = {}
        
        # Statistics
        self.messages_sent = 0
        self.messages_received = 0
        self.last_activity = time.time()
        self.connection_attempts = 0
        
        # Heartbeat
        self.heartbeat_interval = 30.0  # seconds
        self.heartbeat_thread = None
        self.heartbeat_running = False
        
        logger.info(f"MQTTClient initialized for device '{device_id}' "
                   f"-> {broker_host}:{broker_port}")
    
    def set_message_handler(self, topic_suffix: str, handler: Callable) -> None:
        """
        Set handler for specific message topic.
        
        Args:
            topic_suffix: Topic suffix (e.g., 'buffer_offset', 'config')
            handler: Function to handle messages for this topic
        """
        self.message_handlers[topic_suffix] = handler
        logger.debug(f"Set message handler for topic suffix: {topic_suffix}")
    
    def set_command_handler(self, command: str, handler: Callable) -> None:
        """
        Set handler for specific command.
        
        Args:
            command: Command name (e.g., 'resync', 'mute')
            handler: Function to handle this command
        """
        self.command_handlers[command] = handler
        logger.debug(f"Set command handler for: {command}")
    
    def start(self) -> bool:
        """
        Start MQTT client and connect to broker.
        
        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.connection_attempts += 1
            
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10.0
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.is_connected:
                # Start heartbeat
                self._start_heartbeat()
                
                # Register device
                self.register_device()
                
                logger.info("MQTT client started successfully")
                return True
            else:
                logger.error("Failed to connect to MQTT broker within timeout")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start MQTT client: {e}")
            return False
    
    def stop(self) -> None:
        """Stop MQTT client and disconnect from broker."""
        logger.info("Stopping MQTT client")
        
        # Stop heartbeat
        self._stop_heartbeat()
        
        # Disconnect
        self.client.loop_stop()
        self.client.disconnect()
        
        with self.connection_lock:
            self.is_connected = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection event."""
        if rc == 0:
            with self.connection_lock:
                self.is_connected = True
            logger.info("Connected to MQTT broker")
            
            # Subscribe to device-specific topics
            topics = [
                f"syncstream/buffer_offset/{self.device_id}",
                f"syncstream/config/{self.device_id}",
                f"syncstream/command/{self.device_id}",
                f"syncstream/command/all",  # Broadcast commands
                "syncstream/sync_status"
            ]
            
            for topic in topics:
                client.subscribe(topic)
                logger.debug(f"Subscribed to topic: {topic}")
                
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection event."""
        with self.connection_lock:
            self.is_connected = False
        
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection, return code {rc}")
        else:
            logger.info("Disconnected from MQTT broker")
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT message."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            self.messages_received += 1
            self.last_activity = time.time()
            
            logger.debug(f"Received message on topic '{topic}': {payload}")
            
            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON payload: {e}")
                return
            
            # Route message to appropriate handler
            if topic.startswith(f"syncstream/buffer_offset/{self.device_id}"):
                self._handle_buffer_offset(data)
            elif topic.startswith(f"syncstream/config/{self.device_id}"):
                self._handle_config(data)
            elif topic.startswith(f"syncstream/command/"):
                self._handle_command(data)
            elif topic == "syncstream/sync_status":
                self._handle_sync_status(data)
            else:
                # Check custom message handlers
                for topic_suffix, handler in self.message_handlers.items():
                    if topic.endswith(topic_suffix):
                        handler(data)
                        break
                else:
                    logger.warning(f"No handler found for topic: {topic}")
                    
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _handle_buffer_offset(self, data: dict) -> None:
        """Handle buffer offset message from transmitter."""
        try:
            offset_ms = data.get('offset_ms', 0.0)
            timestamp = data.get('timestamp', time.time())
            
            logger.debug(f"Received buffer offset: {offset_ms:.1f}ms")
            
            # Call handler if registered
            if 'buffer_offset' in self.message_handlers:
                self.message_handlers['buffer_offset'](data)
            
        except Exception as e:
            logger.error(f"Error handling buffer offset: {e}")
    
    def _handle_config(self, data: dict) -> None:
        """Handle configuration message from transmitter."""
        try:
            logger.info(f"Received configuration update: {data}")
            
            # Update local config
            self.device_config.update(data)
            
            # Call handler if registered
            if 'config' in self.message_handlers:
                self.message_handlers['config'](data)
            
        except Exception as e:
            logger.error(f"Error handling config: {e}")
    
    def _handle_command(self, data: dict) -> None:
        """Handle command message from transmitter."""
        try:
            command = data.get('command')
            params = data.get('params', {})
            
            logger.info(f"Received command: {command} with params: {params}")
            
            # Call command handler if registered
            if command in self.command_handlers:
                self.command_handlers[command](params)
            else:
                logger.warning(f"No handler for command: {command}")
            
        except Exception as e:
            logger.error(f"Error handling command: {e}")
    
    def _handle_sync_status(self, data: dict) -> None:
        """Handle sync status broadcast from transmitter."""
        try:
            logger.debug(f"Received sync status: {data}")
            
            # Call handler if registered
            if 'sync_status' in self.message_handlers:
                self.message_handlers['sync_status'](data)
            
        except Exception as e:
            logger.error(f"Error handling sync status: {e}")
    
    def register_device(self) -> bool:
        """Register this device with the transmitter."""
        if not self.is_connected:
            logger.warning("Cannot register: MQTT not connected")
            return False
        
        topic = f"syncstream/register/{self.device_id}"
        payload = json.dumps(self.device_config)
        
        try:
            result = self.client.publish(topic, payload)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.messages_sent += 1
                logger.info(f"Device registration sent")
                return True
            else:
                logger.error(f"Failed to send device registration: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error registering device: {e}")
            return False
    
    def report_drift(self, drift_ms: float, signal_strength: float = -50.0,
                    additional_data: Optional[Dict] = None) -> bool:
        """
        Report drift measurement to transmitter.
        
        Args:
            drift_ms: Measured drift in milliseconds
            signal_strength: Signal strength in dBm
            additional_data: Additional measurement data
        
        Returns:
            True if message sent successfully
        """
        if not self.is_connected:
            logger.warning("Cannot report drift: MQTT not connected")
            return False
        
        topic = f"syncstream/drift/{self.device_id}"
        
        payload_data = {
            'drift_ms': drift_ms,
            'signal_strength': signal_strength,
            'timestamp': time.time()
        }
        
        if additional_data:
            payload_data.update(additional_data)
        
        payload = json.dumps(payload_data)
        
        try:
            result = self.client.publish(topic, payload)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.messages_sent += 1
                logger.debug(f"Drift report sent: {drift_ms:.1f}ms")
                return True
            else:
                logger.error(f"Failed to send drift report: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error reporting drift: {e}")
            return False
    
    def report_status(self, status_data: Dict[str, Any]) -> bool:
        """
        Report device status to transmitter.
        
        Args:
            status_data: Status information dictionary
        
        Returns:
            True if message sent successfully
        """
        if not self.is_connected:
            return False
        
        topic = f"syncstream/status/{self.device_id}"
        
        payload_data = {
            'device_id': self.device_id,
            'timestamp': time.time()
        }
        payload_data.update(status_data)
        
        payload = json.dumps(payload_data)
        
        try:
            result = self.client.publish(topic, payload)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.messages_sent += 1
                logger.debug("Status report sent")
                return True
            else:
                logger.error(f"Failed to send status report: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error reporting status: {e}")
            return False
    
    def _start_heartbeat(self) -> None:
        """Start heartbeat thread."""
        if self.heartbeat_running:
            return
        
        self.heartbeat_running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        logger.debug("Heartbeat started")
    
    def _stop_heartbeat(self) -> None:
        """Stop heartbeat thread."""
        self.heartbeat_running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5.0)
        logger.debug("Heartbeat stopped")
    
    def _heartbeat_loop(self) -> None:
        """Heartbeat loop to maintain connection."""
        while self.heartbeat_running:
            try:
                if self.is_connected:
                    topic = f"syncstream/heartbeat/{self.device_id}"
                    payload = json.dumps({
                        'timestamp': time.time(),
                        'device_id': self.device_id
                    })
                    
                    self.client.publish(topic, payload)
                    logger.debug("Heartbeat sent")
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(5.0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get MQTT client statistics."""
        return {
            'device_id': self.device_id,
            'is_connected': self.is_connected,
            'broker_host': self.broker_host,
            'broker_port': self.broker_port,
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'last_activity': self.last_activity,
            'connection_attempts': self.connection_attempts,
            'heartbeat_interval': self.heartbeat_interval,
            'uptime': time.time() - self.last_activity if self.last_activity else 0
        }


if __name__ == "__main__":
    # Test MQTT client
    logging.basicConfig(level=logging.DEBUG)
    
    # Create test device config
    device_config = {
        'type': 'analog',
        'base_latency_ms': 50,
        'sync_group': 'test_group',
        'location': 'test_room'
    }
    
    # Create MQTT client
    client = MQTTClient(
        device_id="test_device",
        broker_host="localhost",
        broker_port=1883,
        device_config=device_config
    )
    
    # Set up message handlers
    def handle_buffer_offset(data):
        print(f"Buffer offset received: {data}")
    
    def handle_config(data):
        print(f"Config update received: {data}")
    
    def handle_resync_command(params):
        print(f"Resync command received: {params}")
    
    client.set_message_handler('buffer_offset', handle_buffer_offset)
    client.set_message_handler('config', handle_config)
    client.set_command_handler('resync', handle_resync_command)
    
    # Start client
    if client.start():
        print("MQTT client started. Testing for 30 seconds...")
        
        try:
            # Send test drift reports
            for i in range(10):
                drift = -5.0 + (i * 1.0)  # Simulate drift from -5ms to +5ms
                client.report_drift(drift, signal_strength=-45.0)
                
                # Send status report
                status = {
                    'cpu_usage': 25.0 + (i * 2.0),
                    'memory_usage': 30.0 + (i * 1.5),
                    'temperature': 45.0 + (i * 0.5)
                }
                client.report_status(status)
                
                time.sleep(3)
                
        except KeyboardInterrupt:
            print("\nStopping MQTT client...")
        
        # Print statistics
        stats = client.get_statistics()
        print(f"\nMQTT client statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        client.stop()
    else:
        print("Failed to start MQTT client")

