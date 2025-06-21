"""
Protocol Module for SyncStream

This module defines MQTT topic formats, message schemas, and protocol
constants used for communication between transmitter and receiver nodes.
"""

import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class MessageType(Enum):
    """MQTT message types."""
    DRIFT_REPORT = "drift"
    BUFFER_OFFSET = "buffer_offset"
    DEVICE_REGISTER = "register"
    DEVICE_STATUS = "status"
    HEARTBEAT = "heartbeat"
    CONFIG_UPDATE = "config"
    COMMAND = "command"
    SYNC_STATUS = "sync_status"
    AUDIO_STREAM = "audio_stream"


class CommandType(Enum):
    """Command types for device control."""
    RESYNC = "resync"
    MUTE = "mute"
    UNMUTE = "unmute"
    SET_VOLUME = "set_volume"
    SET_DELAY = "set_delay"
    RESTART = "restart"
    SHUTDOWN = "shutdown"
    CALIBRATE = "calibrate"
    TEST_TONE = "test_tone"
    UPDATE_CONFIG = "update_config"


class DeviceType(Enum):
    """Device output types."""
    ANALOG = "analog"
    HDMI = "hdmi"
    CHROMECAST = "chromecast"
    AIRPLAY = "airplay"
    BLUETOOTH = "bluetooth"
    SNAPCAST = "snapcast"
    PULSE = "pulse"
    ALSA = "alsa"


class SyncStreamTopics:
    """MQTT topic definitions for SyncStream protocol."""
    
    # Base topic prefix
    BASE = "syncstream"
    
    # Topic patterns
    DRIFT_REPORT = f"{BASE}/drift/{{device_id}}"
    BUFFER_OFFSET = f"{BASE}/buffer_offset/{{device_id}}"
    DEVICE_REGISTER = f"{BASE}/register/{{device_id}}"
    DEVICE_STATUS = f"{BASE}/status/{{device_id}}"
    HEARTBEAT = f"{BASE}/heartbeat/{{device_id}}"
    CONFIG_UPDATE = f"{BASE}/config/{{device_id}}"
    COMMAND = f"{BASE}/command/{{device_id}}"
    SYNC_STATUS = f"{BASE}/sync_status"
    AUDIO_STREAM = f"{BASE}/audio_stream"
    
    # Broadcast topics
    COMMAND_ALL = f"{BASE}/command/all"
    CONFIG_ALL = f"{BASE}/config/all"
    
    @staticmethod
    def get_topic(message_type: MessageType, device_id: str = None) -> str:
        """
        Get MQTT topic for message type and device.
        
        Args:
            message_type: Type of message
            device_id: Device identifier (required for device-specific topics)
        
        Returns:
            MQTT topic string
        """
        topic_map = {
            MessageType.DRIFT_REPORT: SyncStreamTopics.DRIFT_REPORT,
            MessageType.BUFFER_OFFSET: SyncStreamTopics.BUFFER_OFFSET,
            MessageType.DEVICE_REGISTER: SyncStreamTopics.DEVICE_REGISTER,
            MessageType.DEVICE_STATUS: SyncStreamTopics.DEVICE_STATUS,
            MessageType.HEARTBEAT: SyncStreamTopics.HEARTBEAT,
            MessageType.CONFIG_UPDATE: SyncStreamTopics.CONFIG_UPDATE,
            MessageType.COMMAND: SyncStreamTopics.COMMAND,
            MessageType.SYNC_STATUS: SyncStreamTopics.SYNC_STATUS,
            MessageType.AUDIO_STREAM: SyncStreamTopics.AUDIO_STREAM
        }
        
        topic_template = topic_map.get(message_type)
        if not topic_template:
            raise ValueError(f"Unknown message type: {message_type}")
        
        if "{device_id}" in topic_template:
            if not device_id:
                raise ValueError(f"Device ID required for message type: {message_type}")
            return topic_template.format(device_id=device_id)
        
        return topic_template
    
    @staticmethod
    def parse_topic(topic: str) -> tuple[MessageType, Optional[str]]:
        """
        Parse MQTT topic to extract message type and device ID.
        
        Args:
            topic: MQTT topic string
        
        Returns:
            Tuple of (message_type, device_id)
        """
        if not topic.startswith(SyncStreamTopics.BASE):
            raise ValueError(f"Invalid topic prefix: {topic}")
        
        parts = topic.split('/')
        if len(parts) < 2:
            raise ValueError(f"Invalid topic format: {topic}")
        
        message_type_str = parts[1]
        device_id = parts[2] if len(parts) > 2 else None
        
        # Map topic parts to message types
        type_map = {
            "drift": MessageType.DRIFT_REPORT,
            "buffer_offset": MessageType.BUFFER_OFFSET,
            "register": MessageType.DEVICE_REGISTER,
            "status": MessageType.DEVICE_STATUS,
            "heartbeat": MessageType.HEARTBEAT,
            "config": MessageType.CONFIG_UPDATE,
            "command": MessageType.COMMAND,
            "sync_status": MessageType.SYNC_STATUS,
            "audio_stream": MessageType.AUDIO_STREAM
        }
        
        message_type = type_map.get(message_type_str)
        if not message_type:
            raise ValueError(f"Unknown message type in topic: {topic}")
        
        return message_type, device_id


@dataclass
class DriftReportMessage:
    """Drift report message from receiver to transmitter."""
    device_id: str
    drift_ms: float
    correlation: float
    signal_strength: float = -50.0
    measurement_time: float = None
    measurement_count: int = 0
    avg_drift_ms: float = None
    drift_variance: float = None
    
    def __post_init__(self):
        if self.measurement_time is None:
            self.measurement_time = time.time()


@dataclass
class BufferOffsetMessage:
    """Buffer offset message from transmitter to receiver."""
    device_id: str
    offset_ms: float
    timestamp: float = None
    sync_group: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class DeviceRegisterMessage:
    """Device registration message from receiver to transmitter."""
    device_id: str
    device_name: str
    device_type: str
    location: str = None
    base_latency_ms: float = 0.0
    sync_group: str = "default"
    capabilities: List[str] = None
    version: str = "1.0"
    ip_address: str = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


@dataclass
class DeviceStatusMessage:
    """Device status message from receiver to transmitter."""
    device_id: str
    is_online: bool
    is_playing: bool
    is_muted: bool = False
    volume: float = 1.0
    current_offset_ms: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    temperature: float = 0.0
    uptime: float = 0.0
    last_drift_ms: float = 0.0
    correlation_quality: float = 0.0
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class HeartbeatMessage:
    """Heartbeat message from receiver to transmitter."""
    device_id: str
    timestamp: float = None
    sequence: int = 0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class ConfigUpdateMessage:
    """Configuration update message from transmitter to receiver."""
    device_id: str
    config: Dict[str, Any]
    config_version: str = "1.0"
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class CommandMessage:
    """Command message from transmitter to receiver."""
    device_id: str
    command: str
    params: Dict[str, Any] = None
    command_id: str = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.params is None:
            self.params = {}
        if self.command_id is None:
            self.command_id = f"cmd_{int(self.timestamp * 1000)}"


@dataclass
class SyncStatusMessage:
    """Sync status broadcast from transmitter."""
    sync_groups: Dict[str, List[str]]
    device_count: int
    online_devices: int
    sync_events: int
    last_sync_time: float
    avg_drift_ms: float = 0.0
    max_drift_ms: float = 0.0
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class SyncStreamProtocol:
    """Main protocol handler for SyncStream messages."""
    
    @staticmethod
    def serialize_message(message) -> str:
        """
        Serialize message object to JSON string.
        
        Args:
            message: Message dataclass instance
        
        Returns:
            JSON string
        """
        if hasattr(message, '__dict__'):
            data = asdict(message)
        else:
            data = message
        
        return json.dumps(data, default=str)
    
    @staticmethod
    def deserialize_message(message_type: MessageType, json_data: str):
        """
        Deserialize JSON string to message object.
        
        Args:
            message_type: Type of message to deserialize
            json_data: JSON string data
        
        Returns:
            Message dataclass instance
        """
        data = json.loads(json_data)
        
        # Map message types to dataclasses
        type_map = {
            MessageType.DRIFT_REPORT: DriftReportMessage,
            MessageType.BUFFER_OFFSET: BufferOffsetMessage,
            MessageType.DEVICE_REGISTER: DeviceRegisterMessage,
            MessageType.DEVICE_STATUS: DeviceStatusMessage,
            MessageType.HEARTBEAT: HeartbeatMessage,
            MessageType.CONFIG_UPDATE: ConfigUpdateMessage,
            MessageType.COMMAND: CommandMessage,
            MessageType.SYNC_STATUS: SyncStatusMessage
        }
        
        message_class = type_map.get(message_type)
        if not message_class:
            raise ValueError(f"Unknown message type: {message_type}")
        
        try:
            return message_class(**data)
        except TypeError as e:
            raise ValueError(f"Invalid message data for {message_type}: {e}")
    
    @staticmethod
    def validate_message(message_type: MessageType, data: Dict[str, Any]) -> List[str]:
        """
        Validate message data against schema.
        
        Args:
            message_type: Type of message
            data: Message data dictionary
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required fields for each message type
        required_fields = {
            MessageType.DRIFT_REPORT: ['device_id', 'drift_ms', 'correlation'],
            MessageType.BUFFER_OFFSET: ['device_id', 'offset_ms'],
            MessageType.DEVICE_REGISTER: ['device_id', 'device_name', 'device_type'],
            MessageType.DEVICE_STATUS: ['device_id', 'is_online', 'is_playing'],
            MessageType.HEARTBEAT: ['device_id'],
            MessageType.CONFIG_UPDATE: ['device_id', 'config'],
            MessageType.COMMAND: ['device_id', 'command'],
            MessageType.SYNC_STATUS: ['sync_groups', 'device_count', 'online_devices']
        }
        
        # Check required fields
        required = required_fields.get(message_type, [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Type validation
        if message_type == MessageType.DRIFT_REPORT:
            if 'drift_ms' in data and not isinstance(data['drift_ms'], (int, float)):
                errors.append("drift_ms must be a number")
            if 'correlation' in data and not isinstance(data['correlation'], (int, float)):
                errors.append("correlation must be a number")
        
        elif message_type == MessageType.BUFFER_OFFSET:
            if 'offset_ms' in data and not isinstance(data['offset_ms'], (int, float)):
                errors.append("offset_ms must be a number")
        
        elif message_type == MessageType.DEVICE_REGISTER:
            if 'device_type' in data and data['device_type'] not in [t.value for t in DeviceType]:
                errors.append(f"Invalid device_type: {data['device_type']}")
        
        elif message_type == MessageType.COMMAND:
            if 'command' in data and data['command'] not in [c.value for c in CommandType]:
                errors.append(f"Invalid command: {data['command']}")
        
        return errors
    
    @staticmethod
    def create_drift_report(device_id: str, drift_ms: float, correlation: float,
                           **kwargs) -> DriftReportMessage:
        """Create drift report message."""
        return DriftReportMessage(
            device_id=device_id,
            drift_ms=drift_ms,
            correlation=correlation,
            **kwargs
        )
    
    @staticmethod
    def create_buffer_offset(device_id: str, offset_ms: float, **kwargs) -> BufferOffsetMessage:
        """Create buffer offset message."""
        return BufferOffsetMessage(
            device_id=device_id,
            offset_ms=offset_ms,
            **kwargs
        )
    
    @staticmethod
    def create_device_register(device_id: str, device_name: str, device_type: str,
                              **kwargs) -> DeviceRegisterMessage:
        """Create device registration message."""
        return DeviceRegisterMessage(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            **kwargs
        )
    
    @staticmethod
    def create_command(device_id: str, command: str, params: Dict[str, Any] = None,
                      **kwargs) -> CommandMessage:
        """Create command message."""
        return CommandMessage(
            device_id=device_id,
            command=command,
            params=params or {},
            **kwargs
        )


# Protocol constants
PROTOCOL_VERSION = "1.0"
MAX_MESSAGE_SIZE = 64 * 1024  # 64KB
DEFAULT_QOS = 1  # At least once delivery
KEEPALIVE_INTERVAL = 60  # seconds
HEARTBEAT_INTERVAL = 30  # seconds
DEVICE_TIMEOUT = 90  # seconds


if __name__ == "__main__":
    # Test protocol functionality
    print("Testing SyncStream protocol...")
    
    # Test topic generation
    print("\n1. Testing topic generation...")
    drift_topic = SyncStreamTopics.get_topic(MessageType.DRIFT_REPORT, "living_room")
    print(f"Drift topic: {drift_topic}")
    
    command_topic = SyncStreamTopics.get_topic(MessageType.COMMAND, "kitchen")
    print(f"Command topic: {command_topic}")
    
    # Test topic parsing
    print("\n2. Testing topic parsing...")
    msg_type, device_id = SyncStreamTopics.parse_topic(drift_topic)
    print(f"Parsed: {msg_type}, {device_id}")
    
    # Test message creation and serialization
    print("\n3. Testing message serialization...")
    
    # Create drift report
    drift_msg = SyncStreamProtocol.create_drift_report(
        device_id="living_room",
        drift_ms=15.5,
        correlation=0.85,
        signal_strength=-45.0
    )
    
    drift_json = SyncStreamProtocol.serialize_message(drift_msg)
    print(f"Drift message JSON: {drift_json}")
    
    # Test deserialization
    print("\n4. Testing message deserialization...")
    deserialized_drift = SyncStreamProtocol.deserialize_message(
        MessageType.DRIFT_REPORT, drift_json
    )
    print(f"Deserialized drift: {deserialized_drift}")
    
    # Test validation
    print("\n5. Testing message validation...")
    valid_data = {
        "device_id": "test_device",
        "drift_ms": 10.0,
        "correlation": 0.9
    }
    
    invalid_data = {
        "device_id": "test_device",
        "drift_ms": "invalid"  # Should be number
    }
    
    valid_errors = SyncStreamProtocol.validate_message(MessageType.DRIFT_REPORT, valid_data)
    invalid_errors = SyncStreamProtocol.validate_message(MessageType.DRIFT_REPORT, invalid_data)
    
    print(f"Valid data errors: {valid_errors}")
    print(f"Invalid data errors: {invalid_errors}")
    
    # Test command message
    print("\n6. Testing command message...")
    cmd_msg = SyncStreamProtocol.create_command(
        device_id="bedroom",
        command=CommandType.SET_VOLUME.value,
        params={"volume": 0.8}
    )
    
    cmd_json = SyncStreamProtocol.serialize_message(cmd_msg)
    print(f"Command message: {cmd_json}")
    
    print("\nProtocol test completed!")

