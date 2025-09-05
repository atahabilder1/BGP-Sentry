#!/usr/bin/env python3
"""
Shared Clock Manager for BGP-Sentry Simulation
==============================================

This module manages the shared timing reference that all RPKI nodes use to stay
synchronized during the distributed blockchain simulation. It handles creation,
updates, and reading of the shared simulation clock.

Author: Anik Tahabilder
Date: 2025-01-01
"""

import json
import time
import os
import threading
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class SharedClockManager:
    """
    Manages the shared simulation clock that coordinates timing across all nodes.
    
    The shared clock provides a centralized timing reference that all RPKI nodes
    can read to determine the current simulation time and process BGP announcements
    synchronously.
    """
    
    def __init__(self, clock_file_path="simulation_helpers/shared_data/simulation_clock.json"):
        """
        Initialize the shared clock manager.
        
        Args:
            clock_file_path: Path to the shared clock file
        """
        self.clock_file_path = clock_file_path
        self.lock = threading.Lock()
        
        # Ensure the directory exists
        Path(self.clock_file_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"SharedClockManager initialized with clock file: {self.clock_file_path}")
    
    def initialize_simulation_clock(self, experiment_config):
        """
        Initialize the simulation clock for a new experiment.
        
        Args:
            experiment_config: Dictionary containing simulation parameters
                - time_scale: Speed multiplier for simulation (1.0 = real-time)
                - max_duration: Maximum simulation duration in seconds
                - start_delay: Delay before starting simulation
        """
        logger.info("Initializing simulation clock for new experiment")
        
        current_real_time = time.time()
        
        clock_data = {
            "experiment_id": experiment_config.get("experiment_id", f"exp_{int(current_real_time)}"),
            "experiment_start_time": current_real_time,
            "simulation_start_time": 0.0,
            "current_simulation_time": 0.0,
            "time_scale_factor": experiment_config.get("time_scale", 1.0),
            "max_simulation_duration": experiment_config.get("max_duration", 3600),
            "status": "initialized",
            "last_updated": current_real_time,
            "nodes_registered": [],
            "bgp_data_loaded": False,
            "metadata": {
                "created_by": "SharedClockManager",
                "creation_timestamp": datetime.fromtimestamp(current_real_time).isoformat(),
                "version": "1.0"
            }
        }
        
        with self.lock:
            self._write_clock_file(clock_data)
        
        logger.info(f"Simulation clock initialized - ID: {clock_data['experiment_id']}, Scale: {clock_data['time_scale_factor']}x")
        return clock_data["experiment_id"]
    
    def start_simulation(self):
        """
        Start the simulation timer.
        
        Transitions the clock from 'initialized' to 'running' status and begins
        tracking simulation time progression.
        """
        logger.info("Starting simulation clock")
        
        with self.lock:
            clock_data = self._read_clock_file()
            
            if clock_data["status"] != "initialized":
                raise ValueError(f"Cannot start simulation in status: {clock_data['status']}")
            
            current_time = time.time()
            clock_data["simulation_start_time"] = current_time
            clock_data["status"] = "running"
            clock_data["last_updated"] = current_time
            
            self._write_clock_file(clock_data)
        
        logger.info("Simulation clock started - status: running")
    
    def pause_simulation(self):
        """
        Pause the simulation timer.
        
        Transitions to 'paused' status while preserving current simulation time.
        """
        logger.info("Pausing simulation clock")
        
        with self.lock:
            clock_data = self._read_clock_file()
            
            if clock_data["status"] != "running":
                raise ValueError(f"Cannot pause simulation in status: {clock_data['status']}")
            
            # Update current simulation time before pausing
            current_time = time.time()
            if clock_data["simulation_start_time"] > 0:
                elapsed_real_time = current_time - clock_data["simulation_start_time"]
                clock_data["current_simulation_time"] = elapsed_real_time * clock_data["time_scale_factor"]
            
            clock_data["status"] = "paused"
            clock_data["last_updated"] = current_time
            
            self._write_clock_file(clock_data)
        
        logger.info("Simulation clock paused")
    
    def stop_simulation(self):
        """
        Stop the simulation and finalize timing data.
        
        Transitions to 'completed' status and records final timing statistics.
        """
        logger.info("Stopping simulation clock")
        
        with self.lock:
            clock_data = self._read_clock_file()
            
            current_time = time.time()
            
            # Calculate final simulation time
            if clock_data["simulation_start_time"] > 0:
                elapsed_real_time = current_time - clock_data["simulation_start_time"]
                final_sim_time = elapsed_real_time * clock_data["time_scale_factor"]
            else:
                final_sim_time = clock_data["current_simulation_time"]
            
            clock_data["current_simulation_time"] = final_sim_time
            clock_data["status"] = "completed"
            clock_data["last_updated"] = current_time
            clock_data["experiment_end_time"] = current_time
            
            # Add final statistics
            clock_data["final_statistics"] = {
                "total_real_duration": current_time - clock_data["experiment_start_time"],
                "total_simulation_duration": final_sim_time,
                "average_time_scale": final_sim_time / (current_time - clock_data["experiment_start_time"]) if current_time > clock_data["experiment_start_time"] else 0,
                "completion_timestamp": datetime.fromtimestamp(current_time).isoformat()
            }
            
            self._write_clock_file(clock_data)
        
        logger.info(f"Simulation clock stopped - Final sim time: {final_sim_time:.2f}s")
    
    def get_simulation_time(self):
        """
        Get the current simulation time.
        
        Returns:
            float: Current simulation time in seconds
        """
        clock_data = self._read_clock_file()
        
        if clock_data["status"] == "running":
            # Calculate current simulation time based on elapsed real time
            current_real_time = time.time()
            elapsed_real_time = current_real_time - clock_data["simulation_start_time"]
            simulation_time = elapsed_real_time * clock_data["time_scale_factor"]
            return simulation_time
        
        elif clock_data["status"] in ["paused", "completed"]:
            # Return stored simulation time
            return clock_data["current_simulation_time"]
        
        else:
            # Not started yet
            return 0.0
    
    def get_clock_status(self):
        """
        Get the current status of the simulation clock.
        
        Returns:
            dict: Complete clock status information
        """
        clock_data = self._read_clock_file()
        
        # Add calculated current simulation time
        clock_data["calculated_simulation_time"] = self.get_simulation_time()
        
        return clock_data
    
    def register_node(self, node_id):
        """
        Register a node with the simulation clock.
        
        Args:
            node_id: Unique identifier for the RPKI node
        """
        logger.info(f"Registering node {node_id} with simulation clock")
        
        with self.lock:
            clock_data = self._read_clock_file()
            
            if node_id not in clock_data["nodes_registered"]:
                clock_data["nodes_registered"].append(node_id)
                clock_data["last_updated"] = time.time()
                
                self._write_clock_file(clock_data)
        
        logger.info(f"Node {node_id} registered - Total nodes: {len(clock_data['nodes_registered'])}")
    
    def mark_bgp_data_loaded(self):
        """
        Mark that BGP data has been loaded and is ready for processing.
        """
        logger.info("Marking BGP data as loaded")
        
        with self.lock:
            clock_data = self._read_clock_file()
            clock_data["bgp_data_loaded"] = True
            clock_data["bgp_data_load_time"] = time.time()
            clock_data["last_updated"] = time.time()
            
            self._write_clock_file(clock_data)
    
    def wait_for_nodes(self, expected_node_count, timeout=60):
        """
        Wait for a specified number of nodes to register.
        
        Args:
            expected_node_count: Number of nodes to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if enough nodes registered, False if timeout
        """
        logger.info(f"Waiting for {expected_node_count} nodes to register (timeout: {timeout}s)")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            clock_data = self._read_clock_file()
            
            if len(clock_data["nodes_registered"]) >= expected_node_count:
                logger.info(f"All {expected_node_count} nodes registered successfully")
                return True
            
            time.sleep(1)  # Check every second
        
        logger.warning(f"Timeout waiting for nodes - only {len(clock_data['nodes_registered'])}/{expected_node_count} registered")
        return False
    
    def _read_clock_file(self):
        """
        Read the shared clock file with error handling.
        
        Returns:
            dict: Clock data
        """
        try:
            if not os.path.exists(self.clock_file_path):
                raise FileNotFoundError(f"Clock file not found: {self.clock_file_path}")
            
            with open(self.clock_file_path, 'r') as f:
                return json.load(f)
                
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error reading clock file: {e}")
            # Return default clock data if file is corrupted
            return {
                "experiment_start_time": time.time(),
                "simulation_start_time": 0.0,
                "current_simulation_time": 0.0,
                "time_scale_factor": 1.0,
                "status": "error",
                "last_updated": time.time(),
                "nodes_registered": [],
                "bgp_data_loaded": False
            }
    
    def _write_clock_file(self, clock_data):
        """
        Write clock data to the shared file with atomic operation.
        
        Args:
            clock_data: Dictionary containing clock information
        """
        try:
            # Write to temporary file first for atomic operation
            temp_file = f"{self.clock_file_path}.tmp"
            
            with open(temp_file, 'w') as f:
                json.dump(clock_data, f, indent=2)
            
            # Atomic rename
            os.rename(temp_file, self.clock_file_path)
            
        except Exception as e:
            logger.error(f"Error writing clock file: {e}")
            # Clean up temp file if it exists
            if os.path.exists(f"{self.clock_file_path}.tmp"):
                os.remove(f"{self.clock_file_path}.tmp")
            raise

def create_default_experiment_config():
    """
    Create a default experiment configuration for testing.
    
    Returns:
        dict: Default experiment configuration
    """
    return {
        "experiment_id": f"bgp_sentry_exp_{int(time.time())}",
        "time_scale": 1.0,          # Real-time simulation
        "max_duration": 3600,       # 1 hour maximum
        "start_delay": 5,           # 5 second delay before starting
        "expected_nodes": 9,        # 9 RPKI nodes
        "bgp_announcement_interval": 5.0,  # Process announcements every 5 seconds
        "description": "BGP-Sentry distributed blockchain simulation"
    }

# Example usage and testing
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Create shared clock manager
    clock_manager = SharedClockManager()
    
    # Test initialization
    config = create_default_experiment_config()
    experiment_id = clock_manager.initialize_simulation_clock(config)
    
    print(f"Initialized experiment: {experiment_id}")
    print(f"Current status: {clock_manager.get_clock_status()}")
    
    # Test node registration
    for i in range(1, 10, 2):  # as01, as03, as05, etc.
        clock_manager.register_node(f"as{i:02d}")
    
    # Test starting simulation
    clock_manager.start_simulation()
    print(f"Simulation started - time: {clock_manager.get_simulation_time():.2f}s")
    
    # Simulate some time passing
    time.sleep(2)
    print(f"After 2 seconds - simulation time: {clock_manager.get_simulation_time():.2f}s")
    
    # Test stopping
    clock_manager.stop_simulation()
    final_status = clock_manager.get_clock_status()
    print(f"Final status: {final_status['status']}")
    print(f"Final simulation time: {final_status['current_simulation_time']:.2f}s")