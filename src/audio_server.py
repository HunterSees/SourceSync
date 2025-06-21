"""
Audio Server Module for SyncStream Transmitter Host

This module handles audio input from various sources and streams it
to the audio buffer for distribution to receiver nodes.
"""

import threading
import time
import logging
import subprocess
import numpy as np
from typing import Optional, Callable, Dict, Any
import queue # Still used by FFmpegSource.read for timeout-based get
from collections import deque # For FFmpegSource internal buffer
import wave
import pyaudio
from src.audio_buffer import AudioBuffer

logger = logging.getLogger(__name__)


class AudioSource:
    """Base class for audio input sources."""
    
    def __init__(self, sample_rate: int = 44100, channels: int = 2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_running = False
        
    def start(self) -> bool:
        """Start the audio source."""
        raise NotImplementedError
    
    def stop(self) -> None:
        """Stop the audio source."""
        raise NotImplementedError
    
    def read(self, frames: int) -> Optional[np.ndarray]:
        """Read audio frames from the source."""
        raise NotImplementedError


class MicrophoneSource(AudioSource):
    """Audio source from system microphone using PyAudio."""
    
    def __init__(self, sample_rate: int = 44100, channels: int = 2, 
                 device_index: Optional[int] = None, chunk_size: int = 1024):
        super().__init__(sample_rate, channels)
        self.device_index = device_index
        self.chunk_size = chunk_size
        self.audio = None
        self.stream = None
        
    def start(self) -> bool:
        """Start microphone capture."""
        try:
            self.audio = pyaudio.PyAudio()
            
            # Find default input device if not specified
            if self.device_index is None:
                self.device_index = self.audio.get_default_input_device_info()['index']
            
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_running = True
            logger.info(f"Started microphone capture: {self.sample_rate}Hz, "
                       f"{self.channels} channels, device {self.device_index}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start microphone: {e}")
            return False
    
    def stop(self) -> None:
        """Stop microphone capture."""
        self.is_running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
        logger.info("Stopped microphone capture")
    
    def read(self, frames: int) -> Optional[np.ndarray]:
        """Read audio frames from microphone."""
        if not self.is_running or not self.stream:
            return None
        
        try:
            # Calculate number of chunks needed
            chunks_needed = (frames + self.chunk_size - 1) // self.chunk_size
            audio_data = []
            
            for _ in range(chunks_needed):
                chunk = self.stream.read(self.chunk_size, exception_on_overflow=False)
                chunk_array = np.frombuffer(chunk, dtype=np.float32)
                
                if self.channels == 2:
                    chunk_array = chunk_array.reshape(-1, 2)
                else:
                    chunk_array = chunk_array.reshape(-1, 1)
                
                audio_data.append(chunk_array)
            
            # Concatenate and trim to requested length
            result = np.concatenate(audio_data, axis=0)[:frames]
            return result
            
        except Exception as e:
            logger.error(f"Error reading from microphone: {e}")
            return None


class FileSource(AudioSource):
    """Audio source from WAV file."""
    
    def __init__(self, filename: str, loop: bool = True):
        self.filename = filename
        self.loop = loop
        self.wave_file = None
        self.position = 0
        
        # Read file info
        try:
            with wave.open(filename, 'rb') as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                self.total_frames = wf.getnframes()
            
            super().__init__(sample_rate, channels)
            logger.info(f"FileSource initialized: {filename}, {sample_rate}Hz, "
                       f"{channels} channels, {self.total_frames} frames")
        except Exception as e:
            logger.error(f"Failed to initialize FileSource: {e}")
            raise
    
    def start(self) -> bool:
        """Start file playback."""
        try:
            self.wave_file = wave.open(self.filename, 'rb')
            self.position = 0
            self.is_running = True
            logger.info(f"Started file playback: {self.filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to start file playback: {e}")
            return False
    
    def stop(self) -> None:
        """Stop file playback."""
        self.is_running = False
        if self.wave_file:
            self.wave_file.close()
            self.wave_file = None
        logger.info("Stopped file playback")
    
    def read(self, frames: int) -> Optional[np.ndarray]:
        """Read audio frames from file."""
        if not self.is_running or not self.wave_file:
            return None
        
        try:
            # Check if we need to loop
            if self.position + frames > self.total_frames:
                if self.loop:
                    # Read remaining frames and loop back
                    remaining = self.total_frames - self.position
                    data1 = self.wave_file.readframes(remaining)
                    
                    # Reset to beginning
                    self.wave_file.rewind()
                    self.position = 0
                    
                    # Read additional frames
                    needed = frames - remaining
                    data2 = self.wave_file.readframes(needed)
                    self.position = needed
                    
                    # Combine data
                    data = data1 + data2
                else:
                    # Read remaining frames only
                    data = self.wave_file.readframes(self.total_frames - self.position)
                    self.position = self.total_frames
            else:
                # Normal read
                data = self.wave_file.readframes(frames)
                self.position += frames
            
            # Convert to numpy array
            if self.wave_file.getsampwidth() == 2:
                audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                audio_array = np.frombuffer(data, dtype=np.float32)
            
            if self.channels == 2:
                audio_array = audio_array.reshape(-1, 2)
            else:
                audio_array = audio_array.reshape(-1, 1)
            
            return audio_array
            
        except Exception as e:
            logger.error(f"Error reading from file: {e}")
            return None


class FFmpegSource(AudioSource):
    """Audio source from FFmpeg subprocess (for streaming, etc.)."""
    
    DEFAULT_FFMPEG_CHUNK_SAMPLES = 1024
    DEFAULT_AUDIO_QUEUE_MAXLEN = 100 # Max number of chunks in the deque

    def __init__(self, input_url: str, sample_rate: int = 44100, channels: int = 2,
                 ffmpeg_chunk_samples: int = DEFAULT_FFMPEG_CHUNK_SAMPLES,
                 audio_queue_maxlen: int = DEFAULT_AUDIO_QUEUE_MAXLEN):
        super().__init__(sample_rate, channels)
        self.input_url = input_url
        self.process = None
        # Calculate chunk size in bytes: samples * channels * 4 bytes/float
        self.ffmpeg_chunk_size_bytes = ffmpeg_chunk_samples * self.channels * 4
        self.audio_queue = deque(maxlen=audio_queue_maxlen)
        self.reader_thread = None
        self._audio_data_lock = threading.Lock() # To protect access to audio_queue
        
    def start(self) -> bool:
        """Start FFmpeg audio capture."""
        try:
            # FFmpeg command to capture audio
            cmd = [
                'ffmpeg',
                '-i', self.input_url,
                '-f', 'f32le',  # 32-bit float little-endian
                '-acodec', 'pcm_f32le',
                '-ar', str(self.sample_rate),
                '-ac', str(self.channels),
                '-'
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            # Start reader thread
            self.is_running = True
            self.reader_thread = threading.Thread(target=self._read_audio_data)
            self.reader_thread.daemon = True
            self.reader_thread.start()
            
            logger.info(f"Started FFmpeg source: {self.input_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start FFmpeg source: {e}")
            return False
    
    def stop(self) -> None:
        """Stop FFmpeg audio capture."""
        self.is_running = False
        
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
        
        if self.reader_thread:
            self.reader_thread.join(timeout=5.0)
        
        logger.info("Stopped FFmpeg source")
    
    def _read_audio_data(self) -> None:
        """Read audio data from FFmpeg process in background thread."""
        while self.is_running and self.process and self.process.stdout:
            try:
                data = self.process.stdout.read(self.ffmpeg_chunk_size_bytes)
                if not data:
                    logger.info("FFmpeg stdout stream ended.")
                    break
                
                # Convert to numpy array
                audio_array = np.frombuffer(data, dtype=np.float32)
                if self.channels == 2:
                    # Ensure correct shape even if last chunk is partial
                    if audio_array.size % 2 == 0:
                        audio_array = audio_array.reshape(-1, 2)
                    else: # Should not happen with f32le, but good to be safe
                        logger.warning("Received odd number of samples for stereo, discarding last sample.")
                        audio_array = audio_array[:-1].reshape(-1, 2)
                else:
                    audio_array = audio_array.reshape(-1, 1)
                
                if audio_array.size > 0:
                    with self._audio_data_lock:
                        self.audio_queue.append(audio_array)
                        
            except Exception as e:
                if self.is_running: # Don't log errors if we are stopping
                    logger.error(f"Error reading FFmpeg data: {e}")
                break
    
    def read(self, frames: int) -> Optional[np.ndarray]:
        """Read audio frames from FFmpeg source."""
        if not self.is_running:
            return None
        
        try:
            # Collect audio data from deque
            audio_chunks_to_process = []
            frames_collected = 0
            
            with self._audio_data_lock:
                while self.audio_queue and frames_collected < frames:
                    chunk = self.audio_queue.popleft()
                    audio_chunks_to_process.append(chunk)
                    frames_collected += len(chunk) # Assumes len gives number of frames

            if not audio_chunks_to_process:
                # To prevent busy-waiting if called in a tight loop, sleep briefly
                # This behavior is different from queue.get(timeout=0.1)
                # If the caller expects blocking, this needs more advanced handling (e.g. Condition)
                time.sleep(0.01)
                return None
            
            # Concatenate and trim to requested length
            # This is done outside the lock to minimize lock holding time
            result_array = np.concatenate(audio_chunks_to_process, axis=0)

            # If we collected more frames than needed, put the excess back
            # This is important to avoid data loss if frames_collected > frames
            if frames_collected > frames:
                excess_frames = frames_collected - frames
                excess_data = result_array[frames:]
                result_array = result_array[:frames]

                # The excess data needs to be reshaped correctly if it's stereo
                # and then put back into the deque AT THE FRONT
                if self.channels == 2:
                    excess_data = excess_data.reshape(-1, 2)
                else:
                    excess_data = excess_data.reshape(-1, 1)

                with self._audio_data_lock:
                    self.audio_queue.appendleft(excess_data)

            return result_array
            
        except Exception as e:
            logger.error(f"Error reading from FFmpeg source deque: {e}")
            return None


class AudioServer:
    """
    Main audio server that manages audio sources and streams to buffer.
    """
    
    def __init__(self, audio_buffer: AudioBuffer, chunk_duration: float = 0.1):
        """
        Initialize audio server.
        
        Args:
            audio_buffer: AudioBuffer instance to write audio data
            chunk_duration: Duration of each audio chunk in seconds
        """
        self.audio_buffer = audio_buffer
        self.chunk_duration = chunk_duration
        self.chunk_frames = int(audio_buffer.sample_rate * chunk_duration)
        
        # Audio source management
        self.current_source: Optional[AudioSource] = None
        self.source_lock = threading.Lock()
        
        # Streaming control
        self.is_streaming = False
        self.stream_thread: Optional[threading.Thread] = None
        
        # Statistics
        self.chunks_processed = 0
        self.bytes_processed = 0
        self.start_time = 0.0
        
        logger.info(f"AudioServer initialized: chunk_duration={chunk_duration}s, "
                   f"chunk_frames={self.chunk_frames}")
    
    def set_source(self, source: AudioSource) -> bool:
        """
        Set the current audio source.
        
        Args:
            source: AudioSource instance
        
        Returns:
            True if source set successfully
        """
        with self.source_lock:
            # Stop current source if running
            if self.current_source and self.current_source.is_running:
                self.current_source.stop()
            
            self.current_source = source
            
            # Verify source compatibility
            if (source.sample_rate != self.audio_buffer.sample_rate or
                source.channels != self.audio_buffer.channels):
                logger.warning(f"Source format mismatch: source={source.sample_rate}Hz/"
                             f"{source.channels}ch, buffer={self.audio_buffer.sample_rate}Hz/"
                             f"{self.audio_buffer.channels}ch")
            
            logger.info(f"Audio source set: {type(source).__name__}")
            return True
    
    def start_streaming(self) -> bool:
        """Start audio streaming from current source to buffer."""
        if self.is_streaming:
            logger.warning("Audio streaming already running")
            return True
        
        if not self.current_source:
            logger.error("No audio source set")
            return False
        
        # Start audio source
        if not self.current_source.start():
            logger.error("Failed to start audio source")
            return False
        
        # Start streaming thread
        self.is_streaming = True
        self.start_time = time.time()
        self.chunks_processed = 0
        self.bytes_processed = 0
        
        self.stream_thread = threading.Thread(target=self._stream_audio)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        
        logger.info("Started audio streaming")
        return True
    
    def stop_streaming(self) -> None:
        """Stop audio streaming."""
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        
        # Stop audio source
        with self.source_lock:
            if self.current_source:
                self.current_source.stop()
        
        # Wait for streaming thread to finish
        if self.stream_thread:
            self.stream_thread.join(timeout=5.0)
        
        logger.info("Stopped audio streaming")
    
    def _stream_audio(self) -> None:
        """Main audio streaming loop."""
        logger.info("Audio streaming thread started")
        
        while self.is_streaming:
            try:
                # Read audio chunk from source
                with self.source_lock:
                    if not self.current_source or not self.current_source.is_running:
                        break
                    
                    audio_chunk = self.current_source.read(self.chunk_frames)
                
                if audio_chunk is not None and len(audio_chunk) > 0:
                    # Write to buffer
                    self.audio_buffer.write(audio_chunk)
                    
                    # Update statistics
                    self.chunks_processed += 1
                    self.bytes_processed += audio_chunk.nbytes
                    
                    if self.chunks_processed % 100 == 0:
                        logger.debug(f"Processed {self.chunks_processed} chunks, "
                                   f"{self.bytes_processed / 1024:.1f} KB")
                else:
                    # No audio data available, short sleep
                    time.sleep(0.01)
                    
            except Exception as e:
                logger.error(f"Error in audio streaming loop: {e}")
                break
        
        logger.info("Audio streaming thread finished")
    
    def get_statistics(self) -> dict:
        """Get audio server statistics."""
        current_time = time.time()
        uptime = current_time - self.start_time if self.start_time > 0 else 0
        
        stats = {
            'is_streaming': self.is_streaming,
            'chunks_processed': self.chunks_processed,
            'bytes_processed': self.bytes_processed,
            'uptime': uptime,
            'chunk_duration': self.chunk_duration,
            'chunk_frames': self.chunk_frames
        }
        
        if self.current_source:
            stats['source_type'] = type(self.current_source).__name__
            stats['source_sample_rate'] = self.current_source.sample_rate
            stats['source_channels'] = self.current_source.channels
            stats['source_running'] = self.current_source.is_running
        
        if uptime > 0 and self.chunks_processed > 0:
            stats['chunks_per_second'] = self.chunks_processed / uptime
            stats['bytes_per_second'] = self.bytes_processed / uptime
        
        return stats


if __name__ == "__main__":
    # Test the audio server
    logging.basicConfig(level=logging.DEBUG)
    
    # Create audio buffer and server
    buffer = AudioBuffer(sample_rate=44100, buffer_duration=5.0, channels=2)
    server = AudioServer(buffer, chunk_duration=0.1)
    
    # Test with microphone source
    try:
        mic_source = MicrophoneSource(sample_rate=44100, channels=2)
        server.set_source(mic_source)
        
        if server.start_streaming():
            print("Audio streaming started. Press Ctrl+C to stop.")
            
            while True:
                time.sleep(1)
                stats = server.get_statistics()
                print(f"Chunks: {stats['chunks_processed']}, "
                      f"Bytes: {stats['bytes_processed']}")
                
    except KeyboardInterrupt:
        print("\nStopping audio server...")
        server.stop_streaming()
    except Exception as e:
        print(f"Error: {e}")
        # Fallback to test tone
        print("Microphone not available, testing with file source...")
        
        # Create a test WAV file with sine wave
        import wave
        test_file = "/tmp/test_tone.wav"
        with wave.open(test_file, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            
            # Generate 5 seconds of 440Hz tone
            duration = 5.0
            samples = int(44100 * duration)
            t = np.linspace(0, duration, samples)
            tone = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
            stereo_tone = np.column_stack([tone, tone])
            wf.writeframes(stereo_tone.tobytes())
        
        # Test with file source
        file_source = FileSource(test_file, loop=True)
        server.set_source(file_source)
        
        if server.start_streaming():
            print("File streaming started. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
                    stats = server.get_statistics()
                    print(f"Chunks: {stats['chunks_processed']}")
            except KeyboardInterrupt:
                pass
        
        server.stop_streaming()

