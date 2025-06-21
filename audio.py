from flask import Blueprint, request, jsonify, Response
from src.models.device import db, Device
import json
import time
import numpy as np

audio_bp = Blueprint('audio', __name__)

# Mock audio buffer for demonstration
class MockAudioBuffer:
    def __init__(self):
        self.sample_rate = 44100
        self.channels = 2
        self.buffer_duration = 10.0
        self.start_time = time.time()
    
    def get_buffer_info(self):
        return {
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'buffer_duration': self.buffer_duration,
            'uptime': time.time() - self.start_time,
            'buffer_fill': 0.8,  # Mock 80% fill
            'last_write_time': time.time()
        }
    
    def get_latest_audio(self, duration):
        # Generate mock audio data (sine wave)
        samples = int(duration * self.sample_rate)
        t = np.linspace(0, duration, samples)
        # 440Hz sine wave
        audio = 0.5 * np.sin(2 * np.pi * 440 * t)
        
        if self.channels == 2:
            # Convert to stereo
            audio = np.column_stack([audio, audio])
        
        return audio.astype(np.float32)

# Global mock audio buffer
mock_buffer = MockAudioBuffer()

@audio_bp.route('/audio/buffer/info', methods=['GET'])
def get_buffer_info():
    """Get audio buffer information."""
    try:
        buffer_info = mock_buffer.get_buffer_info()
        
        return jsonify({
            'success': True,
            'buffer_info': buffer_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@audio_bp.route('/audio/buffer', methods=['GET'])
def get_audio_buffer():
    """Get audio buffer data for drift detection."""
    try:
        # Get query parameters
        duration = request.args.get('duration', 2.0, type=float)
        offset = request.args.get('offset', 0.0, type=float)
        format_type = request.args.get('format', 'json')
        
        # Validate parameters
        if duration <= 0 or duration > 10:
            return jsonify({
                'success': False,
                'error': 'Duration must be between 0 and 10 seconds'
            }), 400
        
        # Get audio data
        audio_data = mock_buffer.get_latest_audio(duration)
        
        if format_type == 'raw':
            # Return raw binary data
            response = Response(
                audio_data.tobytes(),
                mimetype='application/octet-stream'
            )
            response.headers['X-Sample-Rate'] = str(mock_buffer.sample_rate)
            response.headers['X-Channels'] = str(mock_buffer.channels)
            response.headers['X-Duration'] = str(duration)
            response.headers['X-Samples'] = str(len(audio_data))
            return response
        
        else:
            # Return JSON data
            return jsonify({
                'success': True,
                'audio_data': audio_data.tolist(),
                'metadata': {
                    'sample_rate': mock_buffer.sample_rate,
                    'channels': mock_buffer.channels,
                    'duration': duration,
                    'samples': len(audio_data),
                    'timestamp': time.time()
                }
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@audio_bp.route('/audio/stream/info', methods=['GET'])
def get_stream_info():
    """Get audio stream information."""
    try:
        # Mock stream info
        stream_info = {
            'is_streaming': True,
            'stream_url': 'http://localhost:8080/audio/stream',
            'format': 'PCM',
            'sample_rate': 44100,
            'channels': 2,
            'bitrate': 1411,  # kbps for CD quality
            'codec': 'pcm_s16le',
            'uptime': time.time() - mock_buffer.start_time,
            'connected_devices': Device.query.filter_by(is_online=True, is_playing=True).count()
        }
        
        return jsonify({
            'success': True,
            'stream_info': stream_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@audio_bp.route('/audio/stream/start', methods=['POST'])
def start_audio_stream():
    """Start audio streaming."""
    try:
        data = request.get_json() or {}
        source_type = data.get('source_type', 'microphone')
        
        # Mock stream start
        # In real implementation, this would start the audio server
        
        return jsonify({
            'success': True,
            'message': f'Audio stream started with source: {source_type}',
            'stream_url': 'http://localhost:8080/audio/stream'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@audio_bp.route('/audio/stream/stop', methods=['POST'])
def stop_audio_stream():
    """Stop audio streaming."""
    try:
        # Mock stream stop
        # In real implementation, this would stop the audio server
        
        return jsonify({
            'success': True,
            'message': 'Audio stream stopped'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@audio_bp.route('/audio/sources', methods=['GET'])
def get_audio_sources():
    """Get available audio sources."""
    try:
        # Mock audio sources
        sources = [
            {
                'id': 'microphone',
                'name': 'System Microphone',
                'type': 'microphone',
                'available': True,
                'description': 'Default system microphone input'
            },
            {
                'id': 'line_in',
                'name': 'Line Input',
                'type': 'line',
                'available': True,
                'description': 'Analog line input'
            },
            {
                'id': 'file_test',
                'name': 'Test Audio File',
                'type': 'file',
                'available': True,
                'description': 'Test audio file for demonstration'
            },
            {
                'id': 'stream_url',
                'name': 'Network Stream',
                'type': 'stream',
                'available': False,
                'description': 'Audio stream from network URL'
            }
        ]
        
        return jsonify({
            'success': True,
            'sources': sources
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@audio_bp.route('/audio/test-tone', methods=['POST'])
def generate_test_tone():
    """Generate test tone for calibration."""
    try:
        data = request.get_json() or {}
        frequency = data.get('frequency', 1000)  # Hz
        duration = data.get('duration', 5)  # seconds
        amplitude = data.get('amplitude', 0.5)  # 0.0 to 1.0
        
        # Validate parameters
        if frequency < 20 or frequency > 20000:
            return jsonify({
                'success': False,
                'error': 'Frequency must be between 20 and 20000 Hz'
            }), 400
        
        if duration < 0.1 or duration > 30:
            return jsonify({
                'success': False,
                'error': 'Duration must be between 0.1 and 30 seconds'
            }), 400
        
        if amplitude < 0.0 or amplitude > 1.0:
            return jsonify({
                'success': False,
                'error': 'Amplitude must be between 0.0 and 1.0'
            }), 400
        
        # TODO: Generate and play test tone on all devices
        # For now, just return success
        
        return jsonify({
            'success': True,
            'message': f'Test tone generated: {frequency}Hz for {duration}s',
            'parameters': {
                'frequency': frequency,
                'duration': duration,
                'amplitude': amplitude
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@audio_bp.route('/audio/volume', methods=['POST'])
def set_global_volume():
    """Set global volume for all devices."""
    try:
        data = request.get_json()
        
        if not data or 'volume' not in data:
            return jsonify({
                'success': False,
                'error': 'Volume is required'
            }), 400
        
        volume = data['volume']
        
        if volume < 0.0 or volume > 1.0:
            return jsonify({
                'success': False,
                'error': 'Volume must be between 0.0 and 1.0'
            }), 400
        
        # Update all online devices
        devices = Device.query.filter_by(is_online=True).all()
        
        for device in devices:
            device.volume = volume
        
        db.session.commit()
        
        # TODO: Send volume commands via MQTT
        
        return jsonify({
            'success': True,
            'message': f'Global volume set to {volume:.1%}',
            'device_count': len(devices)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@audio_bp.route('/audio/mute', methods=['POST'])
def set_global_mute():
    """Set global mute for all devices."""
    try:
        data = request.get_json()
        
        if not data or 'muted' not in data:
            return jsonify({
                'success': False,
                'error': 'Muted state is required'
            }), 400
        
        muted = data['muted']
        
        # Update all online devices
        devices = Device.query.filter_by(is_online=True).all()
        
        for device in devices:
            device.is_muted = muted
        
        db.session.commit()
        
        # TODO: Send mute commands via MQTT
        
        action = 'muted' if muted else 'unmuted'
        return jsonify({
            'success': True,
            'message': f'All devices {action}',
            'device_count': len(devices)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@audio_bp.route('/audio/latency/test', methods=['POST'])
def test_audio_latency():
    """Test audio latency for devices."""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id')
        
        if device_id:
            # Test specific device
            device = Device.query.filter_by(device_id=device_id).first()
            if not device:
                return jsonify({
                    'success': False,
                    'error': 'Device not found'
                }), 404
            
            # Mock latency test
            # In real implementation, this would measure round-trip latency
            mock_latency = device.base_latency_ms + np.random.normal(0, 10)  # Add some noise
            
            return jsonify({
                'success': True,
                'device_id': device_id,
                'latency_ms': mock_latency,
                'message': f'Latency test completed for {device_id}'
            })
        
        else:
            # Test all online devices
            devices = Device.query.filter_by(is_online=True).all()
            results = []
            
            for device in devices:
                mock_latency = device.base_latency_ms + np.random.normal(0, 10)
                results.append({
                    'device_id': device.device_id,
                    'device_name': device.device_name,
                    'latency_ms': mock_latency
                })
            
            return jsonify({
                'success': True,
                'results': results,
                'device_count': len(results),
                'message': 'Latency test completed for all devices'
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

