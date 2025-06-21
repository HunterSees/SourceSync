from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Device(db.Model):
    """Device model for storing receiver device information."""
    
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), unique=True, nullable=False)
    device_name = db.Column(db.String(200), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(200))
    sync_group = db.Column(db.String(100), default='default')
    
    # Configuration
    base_latency_ms = db.Column(db.Float, default=0.0)
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    
    # Status
    is_online = db.Column(db.Boolean, default=False)
    is_playing = db.Column(db.Boolean, default=False)
    is_muted = db.Column(db.Boolean, default=False)
    volume = db.Column(db.Float, default=1.0)
    
    # Sync data
    current_offset_ms = db.Column(db.Float, default=0.0)
    last_drift_ms = db.Column(db.Float, default=0.0)
    avg_drift_ms = db.Column(db.Float, default=0.0)
    drift_variance = db.Column(db.Float, default=0.0)
    correlation_quality = db.Column(db.Float, default=0.0)
    
    # System info
    cpu_usage = db.Column(db.Float, default=0.0)
    memory_usage = db.Column(db.Float, default=0.0)
    temperature = db.Column(db.Float, default=0.0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert device to dictionary."""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'location': self.location,
            'sync_group': self.sync_group,
            'base_latency_ms': self.base_latency_ms,
            'ip_address': self.ip_address,
            'is_online': self.is_online,
            'is_playing': self.is_playing,
            'is_muted': self.is_muted,
            'volume': self.volume,
            'current_offset_ms': self.current_offset_ms,
            'last_drift_ms': self.last_drift_ms,
            'avg_drift_ms': self.avg_drift_ms,
            'drift_variance': self.drift_variance,
            'correlation_quality': self.correlation_quality,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'temperature': self.temperature,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None
        }
    
    def update_from_dict(self, data):
        """Update device from dictionary."""
        for key, value in data.items():
            if hasattr(self, key) and key not in ['id', 'device_id', 'created_at']:
                setattr(self, key, value)
    
    def __repr__(self):
        return f'<Device {self.device_id}: {self.device_name}>'


class SyncEvent(db.Model):
    """Model for storing synchronization events."""
    
    __tablename__ = 'sync_events'
    
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)  # 'drift_report', 'offset_update', etc.
    device_id = db.Column(db.String(100), nullable=False)
    
    # Event data
    drift_ms = db.Column(db.Float)
    offset_ms = db.Column(db.Float)
    correlation = db.Column(db.Float)
    signal_strength = db.Column(db.Float)
    
    # Metadata
    sync_group = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert sync event to dictionary."""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'device_id': self.device_id,
            'drift_ms': self.drift_ms,
            'offset_ms': self.offset_ms,
            'correlation': self.correlation,
            'signal_strength': self.signal_strength,
            'sync_group': self.sync_group,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    def __repr__(self):
        return f'<SyncEvent {self.event_type}: {self.device_id}>'


class SystemStatus(db.Model):
    """Model for storing system status snapshots."""
    
    __tablename__ = 'system_status'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Overall stats
    total_devices = db.Column(db.Integer, default=0)
    online_devices = db.Column(db.Integer, default=0)
    playing_devices = db.Column(db.Integer, default=0)
    
    # Sync stats
    sync_events_count = db.Column(db.Integer, default=0)
    avg_drift_ms = db.Column(db.Float, default=0.0)
    max_drift_ms = db.Column(db.Float, default=0.0)
    min_drift_ms = db.Column(db.Float, default=0.0)
    
    # System performance
    cpu_usage = db.Column(db.Float, default=0.0)
    memory_usage = db.Column(db.Float, default=0.0)
    network_latency = db.Column(db.Float, default=0.0)
    
    # Timestamp
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert system status to dictionary."""
        return {
            'id': self.id,
            'total_devices': self.total_devices,
            'online_devices': self.online_devices,
            'playing_devices': self.playing_devices,
            'sync_events_count': self.sync_events_count,
            'avg_drift_ms': self.avg_drift_ms,
            'max_drift_ms': self.max_drift_ms,
            'min_drift_ms': self.min_drift_ms,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'network_latency': self.network_latency,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    def __repr__(self):
        return f'<SystemStatus {self.timestamp}: {self.online_devices}/{self.total_devices} online>'

