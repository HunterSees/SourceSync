from flask import Blueprint, request, jsonify
from src.models.device import db, Device, SystemStatus
from datetime import datetime, timedelta
import psutil
import time

system_bp = Blueprint('system', __name__)

@system_bp.route('/system/status', methods=['GET'])
def get_system_status():
    """Get overall system status."""
    try:
        # Get device statistics
        total_devices = Device.query.count()
        online_devices = Device.query.filter_by(is_online=True).count()
        playing_devices = Device.query.filter(Device.is_online == True, Device.is_playing == True).count()
        
        # Get system performance
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get network info
        network = psutil.net_io_counters()
        
        # Calculate uptime (mock)
        uptime = time.time() - 1640995200  # Mock start time
        
        system_status = {
            'devices': {
                'total': total_devices,
                'online': online_devices,
                'playing': playing_devices,
                'offline': total_devices - online_devices
            },
            'performance': {
                'cpu_usage': cpu_usage,
                'memory_usage': memory.percent,
                'memory_total_gb': memory.total / (1024**3),
                'memory_used_gb': memory.used / (1024**3),
                'disk_usage': disk.percent,
                'disk_total_gb': disk.total / (1024**3),
                'disk_used_gb': disk.used / (1024**3)
            },
            'network': {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            },
            'uptime': uptime,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'system_status': system_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_bp.route('/system/health', methods=['GET'])
def get_system_health():
    """Get system health check."""
    try:
        health_checks = []
        overall_status = 'healthy'
        
        # Check database connectivity
        try:
            db.session.execute('SELECT 1')
            health_checks.append({
                'component': 'database',
                'status': 'healthy',
                'message': 'Database connection OK'
            })
        except Exception as e:
            health_checks.append({
                'component': 'database',
                'status': 'unhealthy',
                'message': f'Database error: {str(e)}'
            })
            overall_status = 'unhealthy'
        
        # Check MQTT broker (mock)
        health_checks.append({
            'component': 'mqtt_broker',
            'status': 'healthy',
            'message': 'MQTT broker connection OK'
        })
        
        # Check audio buffer (mock)
        health_checks.append({
            'component': 'audio_buffer',
            'status': 'healthy',
            'message': 'Audio buffer operational'
        })
        
        # Check device connectivity
        recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent_devices = Device.query.filter(Device.last_seen >= recent_cutoff).count()
        total_devices = Device.query.count()
        
        if total_devices > 0:
            connectivity_ratio = recent_devices / total_devices
            if connectivity_ratio >= 0.8:
                device_status = 'healthy'
                device_message = f'{recent_devices}/{total_devices} devices responsive'
            elif connectivity_ratio >= 0.5:
                device_status = 'degraded'
                device_message = f'Only {recent_devices}/{total_devices} devices responsive'
                if overall_status == 'healthy':
                    overall_status = 'degraded'
            else:
                device_status = 'unhealthy'
                device_message = f'Only {recent_devices}/{total_devices} devices responsive'
                overall_status = 'unhealthy'
        else:
            device_status = 'unknown'
            device_message = 'No devices registered'
        
        health_checks.append({
            'component': 'device_connectivity',
            'status': device_status,
            'message': device_message
        })
        
        return jsonify({
            'success': True,
            'overall_status': overall_status,
            'health_checks': health_checks,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_bp.route('/system/logs', methods=['GET'])
def get_system_logs():
    """Get system logs."""
    try:
        # Mock log entries
        logs = [
            {
                'timestamp': datetime.utcnow().isoformat(),
                'level': 'INFO',
                'component': 'api',
                'message': 'System status requested'
            },
            {
                'timestamp': (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
                'level': 'INFO',
                'component': 'sync',
                'message': 'Drift report received from living_room'
            },
            {
                'timestamp': (datetime.utcnow() - timedelta(minutes=2)).isoformat(),
                'level': 'DEBUG',
                'component': 'mqtt',
                'message': 'Device heartbeat: kitchen_speaker'
            },
            {
                'timestamp': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                'level': 'WARNING',
                'component': 'sync',
                'message': 'High drift detected on bedroom_speaker: 150ms'
            }
        ]
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_bp.route('/system/config', methods=['GET'])
def get_system_config():
    """Get system configuration."""
    try:
        config = {
            'version': '1.0.0',
            'build': 'dev-2024',
            'mqtt': {
                'host': 'localhost',
                'port': 1883,
                'keepalive': 60
            },
            'audio': {
                'sample_rate': 44100,
                'channels': 2,
                'buffer_duration': 10.0,
                'max_drift_ms': 1000.0
            },
            'sync': {
                'measurement_interval': 5.0,
                'correlation_threshold': 0.7,
                'max_devices_per_group': 20
            },
            'api': {
                'host': '0.0.0.0',
                'port': 8080,
                'debug': True
            }
        }
        
        return jsonify({
            'success': True,
            'config': config
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_bp.route('/system/restart', methods=['POST'])
def restart_system():
    """Restart system components."""
    try:
        data = request.get_json() or {}
        component = data.get('component', 'all')
        
        # Mock restart functionality
        if component == 'all':
            message = 'System restart initiated'
        elif component == 'mqtt':
            message = 'MQTT broker restart initiated'
        elif component == 'audio':
            message = 'Audio server restart initiated'
        elif component == 'sync':
            message = 'Sync engine restart initiated'
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown component: {component}'
            }), 400
        
        return jsonify({
            'success': True,
            'message': message,
            'component': component
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_bp.route('/system/backup', methods=['POST'])
def create_backup():
    """Create system backup."""
    try:
        # Mock backup creation
        backup_id = f"backup_{int(time.time())}"
        
        return jsonify({
            'success': True,
            'message': 'Backup created successfully',
            'backup_id': backup_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_bp.route('/system/update', methods=['POST'])
def update_system():
    """Update system software."""
    try:
        data = request.get_json() or {}
        update_type = data.get('type', 'patch')  # patch, minor, major
        
        # Mock update process
        return jsonify({
            'success': True,
            'message': f'System {update_type} update initiated',
            'estimated_duration': '5-10 minutes',
            'requires_restart': True
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_bp.route('/system/metrics', methods=['GET'])
def get_system_metrics():
    """Get detailed system metrics."""
    try:
        # Get query parameters
        hours = request.args.get('hours', 24, type=int)
        
        # Mock metrics data
        metrics = {
            'sync_performance': {
                'avg_drift_ms': 12.5,
                'max_drift_ms': 45.2,
                'sync_events_per_hour': 120,
                'correlation_quality': 0.85
            },
            'device_performance': {
                'avg_cpu_usage': 15.2,
                'avg_memory_usage': 45.8,
                'avg_temperature': 42.1,
                'device_uptime_hours': 168.5
            },
            'network_performance': {
                'avg_latency_ms': 2.1,
                'packet_loss_rate': 0.001,
                'bandwidth_usage_mbps': 1.4,
                'mqtt_messages_per_minute': 45
            },
            'audio_performance': {
                'buffer_underruns': 0,
                'audio_dropouts': 2,
                'stream_uptime_hours': 167.8,
                'quality_score': 0.95
            }
        }
        
        return jsonify({
            'success': True,
            'metrics': metrics,
            'time_range_hours': hours,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

