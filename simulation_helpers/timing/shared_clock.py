import time
import json
from pathlib import Path
from typing import List

class SharedClockManager:
    def __init__(self):
        self.start_time = None
        self.experiment_id = None
        self.registered_nodes: List[str] = []
        self.clock_file = "simulation_helpers/shared_data/simulation_clock.json"
    
    def initialize_simulation_clock(self, config):
        self.experiment_id = f"exp_{int(time.time())}"
        self._save_clock_state()
        return self.experiment_id
    
    def register_node(self, node_id: str):
        """Register a node with the shared clock"""
        if node_id not in self.registered_nodes:
            self.registered_nodes.append(node_id)
            self._save_clock_state()
    
    def start_simulation(self):
        self.start_time = time.time()
        self._save_clock_state()
    
    def get_simulation_time(self):
        if self.start_time:
            return time.time() - self.start_time
        return 0
    
    def stop_simulation(self):
        self._save_clock_state()
    
    def mark_bgp_data_loaded(self):
        self._save_clock_state()
    
    def wait_for_nodes(self, expected, timeout=60):
        start_time = time.time()
        while len(self.registered_nodes) < expected:
            if time.time() - start_time > timeout:
                return False
            time.sleep(1)
        return True
    
    def get_clock_status(self):
        return {
            "experiment_id": self.experiment_id, 
            "running": self.start_time is not None,
            "registered_nodes": self.registered_nodes,
            "simulation_time": self.get_simulation_time()
        }
    
    def _save_clock_state(self):
        """Save current clock state to shared file"""
        state = {
            "experiment_id": self.experiment_id,
            "registered_nodes": self.registered_nodes,
            "simulation_time": self.get_simulation_time(),
            "status": "running" if self.start_time else "initialized"
        }
        
        Path(self.clock_file).parent.mkdir(exist_ok=True)
        with open(self.clock_file, 'w') as f:
            json.dump(state, f, indent=2)
