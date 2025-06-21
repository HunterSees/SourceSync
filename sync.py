from flask import Blueprint, request, jsonify
from src.models.device import db, Device, SyncEvent
from datetime import datetime, timedelta
import statistics

sync_bp = Blueprint('sync', __name__)

@sync_bp.route('/sync/status', methods=['GET'])
def get_sync_status():
    """Get overall synchronization status."""
    try:
        # Get all online devices
        online_devices = Device.query.filter_by(is_online=True).all()
        
        if not online_devices:
            return jsonify({
                'success': True,
                'sync_status': {
                    'total_devices': 0,
                    'online_devices': 0,
                    'sync_groups': {},
                    'overall_drift_ms': 0.0,
                    'max_drift_ms': 0.0,
                    'sync_quality': 'unknown'
                }
            })
        
        # Group devices by sync group
        sync_groups = {}
        all_drifts = []
        
        for device in online_devices:
            group = device.sync_group or 'default'
            if group not in sync_groups:
                sync_groups[group] = {
                    'devices': [],
                    'avg_drift_ms': 0.0,
                    'max_drift_ms': 0.0,
                    'device_count': 0,
                    'sync_quality': 'unknown'
                }
            
            device_data = {
                'device_id': device.device_id,
                'device_name': device.device_name,
                'last_drift_ms': device.last_drift_ms,
                'avg_drift_ms': device.avg_drift_ms,
                'correlation_quality': device.correlation_quality,
                'current_offset_ms': device.current_offset_ms
            }
            
            sync_groups[group]['devices'].append(device_data)
            sync_groups[group]['device_count'] += 1
            
            if device.last_drift_ms is not None:
                all_drifts.append(device.last_drift_ms)
        
        # Calculate group statistics
        for group_name, group_data in sync_groups.items():
            group_drifts = [d['last_drift_ms'] for d in group_data['devices'] if d['last_drift_ms'] is not None]
            
            if group_drifts:
                group_data['avg_drift_ms'] = statistics.mean(group_drifts)
                group_data['max_drift_ms'] = max(abs(d) for d in group_drifts)
                
                # Determine sync quality based on drift variance
                if len(group_drifts) > 1:
                    drift_variance = statistics.variance(group_drifts)
                    if drift_variance < 25:  # < 25ms variance
                        group_data['sync_quality'] = 'excellent'
                    elif drift_variance < 100:  # < 100ms variance
                        group_data['sync_quality'] = 'good'
                    elif drift_variance < 250:  # < 250ms variance
                        group_data['sync_quality'] = 'fair'
                    else:
                        group_data['sync_quality'] = 'poor'
                else:
                    group_data['sync_quality'] = 'single_device'
        
        # Overall statistics
        overall_drift = statistics.mean(all_drifts) if all_drifts else 0.0
        max_drift = max(abs(d) for d in all_drifts) if all_drifts else 0.0
        
        # Overall sync quality
        if len(all_drifts) > 1:
            overall_variance = statistics.variance(all_drifts)
            if overall_variance < 25:
                overall_quality = 'excellent'
            elif overall_variance < 100:
                overall_quality = 'good'
            elif overall_variance < 250:
                overall_quality = 'fair'
            else:
                overall_quality = 'poor'
        else:
            overall_quality = 'insufficient_data'
        
        return jsonify({
            'success': True,
            'sync_status': {
                'total_devices': Device.query.count(),
                'online_devices': len(online_devices),
                'sync_groups': sync_groups,
                'overall_drift_ms': overall_drift,
                'max_drift_ms': max_drift,
                'sync_quality': overall_quality,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sync_bp.route('/sync/drift', methods=['POST'])
def report_drift():
    """Record drift measurement from device."""
    try:
        data = request.get_json()
        
        if not data or 'device_id' not in data or 'drift_ms' not in data:
            return jsonify({
                'success': False,
                'error': 'device_id and drift_ms are required'
            }), 400
        
        device_id = data['device_id']
        drift_ms = data['drift_ms']
        correlation = data.get('correlation', 0.0)
        signal_strength = data.get('signal_strength', -50.0)
        
        # Update device with drift data
        device = Device.query.filter_by(device_id=device_id).first()
        if device:
            device.last_drift_ms = drift_ms
            device.correlation_quality = correlation
            device.last_seen = datetime.utcnow()
            
            # Update average drift (simple moving average)
            if device.avg_drift_ms is None:
                device.avg_drift_ms = drift_ms
            else:
                # Exponential moving average with alpha = 0.1
                device.avg_drift_ms = 0.9 * device.avg_drift_ms + 0.1 * drift_ms
        
        # Record sync event
        sync_event = SyncEvent(
            event_type='drift_report',
            device_id=device_id,
            drift_ms=drift_ms,
            correlation=correlation,
            signal_strength=signal_strength,
            sync_group=device.sync_group if device else None
        )
        
        db.session.add(sync_event)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Drift recorded'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sync_bp.route('/sync/offset', methods=['POST'])
def set_buffer_offset():
    """Set buffer offset for device."""
    try:
        data = request.get_json()
        
        if not data or 'device_id' not in data or 'offset_ms' not in data:
            return jsonify({
                'success': False,
                'error': 'device_id and offset_ms are required'
            }), 400
        
        device_id = data['device_id']
        offset_ms = data['offset_ms']
        
        # Update device offset
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404
        
        device.current_offset_ms = offset_ms
        device.last_seen = datetime.utcnow()
        
        # Record sync event
        sync_event = SyncEvent(
            event_type='offset_update',
            device_id=device_id,
            offset_ms=offset_ms,
            sync_group=device.sync_group
        )
        
        db.session.add(sync_event)
        db.session.commit()
        
        # TODO: Send offset to device via MQTT
        
        return jsonify({
            'success': True,
            'message': 'Buffer offset updated'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sync_bp.route('/sync/resync', methods=['POST'])
def force_resync():
    """Force resynchronization of devices."""
    try:
        data = request.get_json() or {}
        sync_group = data.get('sync_group')
        device_id = data.get('device_id')
        
        if device_id:
            # Resync specific device
            device = Device.query.filter_by(device_id=device_id).first()
            if not device:
                return jsonify({
                    'success': False,
                    'error': 'Device not found'
                }), 404
            
            # Reset offset and trigger resync
            device.current_offset_ms = 0.0
            device.last_seen = datetime.utcnow()
            
            # TODO: Send resync command via MQTT
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Resync triggered for device {device_id}'
            })
        
        elif sync_group:
            # Resync all devices in group
            devices = Device.query.filter_by(sync_group=sync_group, is_online=True).all()
            
            for device in devices:
                device.current_offset_ms = 0.0
                device.last_seen = datetime.utcnow()
            
            # TODO: Send resync command to group via MQTT
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Resync triggered for group {sync_group}',
                'device_count': len(devices)
            })
        
        else:
            # Resync all devices
            devices = Device.query.filter_by(is_online=True).all()
            
            for device in devices:
                device.current_offset_ms = 0.0
                device.last_seen = datetime.utcnow()
            
            # TODO: Send resync command to all devices via MQTT
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Resync triggered for all devices',
                'device_count': len(devices)
            })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sync_bp.route('/sync/events', methods=['GET'])
def get_sync_events():
    """Get recent synchronization events."""
    try:
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        device_id = request.args.get('device_id')
        event_type = request.args.get('event_type')
        hours = request.args.get('hours', 24, type=int)
        
        # Build query
        query = SyncEvent.query
        
        if device_id:
            query = query.filter_by(device_id=device_id)
        
        if event_type:
            query = query.filter_by(event_type=event_type)
        
        # Filter by time range
        time_cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(SyncEvent.timestamp >= time_cutoff)
        
        # Order by timestamp and limit
        events = query.order_by(SyncEvent.timestamp.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'events': [event.to_dict() for event in events],
            'count': len(events)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sync_bp.route('/sync/history', methods=['GET'])
def get_sync_history():
    """Get synchronization history for charts."""
    try:
        # Get query parameters
        device_id = request.args.get('device_id')
        hours = request.args.get('hours', 24, type=int)
        
        # Time range
        time_cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        # Build query for drift events
        query = SyncEvent.query.filter(
            SyncEvent.event_type == 'drift_report',
            SyncEvent.timestamp >= time_cutoff
        )
        
        if device_id:
            query = query.filter_by(device_id=device_id)
        
        events = query.order_by(SyncEvent.timestamp.asc()).all()
        
        # Format data for charts
        history_data = []
        for event in events:
            history_data.append({
                'timestamp': event.timestamp.isoformat(),
                'device_id': event.device_id,
                'drift_ms': event.drift_ms,
                'correlation': event.correlation,
                'signal_strength': event.signal_strength
            })
        
        return jsonify({
            'success': True,
            'history': history_data,
            'count': len(history_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sync_bp.route('/sync/groups/<group_name>/adjust', methods=['POST'])
def adjust_group_sync(group_name):
    """Manually adjust synchronization for a group."""
    try:
        data = request.get_json()
        
        if not data or 'adjustment_ms' not in data:
            return jsonify({
                'success': False,
                'error': 'adjustment_ms is required'
            }), 400
        
        adjustment_ms = data['adjustment_ms']
        
        # Get all devices in group
        devices = Device.query.filter_by(sync_group=group_name, is_online=True).all()
        
        if not devices:
            return jsonify({
                'success': False,
                'error': f'No online devices found in group {group_name}'
            }), 404
        
        # Apply adjustment to all devices
        for device in devices:
            device.current_offset_ms += adjustment_ms
            device.last_seen = datetime.utcnow()
        
        # TODO: Send adjustment commands via MQTT
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Applied {adjustment_ms}ms adjustment to group {group_name}',
            'device_count': len(devices)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

