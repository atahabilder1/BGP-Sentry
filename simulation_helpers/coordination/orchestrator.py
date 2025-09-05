#!/usr/bin/env python3
"""
Simulation Orchestrator for BGP-Sentry
======================================

This module orchestrates the distributed BGP-Sentry simulation by managing
the lifecycle of all RPKI nodes, coordinating timing, and monitoring the
overall simulation progress.

Author: Anik Tahabilder
Date: 2025-01-01
"""

import subprocess
import time
import threading
import signal
import sys
import os
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SimulationOrchestrator:
    """
    Orchestrates the distributed BGP-Sentry blockchain simulation.
    
    Manages:
    - Starting and stopping RPKI node processes
    - Coordinating simulation timing
    - Monitoring node health and simulation progress
    - Collecting and organizing results
    """
    
    def __init__(self):
        """Initialize the simulation orchestrator."""
        
        # RPKI node configuration - 9 nodes with odd AS numbers
        self.rpki_node_configs = {
            "as01": {"port": 8001, "process": None, "start_time": None},
            "as03": {"port": 8003, "process": None, "start_time": None},
            "as05": {"port": 8005, "process": None, "start_time": None},
            "as07": {"port": 8007, "process": None, "start_time": None},
            "as09": {"port": 8009, "process": None, "start_time": None},
            "as11": {"port": 8011, "process": None, "start_time": None},
            "as13": {"port": 8013, "process": None, "start_time": None},
            "as15": {"port": 8015, "process": None, "start_time": None},
            "as17": {"port": 8017, "process": None, "start_time": None}
        }
        
        # Simulation state tracking
        self.simulation_id = None
        self.simulation_status = "not_started"
        self.start_time = None
        self.end_time = None
        
        # Process management
        self.shutdown_requested = False
        self.monitoring_thread = None
        
        # Results tracking
        self.node_statistics = {}
        self.simulation_events = []
        
        logger.info("SimulationOrchestrator initialized")
    
    def validate_prerequisites(self):
        """
        Validate that all prerequisites are met for running the simulation.
        
        Checks:
        - Required directories exist
        - Network ports are available
        - Node executables are present
        - Shared data directories are accessible
        
        Raises:
            RuntimeError: If prerequisites are not met
        """
        logger.info("Validating simulation prerequisites...")
        
        # Check required directories
        required_dirs = [
            "nodes/rpki_nodes/",
            "simulation_helpers/shared_data/",
            "bgp_feed/",
            "results/"
        ]
        
        for directory in required_dirs:
            if not os.path.exists(directory):
                raise RuntimeError(f"Required directory not found: {directory}")
        
        # Check individual node directories
        for node_id in self.rpki_node_configs.keys():
            node_dir = f"nodes/rpki_nodes/{node_id}/"
            if not os.path.exists(node_dir):
                raise RuntimeError(f"Node directory not found: {node_dir}")
            
            # Check for required node files
            blockchain_node_script = f"{node_dir}blockchain_node/node.py"
            if not os.path.exists(blockchain_node_script):
                logger.warning(f"Node script not found: {blockchain_node_script}")
                # Create placeholder for now - actual implementation will be added later
                self._create_placeholder_node_script(blockchain_node_script)
        
        # Check port availability
        self._check_port_availability()
        
        # Create shared data directories if needed
        Path("simulation_helpers/shared_data").mkdir(parents=True, exist_ok=True)
        Path("results").mkdir(parents=True, exist_ok=True)
        
        logger.info("Prerequisites validation completed successfully")
    
    def _check_port_availability(self):
        """Check if all required network ports are available."""
        import socket
        
        for node_id, config in self.rpki_node_configs.items():
            port = config["port"]
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            
            try:
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    raise RuntimeError(f"Port {port} for node {node_id} is already in use")
            except socket.error:
                pass  # Port is available
            finally:
                sock.close()
        
        logger.info("All required ports (8001-8017 odd) are available")
    
    def _create_placeholder_node_script(self, script_path):
        """Create a placeholder node script for testing."""
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        
        placeholder_content = '''#!/usr/bin/env python3
"""
Placeholder RPKI Node Script
This is a temporary placeholder that will be replaced with actual implementation.
"""

import sys
import time
import argparse
import logging

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--experiment-mode", action="store_true")
    
    args = parser.parse_args()
    
    print(f"Placeholder node {args.node_id} starting on port {args.port}")
    
    # Simulate node running
    try:
        while True:
            time.sleep(5)
            print(f"Node {args.node_id} heartbeat")
    except KeyboardInterrupt:
        print(f"Node {args.node_id} shutting down")

if __name__ == "__main__":
    main()
'''
        
        with open(script_path, 'w') as f:
            f.write(placeholder_content)
        
        # Make executable
        os.chmod(script_path, 0o755)
        
        logger.info(f"Created placeholder node script: {script_path}")
    
    def start_all_nodes(self, experiment_config=None):
        """
        Start all RPKI node processes.
        
        Args:
            experiment_config: Optional configuration for the experiment
            
        Returns:
            bool: True if all nodes started successfully
        """
        logger.info("Starting all RPKI nodes...")
        
        self.start_time = time.time()
        self.simulation_status = "starting_nodes"
        
        successful_starts = 0
        
        for node_id, config in self.rpki_node_configs.items():
            try:
                success = self._start_single_node(node_id, config, experiment_config)
                if success:
                    successful_starts += 1
                else:
                    logger.error(f"Failed to start node {node_id}")
            
            except Exception as e:
                logger.error(f"Exception starting node {node_id}: {e}")
        
        if successful_starts == len(self.rpki_node_configs):
            logger.info("All RPKI nodes started successfully")
            self.simulation_status = "nodes_running"
            return True
        else:
            logger.error(f"Only {successful_starts}/{len(self.rpki_node_configs)} nodes started")
            self.simulation_status = "start_failed"
            return False
    
    def _start_single_node(self, node_id, config, experiment_config):
        """
        Start a single RPKI node process.
        
        Args:
            node_id: Node identifier (e.g., "as01")
            config: Node configuration dictionary
            experiment_config: Experiment configuration
            
        Returns:
            bool: True if node started successfully
        """
        logger.info(f"Starting node {node_id} on port {config['port']}")
        
        # Build command to start the node
        cmd = [
            sys.executable,  # Use same Python interpreter
            f"nodes/rpki_nodes/{node_id}/blockchain_node/node.py",
            "--node-id", node_id,
            "--port", str(config["port"]),
            "--experiment-mode"
        ]
        
        # Add experiment-specific arguments if provided
        if experiment_config:
            if "log_level" in experiment_config:
                cmd.extend(["--log-level", experiment_config["log_level"]])
        
        try:
            # Start the node process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            # Store process information
            config["process"] = process
            config["start_time"] = time.time()
            config["cmd"] = cmd
            
            # Give the process a moment to start
            time.sleep(1)
            
            # Check if process is still running
            if process.poll() is None:
                logger.info(f"Node {node_id} started successfully with PID {process.pid}")
                return True
            else:
                # Process already terminated
                stdout, stderr = process.communicate()
                logger.error(f"Node {node_id} terminated immediately:")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to start node {node_id}: {e}")
            return False
    
    def wait_for_node_convergence(self, timeout=60):
        """
        Wait for all nodes to establish connections and reach network convergence.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if convergence achieved, False if timeout
        """
        logger.info(f"Waiting for network convergence (timeout: {timeout}s)")
        
        start_time = time.time()
        convergence_checks = 0
        
        while time.time() - start_time < timeout:
            # Check node health
            active_nodes = self.get_active_nodes()
            
            if len(active_nodes) >= len(self.rpki_node_configs):
                convergence_checks += 1
                logger.info(f"Convergence check {convergence_checks}/3: {len(active_nodes)} nodes active")
                
                # Require 3 consecutive successful checks for stability
                if convergence_checks >= 3:
                    logger.info("Network convergence achieved")
                    self.simulation_status = "converged"
                    return True
            else:
                convergence_checks = 0  # Reset counter
                logger.info(f"Waiting for convergence: {len(active_nodes)}/{len(self.rpki_node_configs)} nodes active")
            
            time.sleep(5)  # Check every 5 seconds
        
        logger.warning("Network convergence timeout")
        return False
    
    def get_active_nodes(self):
        """
        Get list of currently active node IDs.
        
        Returns:
            list: Node IDs of active nodes
        """
        active_nodes = []
        
        for node_id, config in self.rpki_node_configs.items():
            process = config.get("process")
            
            if process and process.poll() is None:
                active_nodes.append(node_id)
        
        return active_nodes
    
    def start_monitoring(self):
        """Start background monitoring of node health and simulation progress."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Monitoring thread already running")
            return
        
        logger.info("Starting simulation monitoring")
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
    
    def _monitoring_loop(self):
        """Main monitoring loop that runs in background thread."""
        logger.info("Monitoring loop started")
        
        while not self.shutdown_requested:
            try:
                # Check node health
                active_nodes = self.get_active_nodes()
                
                # Log status periodically
                if len(active_nodes) < len(self.rpki_node_configs):
                    logger.warning(f"Node health issue: {len(active_nodes)}/{len(self.rpki_node_configs)} nodes active")
                    
                    # Identify failed nodes
                    for node_id, config in self.rpki_node_configs.items():
                        process = config.get("process")
                        if process and process.poll() is not None:
                            # Node has terminated
                            stdout, stderr = process.communicate()
                            logger.error(f"Node {node_id} terminated:")
                            if stdout:
                                logger.error(f"STDOUT: {stdout[-500:]}")  # Last 500 chars
                            if stderr:
                                logger.error(f"STDERR: {stderr[-500:]}")
                
                # Update statistics
                self._update_node_statistics()
                
                # Check for simulation completion conditions
                self._check_completion_conditions()
                
                # Sleep before next check
                time.sleep(10)  # Monitor every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
        
        logger.info("Monitoring loop ended")
    
    def _update_node_statistics(self):
        """Update statistics for all nodes."""
        current_time = time.time()
        
        for node_id, config in self.rpki_node_configs.items():
            if node_id not in self.node_statistics:
                self.node_statistics[node_id] = {
                    "start_time": config.get("start_time"),
                    "uptime": 0,
                    "restarts": 0,
                    "last_seen": current_time
                }
            
            process = config.get("process")
            if process and process.poll() is None:
                # Node is running
                start_time = config.get("start_time", current_time)
                self.node_statistics[node_id]["uptime"] = current_time - start_time
                self.node_statistics[node_id]["last_seen"] = current_time
    
    def _check_completion_conditions(self):
        """Check if simulation should be completed."""
        # This would check for experiment-specific completion conditions
        # For now, just log status
        active_nodes = self.get_active_nodes()
        
        if len(active_nodes) == 0:
            logger.warning("No active nodes - simulation may need to be stopped")
            self.simulation_status = "no_active_nodes"
    
    def stop_all_nodes(self, timeout=30):
        """
        Gracefully stop all RPKI node processes.
        
        Args:
            timeout: Maximum time to wait for graceful shutdown
        """
        logger.info("Stopping all RPKI nodes...")
        
        self.shutdown_requested = True
        self.simulation_status = "stopping"
        
        # First, try graceful shutdown
        for node_id, config in self.rpki_node_configs.items():
            process = config.get("process")
            
            if process and process.poll() is None:
                logger.info(f"Sending TERM signal to node {node_id}")
                try:
                    process.terminate()
                except Exception as e:
                    logger.error(f"Error terminating node {node_id}: {e}")
        
        # Wait for graceful shutdown
        shutdown_start = time.time()
        while time.time() - shutdown_start < timeout:
            active_nodes = self.get_active_nodes()
            
            if len(active_nodes) == 0:
                logger.info("All nodes shut down gracefully")
                break
            
            logger.info(f"Waiting for {len(active_nodes)} nodes to shut down...")
            time.sleep(2)
        
        # Force kill any remaining processes
        for node_id, config in self.rpki_node_configs.items():
            process = config.get("process")
            
            if process and process.poll() is None:
                logger.warning(f"Force killing node {node_id}")
                try:
                    process.kill()
                    process.wait(5)  # Wait up to 5 seconds
                except Exception as e:
                    logger.error(f"Error force killing node {node_id}: {e}")
        
        self.end_time = time.time()
        self.simulation_status = "stopped"
        logger.info("All nodes stopped")
    
    def get_simulation_summary(self):
        """
        Get summary of simulation status and statistics.
        
        Returns:
            dict: Simulation summary information
        """
        active_nodes = self.get_active_nodes()
        total_duration = None
        
        if self.start_time:
            end_time = self.end_time or time.time()
            total_duration = end_time - self.start_time
        
        return {
            "simulation_id": self.simulation_id,
            "status": self.simulation_status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": total_duration,
            "total_nodes": len(self.rpki_node_configs),
            "active_nodes": len(active_nodes),
            "active_node_list": active_nodes,
            "node_statistics": self.node_statistics,
            "simulation_events": self.simulation_events
        }
    
    def save_simulation_results(self, results_dir="results"):
        """
        Save simulation results and statistics to files.
        
        Args:
            results_dir: Directory to save results
        """
        logger.info(f"Saving simulation results to {results_dir}")
        
        Path(results_dir).mkdir(exist_ok=True)
        
        summary = self.get_simulation_summary()
        
        # Save summary as JSON
        import json
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = f"{results_dir}/simulation_summary_{timestamp}.json"
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Simulation summary saved to {summary_file}")

def create_signal_handler(orchestrator):
    """Create signal handler for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        orchestrator.stop_all_nodes()
        sys.exit(0)
    
    return signal_handler

# Example usage and testing
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Create orchestrator
    orchestrator = SimulationOrchestrator()
    
    # Set up signal handlers for graceful shutdown
    signal_handler = create_signal_handler(orchestrator)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Test the orchestrator
        orchestrator.validate_prerequisites()
        
        # Start nodes
        success = orchestrator.start_all_nodes()
        
        if success:
            # Wait for convergence
            converged = orchestrator.wait_for_node_convergence()
            
            if converged:
                # Start monitoring
                orchestrator.start_monitoring()
                
                # Run for a short test period
                print("Running test simulation for 30 seconds...")
                time.sleep(30)
            
        # Get summary
        summary = orchestrator.get_simulation_summary()
        print(f"Simulation summary: {summary}")
        
    except Exception as e:
        logger.error(f"Orchestrator test failed: {e}")
    
    finally:
        # Clean shutdown
        orchestrator.stop_all_nodes()
        orchestrator.save_simulation_results()