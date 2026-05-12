import threading
import time
import dataclasses
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Deque
from collections import deque
import numpy as np

@dataclass
class RobotState:
    # Telemetry
    odom_x: float = 0.0
    odom_y: float = 0.0
    odom_z: float = 0.0
    linear_vel: float = 0.0
    angular_vel: float = 0.0
    
    # Visuals
    camera_image: Optional[np.ndarray] = None # RGB Image
    camera_jpeg: Optional[bytes] = None       # Latest compressed RGB frame
    map_data: Optional[np.ndarray] = None     # Occupancy Grid
    map_info: Optional[Dict] = None           # resolution, origin
    point_cloud_density: int = 0
    
    # System Stats
    cpu_usage: float = 0.0
    cpu_temp: float = 0.0
    ram_usage: float = 0.0
    disk_usage: float = 0.0
    battery_voltage: float = 0.0
    wifi_strength: float = 0.0 
    network_latency: float = 0.0
    
    # Navigation
    target_x: float = 0.0
    target_y: float = 0.0
    baseline_vel: float = 0.0 # From cmd_vel or wheel encoders
    
    # PID Tuning
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.1
    
    # History (for charts)
    history_time: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    history_cpu: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    history_vel: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    history_base_vel: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    history_latency: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    history_battery: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    history_temp: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    
    # Data Ops
    is_recording: bool = False
    bag_filename: str = ""
    
    # Actuators
    camera_height: int = 0
    camera_pan: int = 90
    bucket_pos: int = 0
    mining_rpm: float = 0.0
    teleop_throttle: int = 30
    bucket_chain_speed: int = 30
    conveyor_enabled: bool = False
    active_drive_cmd: str = ""
    active_pan_cmd: str = ""
    active_bucket_cmd: str = ""
    
    # Sensors
    ir_left: int = 0
    ir_right: int = 0
    encoder_left: int = 0
    encoder_right: int = 0
    
    # Hardware Status
    node_health: Dict[str, str] = field(default_factory=dict)
    
    # Logs
    recent_logs: List[str] = field(default_factory=list)

    last_update: float = 0.0

class StateStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._state = RobotState()

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self._state, k):
                    setattr(self._state, k, v)
            
            # Auto-update history on specific triggers if needed, 
            # or bridge can call append_history
            self._state.last_update = time.time()
            
    def append_history(self, timestamp, cpu, vel):
        with self._lock:
            self._state.history_time.append(timestamp)
            self._state.history_cpu.append(cpu)
            self._state.history_vel.append(vel)

    def get_snapshot(self) -> RobotState:
        with self._lock:
            # Return a shallow copy is usually enough for primitives
            return dataclasses.replace(self._state)

# Global singleton
store = StateStore()
