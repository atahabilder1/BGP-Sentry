#!/usr/bin/env python3
"""
BGP-Sentry Main Experiment Orchestrator
========================================

This is the main orchestrator for the BGP-Sentry distributed blockchain simulation.
It launches all RPKI nodes as independent processes, coordinates the BGP announcement
processing, and monitors the consensus mechanism.

Author: Anik Tahabilder
Date: 2025-01-01
"""

import subprocess
import time
import threading
import json
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main_experiment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('BGP-Sentry-Orchestrator')

class BGPSentryOrchestrator:
    """
    Main orchestrator class that manages the distributed BGP-Sentry simulation.
    
    This class handles:
    - Starting and stopping all RPKI blockchain nodes
    - Loading and distributing BGP announcements
    - Monitoring network health and consensus
    - Generating final results and reports
    """
    
    def __init__(self):
        """Initialize the orchestrator with node configurations and state tracking."""
        
        # RPKI node configuration - 9 nodes with odd AS numbers
        self.rpki_nodes = {
            "as01": {"port": 8001, "process": None},
            "as03": {"port": 8003, "process": None},
            "as05": {"port": 8005, "process": None},
            "as07": {"port": 8007, "process": None},
            "as09": {"port": 8009, "process": None},
            "as11": {"port": 8011, "process": None},
            "as13": {"port": 8013, "process": None},
            "as15": {"port": 8015, "process": None},
            "as17": {"port": 8017, "process": None}
        }
        
        # Experiment state tracking
        self.experiment_start_time = None
        self.experiment_end_time = None
        self.bgp_announcements = []
        self.results = {
            "total_announcements_processed": 0,
            "attacks_detected": 0,
            "consensus_decisions": 0,
            "blockchain_blocks_created": 0,
            "node_uptime": {},
            "performance_metrics": {}
        }
        
        # Paths for data and results
        self.bgp_data_path = "bgp_feed/mininet_logs/"
        self.results_path = "results/"
        
        # Create results directory if it doesn't exist
        Path(self.results_path).mkdir(exist_ok=True)
        
        logger.info("BGP-Sentry Orchestrator initialized")
    
    def validate_system_prerequisites(self):
        """
        Validate that all system prerequisites are met before starting the simulation.
        
        Checks:
        - Required directories exist
        - Network ports are available
        - BGP data sources are accessible
        - Shared services are importable
        """
        logger.info("Validating system prerequisites...")
        
        # Check required directories
        required_dirs = [
            "nodes/rpki_nodes/",
            "bgp_feed/",
            "results/",
            "tests/"
        ]
        
        for directory in required_dirs:
            if not os.path.exists(directory):
                raise FileNotFoundError(f"Required directory not found: {directory}")
        
        # Check RPKI node directories
        for node_id in self.rpki_nodes.keys():
            node_dir = f"nodes/rpki_nodes/{node_id}/"
            if not os.path.exists(node_dir):
                raise FileNotFoundError(f"RPKI node directory not found: {node_dir}")
            
            # Check for blockchain_node directory
            blockchain_dir = f"{node_dir}blockchain_node/"
            if not os.path.exists(blockchain_dir):
                os.makedirs(blockchain_dir, exist_ok=True)
                logger.info(f"Created blockchain directory for {node_id}")
        
        # Check port availability
        self.check_port_availability()
        
        # Check BGP data source
        if not os.path.exists(self.bgp_data_path):
            raise FileNotFoundError(f"BGP data source not found: {self.bgp_data_path}")
        
        logger.info("System prerequisites validation completed successfully")
    
    def check_port_availability(self):
        """Check if all required network ports are available for node communication."""
        import socket
        
        for node_id, config in self.rpki_nodes.items():
            port = config["port"]
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            
            try:
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    raise OSError(f"Port {port} for node {node_id} is already in use")
            except socket.error:
                pass  # Port is available
            finally:
                sock.close()
        
        logger.info("All required ports (8001-8017 odd) are available")
    
    def start_all_rpki_nodes(self):
        """
        Start all RPKI blockchain nodes as independent processes.
        
        Each node will:
        - Run on its assigned port
        - Maintain its own blockchain storage
        - Participate in peer-to-peer communication
        - Handle BGP announcement analysis and consensus
        """
        logger.info("Starting all RPKI blockchain nodes...")
        
        for node_id, config in self.rpki_nodes.items():
            logger.info(f"Starting node {node_id} on port {config['port']}")
            
            # Command to start the node process
            cmd = [
                sys.executable,  # Use same Python interpreter
                f"nodes/rpki_nodes/{node_id}/blockchain_node/node.py",
                "--node-id", node_id,
                "--port", str(config["port"]),
                "--experiment-mode"
            ]
            
            try:
                # Start node as subprocess
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                config["process"] = process
                config["start_time"] = time.time()
                
                logger.info(f"Node {node_id} started with PID {process.pid}")
                
                # Stagger node startup to avoid race conditions
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to start node {node_id}: {e}")
                raise
        
        logger.info("All RPKI nodes started successfully")
    
    def wait_for_network_convergence(self, timeout=60):
        """
        Wait for all nodes to establish peer connections and reach network convergence.
        
        Args:
            timeout: Maximum time to wait for convergence in seconds
        """
        logger.info("Waiting for network convergence...")
        
        start_time = time.time()
        convergence_achieved = False
        
        while time.time() - start_time < timeout and not convergence_achieved:
            # Check if all nodes are responding
            active_nodes = self.check_node_health()
            
            if len(active_nodes) >= len(self.rpki_nodes):
                logger.info("Network convergence achieved - all nodes active")
                convergence_achieved = True
            else:
                logger.info(f"Waiting for convergence: {len(active_nodes)}/{len(self.rpki_nodes)} nodes active")
                time.sleep(5)
        
        if not convergence_achieved:
            raise TimeoutError("Network failed to converge within timeout period")
    
    def check_node_health(self):
        """
        Check the health status of all RPKI nodes.
        
        Returns:
            List of active node IDs
        """
        active_nodes = []
        
        for node_id, config in self.rpki_nodes.items():
            process = config.get("process")
            
            if process and process.poll() is None:  # Process is still running
                active_nodes.append(node_id)
            elif process and process.poll() is not None:  # Process has terminated
                logger.warning(f"Node {node_id} has terminated unexpectedly")
        
        return active_nodes
    
    def load_bgp_announcements(self):
        """
        Load pre-recorded BGP announcements from the data source.
        
        Returns:
            List of BGP announcements to be processed
        """
        logger.info("Loading BGP announcements from data source...")
        
        announcements = []
        
        # Load from mininet logs or other BGP data sources
        try:
            # Example: Load from JSON file or parse log files
            # This would be customized based on your actual data format
            data_files = os.listdir(self.bgp_data_path)
            
            for file_name in data_files:
                if file_name.endswith('.log') or file_name.endswith('.json'):
                    file_path = os.path.join(self.bgp_data_path, file_name)
                    
                    # Parse BGP data (implementation depends on data format)
                    parsed_announcements = self.parse_bgp_data_file(file_path)
                    announcements.extend(parsed_announcements)
            
            self.bgp_announcements = announcements
            logger.info(f"Loaded {len(announcements)} BGP announcements for processing")
            
        except Exception as e:
            logger.error(f"Failed to load BGP announcements: {e}")
            raise
        
        return announcements
    
    def parse_bgp_data_file(self, file_path):
        """
        Parse individual BGP data file and extract announcements.
        
        Args:
            file_path: Path to the BGP data file
            
        Returns:
            List of parsed BGP announcements
        """
        announcements = []
        
        try:
            # This is a placeholder - implement based on your actual data format
            # Example for JSON format:
            if file_path.endswith('.json'):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        announcements.extend(data)
                    elif isinstance(data, dict) and 'announcements' in data:
                        announcements.extend(data['announcements'])
            
            # Example for log format:
            elif file_path.endswith('.log'):
                with open(file_path, 'r') as f:
                    for line in f:
                        # Parse log line to extract BGP announcement
                        # This would be customized based on log format
                        announcement = self.parse_bgp_log_line(line.strip())
                        if announcement:
                            announcements.append(announcement)
        
        except Exception as e:
            logger.warning(f"Failed to parse BGP data file {file_path}: {e}")
        
        return announcements
    
    def parse_bgp_log_line(self, log_line):
        """
        Parse a single log line to extract BGP announcement data.
        
        Args:
            log_line: Raw log line string
            
        Returns:
            Parsed BGP announcement dict or None
        """
        # Placeholder implementation - customize based on your log format
        # Example format: "TIMESTAMP AS_NUMBER PREFIX ACTION"
        
        try:
            parts = log_line.split()
            if len(parts) >= 4:
                return {
                    "timestamp": parts[0],
                    "as_number": int(parts[1]),
                    "prefix": parts[2],
                    "action": parts[3],
                    "raw_line": log_line
                }
        except (ValueError, IndexError):
            pass
        
        return None
    
    def distribute_bgp_announcements(self):
        """
        Distribute BGP announcements to the network for processing.
        
        Creates a shared queue that all nodes can read from to simulate
        synchronized processing of BGP announcements.
        """
        logger.info("Distributing BGP announcements to network...")
        
        # Create shared announcement queue
        queue_file = "shared_data/bgp_announcement_queue.json"
        os.makedirs(os.path.dirname(queue_file), exist_ok=True)
        
        # Prepare announcements with processing metadata
        announcement_queue = []
        for i, announcement in enumerate(self.bgp_announcements):
            queue_item = {
                "id": i,
                "announcement": announcement,
                "timestamp_queued": time.time(),
                "processed_by": [],
                "consensus_reached": False
            }
            announcement_queue.append(queue_item)
        
        # Write to shared queue file
        with open(queue_file, 'w') as f:
            json.dump(announcement_queue, f, indent=2)
        
        logger.info(f"Created announcement queue with {len(announcement_queue)} items")
    
    def monitor_simulation_progress(self):
        """
        Monitor the progress of the BGP announcement processing simulation.
        
        Tracks:
        - Number of announcements processed
        - Consensus decisions made
        - Node health and performance
        - Blockchain growth across nodes
        """
        logger.info("Starting simulation monitoring...")
        
        monitoring_active = True
        last_status_time = time.time()
        
        while monitoring_active:
            try:
                # Check node health
                active_nodes = self.check_node_health()
                
                # Update node uptime tracking
                current_time = time.time()
                for node_id in active_nodes:
                    if node_id not in self.results["node_uptime"]:
                        self.results["node_uptime"][node_id] = 0
                    self.results["node_uptime"][node_id] += 5  # 5-second monitoring interval
                
                # Log periodic status
                if current_time - last_status_time >= 30:  # Every 30 seconds
                    logger.info(f"Status: {len(active_nodes)}/{len(self.rpki_nodes)} nodes active")
                    self.log_blockchain_status()
                    last_status_time = current_time
                
                # Check if simulation should continue
                if len(active_nodes) < len(self.rpki_nodes) // 2:
                    logger.warning("Less than half of nodes are active - simulation may be compromised")
                
                # Sleep for monitoring interval
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("Simulation monitoring interrupted by user")
                monitoring_active = False
            except Exception as e:
                logger.error(f"Error during simulation monitoring: {e}")
                time.sleep(5)
    
    def log_blockchain_status(self):
        """Log the current status of blockchain across all nodes."""
        try:
            blockchain_lengths = {}
            
            for node_id in self.rpki_nodes.keys():
                blockchain_file = f"nodes/rpki_nodes/{node_id}/blockchain_node/local_blockchain/blockchain.json"
                
                if os.path.exists(blockchain_file):
                    with open(blockchain_file, 'r') as f:
                        blockchain_data = json.load(f)
                        if isinstance(blockchain_data, list):
                            blockchain_lengths[node_id] = len(blockchain_data)
                        elif isinstance(blockchain_data, dict) and 'blocks' in blockchain_data:
                            blockchain_lengths[node_id] = len(blockchain_data['blocks'])
                        else:
                            blockchain_lengths[node_id] = 0
                else:
                    blockchain_lengths[node_id] = 0
            
            logger.info(f"Blockchain lengths: {blockchain_lengths}")
            
        except Exception as e:
            logger.warning(f"Failed to log blockchain status: {e}")
    
    def shutdown_all_nodes(self):
        """
        Gracefully shutdown all RPKI node processes.
        
        Sends termination signals and waits for clean shutdown.
        """
        logger.info("Shutting down all RPKI nodes...")
        
        for node_id, config in self.rpki_nodes.items():
            process = config.get("process")
            
            if process and process.poll() is None:
                logger.info(f"Shutting down node {node_id}")
                
                try:
                    # Send SIGTERM for graceful shutdown
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    process.wait(timeout=10)
                    
                    logger.info(f"Node {node_id} shut down gracefully")
                    
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    logger.warning(f"Force killing node {node_id}")
                    process.kill()
                    process.wait()
                except Exception as e:
                    logger.error(f"Error shutting down node {node_id}: {e}")
        
        logger.info("All nodes shutdown completed")
    
    def generate_final_results(self):
        """
        Generate final simulation results and analysis.
        
        Creates comprehensive reports of:
        - Consensus performance
        - Attack detection statistics
        - Network performance metrics
        - Blockchain analysis
        """
        logger.info("Generating final simulation results...")
        
        self.experiment_end_time = time.time()
        experiment_duration = self.experiment_end_time - self.experiment_start_time
        
        # Compile final results
        final_results = {
            "experiment_metadata": {
                "start_time": datetime.fromtimestamp(self.experiment_start_time).isoformat(),
                "end_time": datetime.fromtimestamp(self.experiment_end_time).isoformat(),
                "duration_seconds": experiment_duration,
                "total_rpki_nodes": len(self.rpki_nodes),
                "total_bgp_announcements": len(self.bgp_announcements)
            },
            "node_performance": self.results["node_uptime"],
            "blockchain_analysis": self.analyze_blockchain_results(),
            "consensus_metrics": self.analyze_consensus_performance(),
            "network_metrics": self.analyze_network_performance()
        }
        
        # Save results to files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        results_file = f"{self.results_path}experiment_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2)
        
        logger.info(f"Final results saved to {results_file}")
        
        # Print summary to console
        self.print_experiment_summary(final_results)
    
    def analyze_blockchain_results(self):
        """Analyze blockchain growth and consistency across nodes."""
        blockchain_analysis = {}
        
        try:
            for node_id in self.rpki_nodes.keys():
                blockchain_file = f"nodes/rpki_nodes/{node_id}/blockchain_node/local_blockchain/blockchain.json"
                
                if os.path.exists(blockchain_file):
                    with open(blockchain_file, 'r') as f:
                        blockchain_data = json.load(f)
                        
                        blockchain_analysis[node_id] = {
                            "total_blocks": len(blockchain_data) if isinstance(blockchain_data, list) else 0,
                            "file_size_bytes": os.path.getsize(blockchain_file),
                            "last_modified": os.path.getmtime(blockchain_file)
                        }
        except Exception as e:
            logger.error(f"Error analyzing blockchain results: {e}")
        
        return blockchain_analysis
    
    def analyze_consensus_performance(self):
        """Analyze consensus mechanism performance."""
        # Placeholder - implement based on consensus logging
        return {
            "total_consensus_rounds": 0,
            "average_consensus_time": 0,
            "consensus_success_rate": 0
        }
    
    def analyze_network_performance(self):
        """Analyze network communication performance."""
        # Placeholder - implement based on network logging
        return {
            "average_message_latency": 0,
            "total_messages_exchanged": 0,
            "network_partition_events": 0
        }
    
    def print_experiment_summary(self, results):
        """Print a summary of experiment results to console."""
        print("\n" + "="*80)
        print("BGP-SENTRY SIMULATION COMPLETED")
        print("="*80)
        
        metadata = results["experiment_metadata"]
        print(f"Duration: {metadata['duration_seconds']:.1f} seconds")
        print(f"Nodes: {metadata['total_rpki_nodes']}")
        print(f"BGP Announcements: {metadata['total_bgp_announcements']}")
        
        print("\nNode Uptime:")
        for node_id, uptime in results["node_performance"].items():
            uptime_percent = (uptime / metadata['duration_seconds']) * 100
            print(f"  {node_id}: {uptime_percent:.1f}%")
        
        print("\nBlockchain Status:")
        for node_id, analysis in results["blockchain_analysis"].items():
            print(f"  {node_id}: {analysis['total_blocks']} blocks")
        
        print("="*80)

def main():
    """
    Main function to run the BGP-Sentry distributed simulation.
    
    Orchestrates the complete simulation workflow:
    1. System validation
    2. Node startup
    3. Network convergence
    4. BGP announcement processing
    5. Monitoring and results
    """
    
    # Create orchestrator instance
    orchestrator = BGPSentryOrchestrator()
    
    try:
        print("Starting BGP-Sentry Distributed Blockchain Simulation")
        print("=" * 60)
        
        # Step 1: Validate system prerequisites
        orchestrator.validate_system_prerequisites()
        
        # Step 2: Start all RPKI blockchain nodes
        orchestrator.start_all_rpki_nodes()
        
        # Step 3: Wait for network convergence
        orchestrator.wait_for_network_convergence()
        
        # Step 4: Load and distribute BGP announcements
        orchestrator.load_bgp_announcements()
        orchestrator.distribute_bgp_announcements()
        
        # Step 5: Start experiment timing
        orchestrator.experiment_start_time = time.time()
        
        # Step 6: Monitor simulation progress
        # This will run until interrupted or all processing completes
        orchestrator.monitor_simulation_progress()
        
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise
    finally:
        # Always attempt cleanup
        orchestrator.shutdown_all_nodes()
        orchestrator.generate_final_results()

if __name__ == "__main__":
    main()