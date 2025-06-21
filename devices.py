from flask import Blueprint, request, jsonify
from src.models.device import db, Device, SyncEvent
from datetime import datetime, timedelta
import json

devices_bp = Blueprint('devices', __name__)

@devices_bp.route('/devices', methods=['GET'])
def get_devices():
    """Get all devices."""
    try:
        devices = Device.query.all()
        return jsonify({
            'success': True,
            'devices': [device.to_dict() for device in devices],
            'count': len(devices)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@devices_bp.route('/devices/<device_id>', methods=['GET'])
def get_device(device_id):
    """Get specific device by ID."""
    try:
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404
        
        return jsonify({
            'success': True,
            'device': device.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@devices_bp.route('/devices', methods=['POST'])
def register_device():
    """Register a new device."""
    try:
        data = request.get_json()
        
        if not data or 'device_id' not in data:
            return jsonify({
                'success': False,
                'error': 'device_id is required'
            }), 400
        
        # Check if device already exists
        existing_device = Device.query.filter_by(device_id=data['device_id']).first()
        if existing_device:
            # Update existing device
            existing_device.update_from_dict(data)
            existing_device.last_seen = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Device updated',
                'device': existing_device.to_dict()
            })
        
        # Create new device
        device = Device(
            device_id=data['device_id'],
            device_name=data.get('device_name', data['device_id']),
            device_type=data.get('device_type', 'unknown'),
            location=data.get('location'),
            sync_group=data.get('sync_group', 'default'),
            base_latency_ms=data.get('base_latency_ms', 0.0),
            ip_address=data.get('ip_address')
        )
        
        db.session.add(device)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Device registered',
            'device': device.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@devices_bp.route('/devices/<device_id>', methods=['PUT'])
def update_device(device_id):
    """Update device configuration."""
    try:
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        device.update_from_dict(data)
        device.last_seen = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Device updated',
            'device': device.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@devices_bp.route('/devices/<device_id>', methods=['DELETE'])
def delete_device(device_id):
    """Delete a device."""
    try:
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404
        
        db.session.delete(device)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Device deleted'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@devices_bp.route('/devices/<device_id>/status', methods=['POST'])
def update_device_status(device_id):
    """Update device status."""
    try:
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Update status fields
        status_fields = [
            'is_online', 'is_playing', 'is_muted', 'volume',
            'current_offset_ms', 'last_drift_ms', 'avg_drift_ms',
            'drift_variance', 'correlation_quality',
            'cpu_usage', 'memory_usage', 'temperature'
        ]
        
        for field in status_fields:
            if field in data:
                setattr(device, field, data[field])
        
        device.last_seen = datetime.utcnow()
        if data.get('is_online'):
            device.last_heartbeat = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Device status updated',
            'device': device.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@devices_bp.route('/devices/<device_id>/heartbeat', methods=['POST'])
def device_heartbeat(device_id):
    """Record device heartbeat."""
    try:
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404
        
        device.is_online = True
        device.last_heartbeat = datetime.utcnow()
        device.last_seen = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Heartbeat recorded'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@devices_bp.route('/devices/groups', methods=['GET'])
def get_sync_groups():
    """Get all sync groups and their devices."""
    try:
        devices = Device.query.all()
        groups = {}
        
        for device in devices:
            group = device.sync_group or 'default'
            if group not in groups:
                groups[group] = []
            groups[group].append(device.to_dict())
        
        return jsonify({
            'success': True,
            'groups': groups
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@devices_bp.route('/devices/<device_id>/command', methods=['POST'])
def send_device_command(device_id):
    """Send command to device (placeholder for MQTT integration)."""
    try:
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404
        
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({
                'success': False,
                'error': 'Command is required'
            }), 400
        
        command = data['command']
        params = data.get('params', {})
        
        # TODO: Integrate with MQTT to send actual commands
        # For now, just return success
        
        return jsonify({
            'success': True,
            'message': f'Command {command} sent to {device_id}',
            'command': command,
            'params': params
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@devices_bp.route('/devices/stats', methods=['GET'])
def get_device_stats():
    """Get device statistics."""
    try:
        total_devices = Device.query.count()
        online_devices = Device.query.filter_by(is_online=True).count()
        playing_devices = Device.query.filter(Device.is_online == True, Device.is_playing == True).count()
        
        # Get devices by type
        device_types = db.session.query(Device.device_type, db.func.count(Device.id)).group_by(Device.device_type).all()
        
        # Get devices by sync group
        sync_groups = db.session.query(Device.sync_group, db.func.count(Device.id)).group_by(Device.sync_group).all()
        
        # Get recent activity (devices seen in last 5 minutes)
        recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent_devices = Device.query.filter(Device.last_seen >= recent_cutoff).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'playing_devices': playing_devices,
                'recent_devices': recent_devices,
                'device_types': dict(device_types),
                'sync_groups': dict(sync_groups)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

