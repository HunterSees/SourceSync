"""
Shared Logger Module for SyncStream

This module provides unified logging configuration and utilities
for both transmitter and receiver components.
"""

import logging
import logging.handlers
import os
import sys
import time
import threading
from typing import Optional, Dict, Any
import json


class SyncStreamFormatter(logging.Formatter):
    """Custom formatter for SyncStream logs."""
    
    def __init__(self, include_thread: bool = True, include_module: bool = True):
        """
        Initialize formatter.
        
        Args:
            include_thread: Include thread name in log messages
            include_module: Include module name in log messages
        """
        self.include_thread = include_thread
        self.include_module = include_module
        
        # Define format string
        format_parts = ['%(asctime)s']
        
        if include_thread:
            format_parts.append('[%(threadName)s]')
        
        format_parts.extend(['%(levelname)s', '%(name)s'])
        
        if include_module:
            format_parts.append('(%(module)s:%(lineno)d)')
        
        format_parts.append('- %(message)s')
        
        format_string = ' '.join(format_parts)
        
        super().__init__(
            fmt=format_string,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record):
        """Format log record with custom styling."""
        # Add color coding for console output
        if hasattr(record, 'stream_handler') and record.stream_handler:
            level_colors = {
                'DEBUG': '\033[36m',    # Cyan
                'INFO': '\033[32m',     # Green
                'WARNING': '\033[33m',  # Yellow
                'ERROR': '\033[31m',    # Red
                'CRITICAL': '\033[35m'  # Magenta
            }
            
            reset_color = '\033[0m'
            color = level_colors.get(record.levelname, '')
            
            # Apply color to level name
            original_levelname = record.levelname
            record.levelname = f"{color}{record.levelname}{reset_color}"
            
            formatted = super().format(record)
            
            # Restore original level name
            record.levelname = original_levelname
            
            return formatted
        
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            'timestamp': time.time(),
            'datetime': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.threadName,
            'message': record.getMessage()
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class SyncStreamLogger:
    """
    Main logger class for SyncStream components.
    
    Provides unified logging configuration with support for:
    - Console output with colors
    - File output with rotation
    - JSON structured logging
    - Performance monitoring
    - Component-specific loggers
    """
    
    def __init__(self, component_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize SyncStream logger.
        
        Args:
            component_name: Name of the component (e.g., 'transmitter', 'receiver')
            config: Logging configuration dictionary
        """
        self.component_name = component_name
        self.config = config or {}
        
        # Default configuration
        self.default_config = {
            'level': 'INFO',
            'console_output': True,
            'file_output': True,
            'file_path': f'/var/log/syncstream/{component_name}.log',
            'max_file_size': 10 * 1024 * 1024,  # 10MB
            'backup_count': 5,
            'json_format': False,
            'include_thread': True,
            'include_module': True,
            'performance_logging': False
        }
        
        # Merge with provided config
        self.effective_config = {**self.default_config, **self.config}
        
        # Initialize loggers
        self.root_logger = None
        self.performance_logger = None
        self._setup_logging()
        
        # Performance tracking
        self.performance_data = {}
        self.performance_lock = threading.Lock()
    
    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        # Create root logger for this component
        logger_name = f"syncstream.{self.component_name}"
        self.root_logger = logging.getLogger(logger_name)
        
        # Set level
        level = getattr(logging, self.effective_config['level'].upper(), logging.INFO)
        self.root_logger.setLevel(level)
        
        # Clear existing handlers
        self.root_logger.handlers.clear()
        
        # Console handler
        if self.effective_config['console_output']:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            
            if self.effective_config['json_format']:
                console_formatter = JSONFormatter()
            else:
                console_formatter = SyncStreamFormatter(
                    include_thread=self.effective_config['include_thread'],
                    include_module=self.effective_config['include_module']
                )
            
            console_handler.setFormatter(console_formatter)
            
            # Add marker for color formatting
            console_handler.addFilter(lambda record: setattr(record, 'stream_handler', True) or True)
            
            self.root_logger.addHandler(console_handler)
        
        # File handler
        if self.effective_config['file_output']:
            file_path = self.effective_config['file_path']
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=self.effective_config['max_file_size'],
                backupCount=self.effective_config['backup_count']
            )
            file_handler.setLevel(level)
            
            if self.effective_config['json_format']:
                file_formatter = JSONFormatter()
            else:
                file_formatter = SyncStreamFormatter(
                    include_thread=self.effective_config['include_thread'],
                    include_module=self.effective_config['include_module']
                )
            
            file_handler.setFormatter(file_formatter)
            self.root_logger.addHandler(file_handler)
        
        # Performance logger
        if self.effective_config['performance_logging']:
            perf_logger_name = f"{logger_name}.performance"
            self.performance_logger = logging.getLogger(perf_logger_name)
            self.performance_logger.setLevel(logging.DEBUG)
            
            # Separate file for performance logs
            perf_file_path = self.effective_config['file_path'].replace('.log', '_performance.log')
            perf_handler = logging.handlers.RotatingFileHandler(
                perf_file_path,
                maxBytes=self.effective_config['max_file_size'],
                backupCount=self.effective_config['backup_count']
            )
            
            perf_formatter = JSONFormatter()
            perf_handler.setFormatter(perf_formatter)
            self.performance_logger.addHandler(perf_handler)
        
        # Log initialization
        self.root_logger.info(f"SyncStream logger initialized for {self.component_name}")
        self.root_logger.debug(f"Logging configuration: {self.effective_config}")
    
    def get_logger(self, module_name: str = None) -> logging.Logger:
        """
        Get logger for specific module.
        
        Args:
            module_name: Name of the module (optional)
        
        Returns:
            Logger instance
        """
        if module_name:
            logger_name = f"syncstream.{self.component_name}.{module_name}"
            return logging.getLogger(logger_name)
        else:
            return self.root_logger
    
    def log_performance(self, operation: str, duration: float, 
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log performance metrics.
        
        Args:
            operation: Name of the operation
            duration: Duration in seconds
            metadata: Additional metadata
        """
        if not self.performance_logger:
            return
        
        with self.performance_lock:
            # Update performance statistics
            if operation not in self.performance_data:
                self.performance_data[operation] = {
                    'count': 0,
                    'total_time': 0.0,
                    'min_time': float('inf'),
                    'max_time': 0.0
                }
            
            stats = self.performance_data[operation]
            stats['count'] += 1
            stats['total_time'] += duration
            stats['min_time'] = min(stats['min_time'], duration)
            stats['max_time'] = max(stats['max_time'], duration)
            stats['avg_time'] = stats['total_time'] / stats['count']
            
            # Log performance event
            perf_data = {
                'operation': operation,
                'duration': duration,
                'count': stats['count'],
                'avg_duration': stats['avg_time'],
                'min_duration': stats['min_time'],
                'max_duration': stats['max_time']
            }
            
            if metadata:
                perf_data.update(metadata)
            
            # Add performance data as extra fields
            record = self.performance_logger.makeRecord(
                self.performance_logger.name,
                logging.INFO,
                __file__,
                0,
                f"Performance: {operation}",
                (),
                None
            )
            
            for key, value in perf_data.items():
                setattr(record, key, value)
            
            self.performance_logger.handle(record)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        with self.performance_lock:
            return self.performance_data.copy()
    
    def reset_performance_stats(self) -> None:
        """Reset performance statistics."""
        with self.performance_lock:
            self.performance_data.clear()
            if self.performance_logger:
                self.performance_logger.info("Performance statistics reset")
    
    def set_level(self, level: str) -> None:
        """
        Change logging level.
        
        Args:
            level: New logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.root_logger.setLevel(log_level)
        
        for handler in self.root_logger.handlers:
            handler.setLevel(log_level)
        
        self.root_logger.info(f"Logging level changed to {level}")
    
    def add_context_filter(self, context: Dict[str, Any]) -> None:
        """
        Add context information to all log messages.
        
        Args:
            context: Context dictionary to add to logs
        """
        class ContextFilter(logging.Filter):
            def filter(self, record):
                for key, value in context.items():
                    setattr(record, key, value)
                return True
        
        context_filter = ContextFilter()
        self.root_logger.addFilter(context_filter)
        
        self.root_logger.debug(f"Added context filter: {context}")


class PerformanceTimer:
    """Context manager for performance timing."""
    
    def __init__(self, logger: SyncStreamLogger, operation: str, 
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize performance timer.
        
        Args:
            logger: SyncStreamLogger instance
            operation: Operation name
            metadata: Additional metadata
        """
        self.logger = logger
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log performance."""
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.logger.log_performance(self.operation, duration, self.metadata)


# Global logger instances
_loggers: Dict[str, SyncStreamLogger] = {}
_logger_lock = threading.Lock()


def get_logger(component_name: str, config: Optional[Dict[str, Any]] = None) -> SyncStreamLogger:
    """
    Get or create logger for component.
    
    Args:
        component_name: Name of the component
        config: Logging configuration (only used for new loggers)
    
    Returns:
        SyncStreamLogger instance
    """
    with _logger_lock:
        if component_name not in _loggers:
            _loggers[component_name] = SyncStreamLogger(component_name, config)
        return _loggers[component_name]


def setup_logging(component_name: str, config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Set up logging for a component and return standard logger.
    
    Args:
        component_name: Name of the component
        config: Logging configuration
    
    Returns:
        Standard Python logger instance
    """
    syncstream_logger = get_logger(component_name, config)
    return syncstream_logger.get_logger()


if __name__ == "__main__":
    # Test logging functionality
    print("Testing SyncStream logging...")
    
    # Test basic logging
    config = {
        'level': 'DEBUG',
        'console_output': True,
        'file_output': False,  # Disable file output for testing
        'performance_logging': True,
        'include_thread': True,
        'include_module': True
    }
    
    logger = get_logger('test_component', config)
    test_log = logger.get_logger('test_module')
    
    # Test different log levels
    test_log.debug("This is a debug message")
    test_log.info("This is an info message")
    test_log.warning("This is a warning message")
    test_log.error("This is an error message")
    
    # Test performance logging
    with PerformanceTimer(logger, 'test_operation', {'test_param': 'value'}):
        time.sleep(0.1)  # Simulate work
    
    # Test performance logging again
    with PerformanceTimer(logger, 'test_operation'):
        time.sleep(0.05)
    
    # Print performance stats
    stats = logger.get_performance_stats()
    print(f"\nPerformance stats: {stats}")
    
    # Test context filter
    logger.add_context_filter({'device_id': 'test_device', 'version': '1.0'})
    test_log.info("Message with context")
    
    print("\nLogging test completed!")

