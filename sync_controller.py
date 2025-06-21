"""
Sync Controller Module for SyncStream Transmitter Host

This module receives drift reports from receiver nodes and calculates
buffer offset adjustments to maintain synchronization across all devices.
"""

import threading
import time
import json
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
import statistics

logger = logging.getLogger(__name__)


class DeviceState:
    """Represents the synchronization state of a single receiver device."""
    
    def __init__(self, device_id: str, base_latency_ms: float = 0.0):
        self.device_id = device_id
        self.base_latency_ms = base_latency_ms
        
        # Drift tracking
        self.drift_history = deque(maxlen=50)  # Keep last 50 drift measurements
        self.last_drift_ms = 0.0
        self.last_drift_time = 0.0
        
        # Buffer offset management
        self.current_offset_ms = 0.0
        self.target_offset_ms = 0.0
        
        # Statistics
        self.drift_variance = 0.0
        self.avg_drift_ms = 0.0
        self.connection_quality = 1.0  # 0.0 to 1.0
        
        # Status
        self.is_online = False
        self.last_seen = 0.0
        
        logger.info(f"DeviceState created for {device_id} with base latency {base_latency_ms}ms")
    
    def update_drift(self, drift_ms: float, signal_strength: float = -50.0) -> None:
        """Update drift measurement for this device."""
        current_time = time.time()
        
        self.drift_history.append({
            'drift_ms': drift_ms,
            'timestamp': current_time,
            'signal_strength': signal_strength
        })
        
        self.last_drift_ms = drift_ms
        self.last_drift_time = current_time
        self.is_online = True
        self.last_seen = current_time
        
        # Update statistics
        if len(self.drift_history) >= 3:
            recent_drifts = [d['drift_ms'] for d in list(self.drift_history)[-10:]]
            self.avg_drift_ms = statistics.mean(recent_drifts)
            self.drift_variance = statistics.variance(recent_drifts) if len(recent_drifts) > 1 else 0.0
            
            # Update connection quality based on signal strength and drift stability
            signal_quality = max(0.0, min(1.0, (signal_strength + 80) / 30))  # -80 to -50 dBm range
            drift_stability = max(0.0, min(1.0, 1.0 - (self.drift_variance / 100.0)))
            self.connection_quality = (signal_quality + drift_stability) / 2.0
        
        logger.debug(f"Device {self.device_id}: drift={drift_ms:.1f}ms, "
                    f"avg={self.avg_drift_ms:.1f}ms, quality={self.connection_quality:.2f}")
    
    def calculate_target_offset(self, reference_drift: float = 0.0) -> float:
        """Calculate target buffer offset to synchronize with reference."""
        if not self.drift_history:
            return self.base_latency_ms
        
        # Use smoothed drift value
        smoothed_drift = self.avg_drift_ms if len(self.drift_history) >= 3 else self.last_drift_ms
        
        # Calculate offset to compensate for drift relative to reference
        compensation = reference_drift - smoothed_drift
        
        # Apply base latency and compensation
        target = self.base_latency_ms + compensation
        
        logger.debug(f"Device {self.device_id}: target_offset={target:.1f}ms "
                    f"(base={self.base_latency_ms:.1f}ms, comp={compensation:.1f}ms)")
        
        return target
    
    def is_stable(self, max_variance: float = 25.0) -> bool:
        """Check if device drift is stable enough for synchronization."""
        return (len(self.drift_history) >= 5 and 
                self.drift_variance <= max_variance and
                self.connection_quality >= 0.5)
    
    def get_status(self) -> dict:
        """Get current status of this device."""
        current_time = time.time()
        return {
            'device_id': self.device_id,
            'is_online': self.is_online and (current_time - self.last_seen) < 30.0,
            'last_drift_ms': self.last_drift_ms,
            'avg_drift_ms': self.avg_drift_ms,
            'drift_variance': self.drift_variance,
            'current_offset_ms': self.current_offset_ms,
            'target_offset_ms': self.target_offset_ms,
            'connection_quality': self.connection_quality,
            'is_stable': self.is_stable(),
            'last_seen': self.last_seen,
            'drift_measurements': len(self.drift_history)
        }


class SyncController:
    """
    Main synchronization controller that manages drift correction
    and buffer offset calculations for all receiver devices.
    """
    
    def __init__(self, sync_tolerance_ms: float = 10.0, 
                 adjustment_rate: float = 0.1):
        """
        Initialize the sync controller.
        
        Args:
            sync_tolerance_ms: Maximum allowed drift before correction
            adjustment_rate: Rate of offset adjustment (0.0 to 1.0)
        """
        self.sync_tolerance_ms = sync_tolerance_ms
        self.adjustment_rate = adjustment_rate
        
        # Device management
        self.devices: Dict[str, DeviceState] = {}
        self.device_configs: Dict[str, dict] = {}
        
        # Synchronization state
        self.reference_device: Optional[str] = None
        self.sync_groups: Dict[str, List[str]] = {'default': []}
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Statistics
        self.sync_events = 0
        self.last_sync_time = 0.0
        
        logger.info(f"SyncController initialized with tolerance={sync_tolerance_ms}ms, "
                   f"adjustment_rate={adjustment_rate}")
    
    def register_device(self, device_id: str, config: dict) -> None:
        """Register a new receiver device."""
        with self.lock:
            base_latency = config.get('base_latency_ms', 0.0)
            device_type = config.get('type', 'unknown')
            sync_group = config.get('sync_group', 'default')
            
            self.devices[device_id] = DeviceState(device_id, base_latency)
            self.device_configs[device_id] = config.copy()
            
            # Add to sync group
            if sync_group not in self.sync_groups:
                self.sync_groups[sync_group] = []
            if device_id not in self.sync_groups[sync_group]:
                self.sync_groups[sync_group].append(device_id)
            
            logger.info(f"Registered device {device_id} (type={device_type}, "
                       f"group={sync_group}, base_latency={base_latency}ms)")
    
    def update_device_drift(self, device_id: str, drift_ms: float, 
                           signal_strength: float = -50.0) -> None:
        """Update drift measurement for a device."""
        with self.lock:
            if device_id not in self.devices:
                logger.warning(f"Received drift update for unknown device: {device_id}")
                return
            
            self.devices[device_id].update_drift(drift_ms, signal_strength)
            
            # Trigger synchronization check
            self._check_synchronization()
    
    def _check_synchronization(self) -> None:
        """Check if synchronization adjustments are needed."""
        current_time = time.time()
        
        # Don't sync too frequently
        if current_time - self.last_sync_time < 1.0:
            return
        
        for group_name, device_ids in self.sync_groups.items():
            self._sync_group(group_name, device_ids)
        
        self.last_sync_time = current_time
    
    def _sync_group(self, group_name: str, device_ids: List[str]) -> None:
        """Synchronize devices within a group."""
        # Get online and stable devices in group
        stable_devices = []
        for device_id in device_ids:
            if (device_id in self.devices and 
                self.devices[device_id].is_online and
                self.devices[device_id].is_stable()):
                stable_devices.append(device_id)
        
        if len(stable_devices) < 2:
            return  # Need at least 2 devices to sync
        
        # Calculate reference drift (median of stable devices)
        drifts = [self.devices[device_id].avg_drift_ms for device_id in stable_devices]
        reference_drift = statistics.median(drifts)
        
        # Update target offsets for all devices in group
        adjustments_made = 0
        for device_id in device_ids:
            if device_id not in self.devices:
                continue
                
            device = self.devices[device_id]
            new_target = device.calculate_target_offset(reference_drift)
            
            # Check if adjustment is needed
            offset_diff = abs(new_target - device.target_offset_ms)
            if offset_diff > self.sync_tolerance_ms:
                # Apply gradual adjustment
                adjustment = (new_target - device.current_offset_ms) * self.adjustment_rate
                device.current_offset_ms += adjustment
                device.target_offset_ms = new_target
                adjustments_made += 1
                
                logger.info(f"Adjusted {device_id} offset: {device.current_offset_ms:.1f}ms "
                           f"(target: {new_target:.1f}ms)")
        
        if adjustments_made > 0:
            self.sync_events += 1
            logger.info(f"Synchronized group '{group_name}': {adjustments_made} adjustments, "
                       f"reference_drift={reference_drift:.1f}ms")
    
    def get_device_offset(self, device_id: str) -> float:
        """Get current buffer offset for a device."""
        with self.lock:
            if device_id in self.devices:
                return self.devices[device_id].current_offset_ms
            return 0.0
    
    def get_all_offsets(self) -> Dict[str, float]:
        """Get current buffer offsets for all devices."""
        with self.lock:
            return {device_id: device.current_offset_ms 
                   for device_id, device in self.devices.items()}
    
    def get_device_status(self, device_id: str) -> Optional[dict]:
        """Get status for a specific device."""
        with self.lock:
            if device_id in self.devices:
                return self.devices[device_id].get_status()
            return None
    
    def get_all_status(self) -> dict:
        """Get status for all devices and sync controller."""
        with self.lock:
            device_statuses = {device_id: device.get_status() 
                             for device_id, device in self.devices.items()}
            
            return {
                'devices': device_statuses,
                'sync_groups': self.sync_groups,
                'sync_events': self.sync_events,
                'last_sync_time': self.last_sync_time,
                'sync_tolerance_ms': self.sync_tolerance_ms,
                'adjustment_rate': self.adjustment_rate
            }
    
    def force_resync(self, group_name: str = None) -> None:
        """Force immediate resynchronization of a group or all groups."""
        with self.lock:
            if group_name and group_name in self.sync_groups:
                self._sync_group(group_name, self.sync_groups[group_name])
                logger.info(f"Forced resync of group '{group_name}'")
            else:
                for group_name, device_ids in self.sync_groups.items():
                    self._sync_group(group_name, device_ids)
                logger.info("Forced resync of all groups")
            
            self.last_sync_time = time.time()


if __name__ == "__main__":
    # Test the sync controller
    logging.basicConfig(level=logging.DEBUG)
    
    # Create sync controller
    controller = SyncController(sync_tolerance_ms=15.0, adjustment_rate=0.2)
    
    # Register test devices
    controller.register_device("living_room", {
        "type": "chromecast",
        "base_latency_ms": 300,
        "sync_group": "main_floor"
    })
    
    controller.register_device("kitchen", {
        "type": "analog",
        "base_latency_ms": 50,
        "sync_group": "main_floor"
    })
    
    controller.register_device("bedroom", {
        "type": "hdmi",
        "base_latency_ms": 100,
        "sync_group": "upstairs"
    })
    
    # Simulate drift updates
    import random
    for i in range(10):
        # Simulate varying drift
        controller.update_device_drift("living_room", random.uniform(-20, 20))
        controller.update_device_drift("kitchen", random.uniform(-15, 15))
        controller.update_device_drift("bedroom", random.uniform(-10, 25))
        
        time.sleep(0.1)
    
    # Print final status
    status = controller.get_all_status()
    print(json.dumps(status, indent=2))

