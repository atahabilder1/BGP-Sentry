#!/usr/bin/env python3
"""
BGP-Sentry Main Experiment Orchestrator (Updated)
==================================================

This is the main orchestrator for the BGP-Sentry distributed blockchain simulation.
It uses the simulation helpers to manage timing, coordinate nodes, and monitor
the distributed system.

Author: Anik Tahabilder
Date: 2025-01-01
"""

import sys
import time
import signal
import json
import logging
from pathlib import Path
from datetime import datetime

# Import simulation helpers
from simulation_helpers import (
    SharedClockManager,
    SimulationOrchestrator, 
    NodeHealthMonitor,
    HealthDashboard,
    create_default_experiment_config
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main_experiment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('BGP-Sentry-Main')

class BGPSentryExperiment:
    """
    Main experiment controller that orchestrates the entire BGP-Sentry simulation.
    
    This class coordinates:
    - Shared timing across all nodes
    - Node lifecycle management
    - Health monitoring and alerting
    - Experiment results collection
    """
    
    def __init__(self, config_file="simulation_helpers/shared_data/experiment_config.json"):
        """
        Initialize the BGP-Sentry experiment.
        
        Args:
            config_file: Path to experiment configuration file
        """
        self.config_file = config_file
        self.config = self._load_experiment_config()
        
        # Initialize core components
        self.clock_manager = SharedClockManager()
        self.orchestrator = SimulationOrchestrator()
        self.health_monitor = None
        self.dashboard = None
        
        # Experiment state
        self.experiment_id = None
        self.experiment_start_time = None
        self.experiment_status = "initialized"
        
        # Graceful shutdown handling
        self.shutdown_requested = False
        self._setup_signal_handlers()
        
        logger.info("BGP-Sentry Experiment initialized")
    
    def _load_experiment_config(self):
        """
        Load experiment configuration from file.
        
        Returns:
            dict: Experiment configuration
        """
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded configuration from {self.config_file}")
                return config
            else:
                logger.warning(f"Config file {self.config_file} not found, using defaults")
                return self._create_default_config()
                
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")
            return self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration if file doesn't exist."""
        default_config = create_default_experiment_config()
        
        # Add additional experiment-specific settings
        experiment_config = {
            "experiment_metadata": {
                "name": "BGP-Sentry Distributed Simulation",
                "description": "Distributed blockchain simulation for BGP security analysis"
            },
            "simulation_parameters": {
                "time_scale": default_config["time_scale"],
                "max_duration": default_config["max_duration"],
                "expected_nodes": 9,
                "processing_interval": 5.0
            },
            "monitoring": {
                "health_check_interval": 10,
                "enable_dashboard": True,
                "alert_on_failures": True
            }
        }
        
        return experiment_config
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_requested = True
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def validate_prerequisites(self):
        """
        Validate that all prerequisites are met for running the experiment.
        
        Returns:
            bool: True if prerequisites are met
        """
        logger.info("Validating experiment prerequisites...")
        
        try:
            # Validate simulation helpers
            self._validate_simulation_helpers()
            
            # Validate orchestrator prerequisites
            self.orchestrator.validate_prerequisites()
            
            # Validate BGP data sources
            self._validate_bgp_data_sources()
            
            # Validate output directories
            self._validate_output_directories()
            
            logger.info("All prerequisites validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Prerequisites validation failed: {e}")
            return False
    
    def _validate_simulation_helpers(self):
        """Validate simulation helper components."""
        # Test shared clock initialization
        test_config = create_default_experiment_config()
        test_id = self.clock_manager.initialize_simulation_clock(test_config)
        logger.info(f"Shared clock test successful: {test_id}")
        
        # Test orchestrator initialization
        if not hasattr(self.orchestrator, 'rpki_node_configs'):
            raise RuntimeError("Orchestrator not properly initialized")
        
        logger.info("Simulation helpers validation passed")
    
    def _validate_bgp_data_sources(self):
        """Validate BGP data sources are available."""
        bgp_data_path = "bgp_feed/mininet_logs/"
        
        if not Path(bgp_data_path).exists():
            raise FileNotFoundError(f"BGP data source not found: {bgp_data_path}")
        
        # Check for data files
        data_files = list(Path(bgp_data_path).glob("*.log")) + list(Path(bgp_data_path).glob("*.json"))
        
        if not data_files:
            logger.warning(f"No BGP data files found in {bgp_data_path}")
        else:
            logger.info(f"Found {len(data_files)} BGP data files")
    
    def _validate_output_directories(self):
        """Validate and create output directories."""
        output_dirs = ["results", "simulation_helpers/shared_data"]
        
        for directory in output_dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory ready: {directory}")
    
    def initialize_experiment(self):
        """
        Initialize the experiment with shared timing and node coordination.
        
        Returns:
            bool: True if initialization successful
        """
        logger.info("Initializing BGP-Sentry experiment...")
        
        try:
            # Initialize shared clock
            sim_config = self.config.get("simulation_parameters", create_default_experiment_config())
            self.experiment_id = self.clock_manager.initialize_simulation_clock(sim_config)
            
            # Initialize health monitoring
            node_configs = self.orchestrator.rpki_node_configs
            monitoring_interval = self.config.get("monitoring", {}).get("health_check_interval", 10)
            
            self.health_monitor = NodeHealthMonitor(node_configs, monitoring_interval)
            self.dashboard = HealthDashboard(self.health_monitor)
            
            # Mark experiment as initialized
            self.experiment_status = "initialized"
            self.experiment_start_time = time.time()
            
            logger.info(f"Experiment initialized successfully - ID: {self.experiment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Experiment initialization failed: {e}")
            self.experiment_status = "initialization_failed"
            return False
    
    def start_nodes(self):
        """
        Start all RPKI nodes and wait for network convergence.
        
        Returns:
            bool: True if all nodes started successfully
        """
        logger.info("Starting RPKI node network...")
        
        try:
            # Ensure health monitor is ready
            if not self.health_monitor:
                node_configs = self.orchestrator.rpki_node_configs
                monitoring_interval = self.config.get("monitoring", {}).get("health_check_interval", 10)
                self.health_monitor = NodeHealthMonitor(node_configs, monitoring_interval)
            if not self.dashboard:
                self.dashboard = HealthDashboard(self.health_monitor)

            # Start health monitoring first
            self.health_monitor.start_monitoring()
            
            # Start all nodes
            experiment_config = self.config.get("simulation_parameters", {})
            success = self.orchestrator.start_all_nodes(experiment_config)
            
            if not success:
                logger.error("Failed to start all nodes")
                return False
            
            # Wait for network convergence
            convergence_timeout = experiment_config.get("convergence_timeout", 60)
            converged = self.orchestrator.wait_for_node_convergence(convergence_timeout)
            
            if not converged:
                logger.error("Network convergence timeout")
                return False
            
            # Wait for nodes to register with shared clock
            expected_nodes = experiment_config.get("expected_nodes", 9)
            nodes_ready = self.clock_manager.wait_for_nodes(expected_nodes, timeout=60)
            
            if not nodes_ready:
                logger.warning("Not all nodes registered with shared clock")
            
            logger.info("All nodes started and network converged")
            self.experiment_status = "nodes_ready"
            return True
            
        except Exception as e:
            logger.error(f"Node startup failed: {e}")
            self.experiment_status = "startup_failed"
            return False
    
    def run_simulation(self):
        """
        Run the main simulation with BGP announcement processing.
        
        Returns:
            bool: True if simulation completed successfully
        """
        logger.info("Starting BGP simulation...")
        
        try:
            # Mark BGP data as loaded (simulation will load it)
            self.clock_manager.mark_bgp_data_loaded()
            
            # Start the simulation clock
            self.clock_manager.start_simulation()
            self.experiment_status = "running"
            
            # Start orchestrator monitoring
            self.orchestrator.start_monitoring()
            
            # Get simulation duration
            max_duration = self.config.get("simulation_parameters", {}).get("max_duration", 3600)
            processing_interval = self.config.get("simulation_parameters", {}).get("processing_interval", 30)
            
            logger.info(f"Simulation running - Duration: {max_duration}s, Monitoring interval: {processing_interval}s")
            
            # Main simulation loop
            simulation_start = time.time()
            last_status_time = simulation_start
            
            while not self.shutdown_requested:
                current_time = time.time()
                elapsed_time = current_time - simulation_start
                
                # Check if simulation should end
                if elapsed_time >= max_duration:
                    logger.info("Simulation duration reached, stopping...")
                    break
                
                # Periodic status updates
                if current_time - last_status_time >= processing_interval:
                    self._print_simulation_status()
                    last_status_time = current_time
                
                # Check node health
                active_nodes = self.orchestrator.get_active_nodes()
                if len(active_nodes) < len(self.orchestrator.rpki_node_configs) // 2:
                    logger.warning("Less than half of nodes are active - stopping simulation")
                    break
                
                # Sleep before next check
                time.sleep(5)
            
            # Stop simulation clock
            self.clock_manager.stop_simulation()
            self.experiment_status = "completed"
            
            logger.info("Simulation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            self.experiment_status = "simulation_failed"
            return False
    
    def _print_simulation_status(self):
        """Print current simulation status."""
        try:
            # Get simulation time
            sim_time = self.clock_manager.get_simulation_time()
            
            # Get node status
            active_nodes = self.orchestrator.get_active_nodes()
            total_nodes = len(self.orchestrator.rpki_node_configs)
            
            if not self.health_monitor:
                logger.info(
                    "SIMULATION STATUS - Time: %.1fs | Nodes: %d/%d | Health monitor unavailable",
                    sim_time,
                    len(active_nodes),
                    total_nodes,
                )
                return

            # Get health summary
            health_summary = self.health_monitor.get_node_health_summary()
            
            # Print status
            logger.info(f"SIMULATION STATUS - Time: {sim_time:.1f}s | "
                       f"Nodes: {len(active_nodes)}/{total_nodes} | "
                       f"Responsive: {health_summary['responsive_nodes']} | "
                       f"Issues: {health_summary['nodes_with_issues']}")
            
            # Print dashboard if enabled
            if (
                self.dashboard
                and self.config.get("monitoring", {}).get("enable_dashboard", False)
            ):
                print("\n" + "="*80)
                self.dashboard.print_status_summary()
                self.dashboard.print_recent_alerts(max_alerts=5)
                print("="*80)
        
        except Exception as e:
            logger.warning(f"Error printing status: {e}")
    
    def shutdown(self):
        """Gracefully shutdown the experiment."""
        logger.info("Shutting down BGP-Sentry experiment...")
        
        try:
            # Stop simulation clock
            if self.experiment_status in ["running", "nodes_ready"]:
                self.clock_manager.stop_simulation()
            
            # Stop all nodes
            self.orchestrator.stop_all_nodes()
            
            # Stop health monitoring
            if self.health_monitor:
                self.health_monitor.stop_monitoring()
            
            # Generate final results
            self._generate_final_results()
            
            self.experiment_status = "shutdown_complete"
            logger.info("Experiment shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def _generate_final_results(self):
        """Generate and save final experiment results."""
        logger.info("Generating final experiment results...")
        
        try:
            # Create results directory
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)
            
            # Get final clock status
            clock_status = self.clock_manager.get_clock_status()
            
            # Get orchestrator summary
            simulation_summary = self.orchestrator.get_simulation_summary()
            
            # Get health report
            if self.health_monitor:
                health_summary = self.health_monitor.get_node_health_summary()
                performance_metrics = self.health_monitor.get_performance_metrics()
                blockchain_status = self.health_monitor.get_blockchain_sync_status()
            else:
                health_summary = {
                    "total_nodes": len(self.orchestrator.rpki_node_configs),
                    "running_nodes": 0,
                    "responsive_nodes": 0,
                    "nodes_with_issues": len(self.orchestrator.rpki_node_configs),
                }
                performance_metrics = {}
                blockchain_status = {
                    "nodes_with_blockchain": 0,
                    "average_block_count": 0.0,
                    "block_counts": [],
                }
            
            # Compile final results
            final_results = {
                "experiment_metadata": {
                    "experiment_id": self.experiment_id,
                    "config_used": self.config,
                    "start_time": self.experiment_start_time,
                    "end_time": time.time(),
                    "status": self.experiment_status
                },
                "timing_results": clock_status,
                "simulation_summary": simulation_summary,
                "health_summary": health_summary,
                "performance_metrics": performance_metrics,
                "blockchain_status": blockchain_status
            }
            
            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = results_dir / f"bgp_sentry_results_{timestamp}.json"
            
            with open(results_file, 'w') as f:
                json.dump(final_results, f, indent=2, default=str)
            
            # Save health report
            health_report_file = results_dir / f"health_report_{timestamp}.json"
            if self.health_monitor:
                self.health_monitor.export_health_report(str(health_report_file))
            
            # Save orchestrator results
            self.orchestrator.save_simulation_results(str(results_dir))
            
            logger.info(f"Results saved to {results_file}")
            
            # Print summary
            self._print_final_summary(final_results)
            
        except Exception as e:
            logger.error(f"Error generating results: {e}")
    
    def _print_final_summary(self, results):
        """Print final experiment summary."""
        print("\n" + "="*80)
        print("BGP-SENTRY EXPERIMENT COMPLETED")
        print("="*80)
        
        metadata = results["experiment_metadata"]
        duration = metadata["end_time"] - metadata["start_time"]
        
        print(f"Experiment ID: {metadata['experiment_id']}")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Status: {metadata['status']}")
        
        # Node statistics
        sim_summary = results["simulation_summary"]
        print(f"\nNode Performance:")
        print(f"  Total Nodes: {sim_summary['total_nodes']}")
        print(f"  Active Nodes at End: {sim_summary['active_nodes']}")
        
        # Health statistics
        health_summary = results["health_summary"]
        print(f"\nHealth Summary:")
        print(f"  Running Nodes: {health_summary['running_nodes']}")
        print(f"  Responsive Nodes: {health_summary['responsive_nodes']}")
        print(f"  Nodes with Issues: {health_summary['nodes_with_issues']}")
        
        # Blockchain status
        blockchain_status = results["blockchain_status"]
        print(f"\nBlockchain Status:")
        print(f"  Nodes with Blockchain: {blockchain_status['nodes_with_blockchain']}")
        print(f"  Average Block Count: {blockchain_status['average_block_count']:.1f}")
        
        print("="*80)

def main():
    """
    Main function to run the BGP-Sentry experiment.
    """
    print("Starting BGP-Sentry Distributed Blockchain Simulation")
    print("=" * 60)
    
    # Create experiment instance
    experiment = BGPSentryExperiment()
    
    try:
        # Step 1: Validate prerequisites
        print("Step 1: Validating prerequisites...")
        if not experiment.validate_prerequisites():
            print("Prerequisites validation failed. Exiting.")
            return 1
        
        # Step 2: Initialize experiment
        print("Step 2: Initializing experiment...")
        if not experiment.initialize_experiment():
            print("Experiment initialization failed. Exiting.")
            return 1
        
        # Step 3: Start all nodes
        print("Step 3: Starting RPKI nodes...")
        if not experiment.start_nodes():
            print("Node startup failed. Exiting.")
            return 1
        
        # Step 4: Run simulation
        print("Step 4: Running simulation...")
        if not experiment.run_simulation():
            print("Simulation failed.")
            return 1
        
        print("Experiment completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print("\nExperiment interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Experiment failed with exception: {e}")
        return 1
    finally:
        # Always attempt cleanup
        experiment.shutdown()

if __name__ == "__main__":
    sys.exit(main())
