"""
MQTT Server Module for SyncStream Transmitter Host

This module provides MQTT broker functionality and message dispatch
for communication between the transmitter host and receiver nodes.
"""

import json
import logging
import threading
import time
from typing import Dict, Callable, Optional, Any
import paho.mqtt.client as mqtt
from sync_controller import SyncController

logger = logging.getLogger(__name__)


class MQTTServer:
    """
    MQTT server that handles communication with SyncStream receiver nodes.
    
    Manages MQTT broker connection, topic routing, and message dispatch
    for synchronization protocol.
    """
    
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883,
                 sync_controller: Optional[SyncController] = None):
        """
        Initialize MQTT server.
        
        Args:
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
            sync_controller: SyncController instance for handling sync messages
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.sync_controller = sync_controller
        
        # MQTT client setup
        self.client = mqtt.Client(client_id="syncstream_transmitter")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Topic handlers
        self.topic_handlers: Dict[str, Callable] = {
            'syncstream/drift/+': self._handle_drift_message,
            'syncstream/status/+': self._handle_status_message,
            'syncstream/register/+': self._handle_register_message,
            'syncstream/heartbeat/+': self._handle_heartbeat_message
        }
        
        # Connection state
        self.is_connected = False
        self.connection_lock = threading.Lock()
        
        # Message statistics
        self.messages_received = 0
        self.messages_sent = 0
        self.last_activity = time.time()
        
        logger.info(f"MQTTServer initialized for {broker_host}:{broker_port}")
    
    def start(self) -> bool:
        """
        Start the MQTT server and connect to broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10.0
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.is_connected:
                logger.info("MQTT server started successfully")
                return True
            else:
                logger.error("Failed to connect to MQTT broker within timeout")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start MQTT server: {e}")
            return False
    
    def stop(self) -> None:
        """Stop the MQTT server and disconnect from broker."""
        logger.info("Stopping MQTT server")
        self.client.loop_stop()
        self.client.disconnect()
        self.is_connected = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection event."""
        if rc == 0:
            with self.connection_lock:
                self.is_connected = True
            logger.info("Connected to MQTT broker")
            
            # Subscribe to all SyncStream topics
            for topic in self.topic_handlers.keys():
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
            
            # Find matching topic handler
            handler = None
            for topic_pattern, topic_handler in self.topic_handlers.items():
                if self._topic_matches(topic, topic_pattern):
                    handler = topic_handler
                    break
            
            if handler:
                # Parse JSON payload
                try:
                    data = json.loads(payload)
                    handler(topic, data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON payload: {e}")
            else:
                logger.warning(f"No handler found for topic: {topic}")
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern with wildcards."""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        if len(topic_parts) != len(pattern_parts):
            return False
        
        for topic_part, pattern_part in zip(topic_parts, pattern_parts):
            if pattern_part == '+':
                continue  # Single-level wildcard
            elif pattern_part == '#':
                return True  # Multi-level wildcard
            elif topic_part != pattern_part:
                return False
        
        return True
    
    def _extract_device_id(self, topic: str) -> Optional[str]:
        """Extract device ID from topic."""
        parts = topic.split('/')
        if len(parts) >= 3:
            return parts[2]  # Assuming format: syncstream/command/device_id
        return None
    
    def _handle_drift_message(self, topic: str, data: dict) -> None:
        """Handle drift report from receiver node."""
        device_id = self._extract_device_id(topic)
        if not device_id:
            logger.error(f"Could not extract device ID from topic: {topic}")
            return
        
        try:
            drift_ms = data.get('drift_ms', 0.0)
            signal_strength = data.get('signal_strength', -50.0)
            
            if self.sync_controller:
                self.sync_controller.update_device_drift(device_id, drift_ms, signal_strength)
                
                # Send back buffer offset
                offset_ms = self.sync_controller.get_device_offset(device_id)
                self.publish_buffer_offset(device_id, offset_ms)
            
            logger.debug(f"Processed drift report from {device_id}: {drift_ms:.1f}ms")
            
        except Exception as e:
            logger.error(f"Error handling drift message from {device_id}: {e}")
    
    def _handle_status_message(self, topic: str, data: dict) -> None:
        """Handle status update from receiver node."""
        device_id = self._extract_device_id(topic)
        if not device_id:
            return
        
        logger.debug(f"Received status from {device_id}: {data}")
        # Status messages are informational only
    
    def _handle_register_message(self, topic: str, data: dict) -> None:
        """Handle device registration from receiver node."""
        device_id = self._extract_device_id(topic)
        if not device_id:
            return
        
        try:
            if self.sync_controller:
                self.sync_controller.register_device(device_id, data)
                
                # Send initial configuration
                self.publish_config(device_id, data)
            
            logger.info(f"Registered device {device_id}: {data}")
            
        except Exception as e:
            logger.error(f"Error registering device {device_id}: {e}")
    
    def _handle_heartbeat_message(self, topic: str, data: dict) -> None:
        """Handle heartbeat from receiver node."""
        device_id = self._extract_device_id(topic)
        if not device_id:
            return
        
        # Update last seen time for device
        logger.debug(f"Heartbeat from {device_id}")
    
    def publish_buffer_offset(self, device_id: str, offset_ms: float) -> bool:
        """
        Publish buffer offset to a receiver node.
        
        Args:
            device_id: Target device ID
            offset_ms: Buffer offset in milliseconds
        
        Returns:
            True if message sent successfully
        """
        if not self.is_connected:
            logger.warning("Cannot publish: MQTT not connected")
            return False
        
        topic = f"syncstream/buffer_offset/{device_id}"
        payload = json.dumps({
            'offset_ms': offset_ms,
            'timestamp': time.time()
        })
        
        try:
            result = self.client.publish(topic, payload)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.messages_sent += 1
                logger.debug(f"Published buffer offset to {device_id}: {offset_ms:.1f}ms")
                return True
            else:
                logger.error(f"Failed to publish buffer offset: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error publishing buffer offset: {e}")
            return False
    
    def publish_config(self, device_id: str, config: dict) -> bool:
        """
        Publish configuration to a receiver node.
        
        Args:
            device_id: Target device ID
            config: Configuration dictionary
        
        Returns:
            True if message sent successfully
        """
        if not self.is_connected:
            return False
        
        topic = f"syncstream/config/{device_id}"
        payload = json.dumps(config)
        
        try:
            result = self.client.publish(topic, payload)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.messages_sent += 1
                logger.debug(f"Published config to {device_id}")
                return True
            else:
                logger.error(f"Failed to publish config: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error publishing config: {e}")
            return False
    
    def publish_command(self, device_id: str, command: str, params: dict = None) -> bool:
        """
        Publish command to a receiver node.
        
        Args:
            device_id: Target device ID (or 'all' for broadcast)
            command: Command name
            params: Command parameters
        
        Returns:
            True if message sent successfully
        """
        if not self.is_connected:
            return False
        
        topic = f"syncstream/command/{device_id}"
        payload = json.dumps({
            'command': command,
            'params': params or {},
            'timestamp': time.time()
        })
        
        try:
            result = self.client.publish(topic, payload)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.messages_sent += 1
                logger.debug(f"Published command '{command}' to {device_id}")
                return True
            else:
                logger.error(f"Failed to publish command: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error publishing command: {e}")
            return False
    
    def broadcast_sync_status(self) -> bool:
        """Broadcast current synchronization status to all devices."""
        if not self.sync_controller:
            return False
        
        status = self.sync_controller.get_all_status()
        topic = "syncstream/sync_status"
        payload = json.dumps(status)
        
        try:
            result = self.client.publish(topic, payload)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.messages_sent += 1
                logger.debug("Broadcast sync status")
                return True
            else:
                logger.error(f"Failed to broadcast sync status: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error broadcasting sync status: {e}")
            return False
    
    def get_statistics(self) -> dict:
        """Get MQTT server statistics."""
        return {
            'is_connected': self.is_connected,
            'broker_host': self.broker_host,
            'broker_port': self.broker_port,
            'messages_received': self.messages_received,
            'messages_sent': self.messages_sent,
            'last_activity': self.last_activity,
            'uptime': time.time() - self.last_activity if self.last_activity else 0
        }


if __name__ == "__main__":
    # Test the MQTT server
    logging.basicConfig(level=logging.DEBUG)
    
    # Create sync controller and MQTT server
    from sync_controller import SyncController
    
    sync_controller = SyncController()
    mqtt_server = MQTTServer(sync_controller=sync_controller)
    
    # Start server
    if mqtt_server.start():
        print("MQTT server started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
                
                # Broadcast status every 10 seconds
                if int(time.time()) % 10 == 0:
                    mqtt_server.broadcast_sync_status()
                    
        except KeyboardInterrupt:
            print("\nStopping MQTT server...")
            mqtt_server.stop()
    else:
        print("Failed to start MQTT server")

