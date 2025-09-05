#!/usr/bin/env python3
"""
Node Health Monitor for BGP-Sentry Simulation
=============================================

This module provides health monitoring capabilities for the distributed
BGP-Sentry simulation. It tracks node status, performance metrics, and
network connectivity across all RPKI nodes.

Author: Anik Tahabilder
Date: 2025-01-01
"""

import time
import threading
import socket
import json
import os
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class NodeHealthMonitor:
    """
    Monitors the health and performance of RPKI nodes in the simulation.
    
    Tracks:
    - Process status and resource usage
    - Network connectivity between nodes
    - Blockchain synchronization status
    - Performance metrics and alerts
    """
    
    def __init__(self, node_configs, monitoring_interval=10):
        """
        Initialize the health monitor.
        
        Args:
            node_configs: Dictionary of node configurations
            monitoring_interval: Seconds between health checks
        """
        self.node_configs = node_configs
        self.monitoring_interval = monitoring_interval
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Health data storage
        self.node_health_data = {}
        self.network_topology = {}
        self.performance_history = {}
        self.alerts = []
        
        # Monitoring thresholds
        self.thresholds = {
            "cpu_usage_warning": 80.0,
            "memory_usage_warning": 85.0,
            "response_timeout": 5.0,
            "max_connection_failures": 3,
            "blockchain_sync_lag_warning": 10  # blocks
        }
        
        logger.info("NodeHealthMonitor initialized")
    
    def start_monitoring(self):
        """Start the health monitoring background thread."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Health monitoring already running")
            return
        
        logger.info("Starting node health monitoring")
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
    
    def stop_monitoring(self):
        """Stop the health monitoring."""
        logger.info("Stopping node health monitoring")
        self.monitoring_active = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        logger.info("Health monitoring loop started")
        
        while self.monitoring_active:
            try:
                # Perform health checks
                self._check_all_nodes()
                
                # Check network connectivity
                self._check_network_connectivity()
                
                # Update performance metrics
                self._update_performance_metrics()
                
                # Check for alerts
                self._check_alert_conditions()
                
                # Clean up old data
                self._cleanup_old_data()
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(5)  # Short sleep on error
        
        logger.info("Health monitoring loop ended")
    
    def _check_all_nodes(self):
        """Check health status of all nodes."""
        current_time = time.time()
        
        for node_id, config in self.node_configs.items():
            try:
                health_data = self._check_single_node(node_id, config)
                health_data["last_checked"] = current_time
                
                self.node_health_data[node_id] = health_data
                
            except Exception as e:
                logger.error(f"Error checking node {node_id}: {e}")
                self.node_health_data[node_id] = {
                    "status": "error",
                    "error": str(e),
                    "last_checked": current_time
                }
    
    def _check_single_node(self, node_id, config):
        """
        Check health of a single node.
        
        Args:
            node_id: Node identifier
            config: Node configuration
            
        Returns:
            dict: Health status data
        """
        health_data = {
            "node_id": node_id,
            "status": "unknown",
            "process_running": False,
            "port_responsive": False,
            "resource_usage": {},
            "blockchain_status": {},
            "errors": []
        }
        
        # Check process status
        process = config.get("process")
        if process:
            poll_result = process.poll()
            
            if poll_result is None:
                # Process is running
                health_data["process_running"] = True
                health_data["status"] = "running"
                
                # Get resource usage
                try:
                    proc = psutil.Process(process.pid)
                    health_data["resource_usage"] = {
                        "cpu_percent": proc.cpu_percent(),
                        "memory_percent": proc.memory_percent(),
                        "memory_mb": proc.memory_info().rss / 1024 / 1024,
                        "num_threads": proc.num_threads(),
                        "create_time": proc.create_time()
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    health_data["errors"].append(f"Resource usage error: {e}")
            
            else:
                # Process has terminated
                health_data["status"] = "terminated"
                health_data["exit_code"] = poll_result
                
                # Try to get termination output
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    if stderr:
                        health_data["errors"].append(f"STDERR: {stderr[-200:]}")
                except:
                    pass
        else:
            health_data["status"] = "not_started"
        
        # Check port responsiveness
        port = config.get("port")
        if port and health_data["process_running"]:
            health_data["port_responsive"] = self._check_port_connectivity(port)
        
        # Check blockchain status
        if health_data["process_running"]:
            blockchain_status = self._check_blockchain_status(node_id)
            health_data["blockchain_status"] = blockchain_status
        
        return health_data
    
    def _check_port_connectivity(self, port, timeout=2):
        """
        Check if a node's port is responsive.
        
        Args:
            port: Port number to check
            timeout: Connection timeout in seconds
            
        Returns:
            bool: True if port is responsive
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            return result == 0
            
        except Exception:
            return False
    
    def _check_blockchain_status(self, node_id):
        """
        Check blockchain status for a node.
        
        Args:
            node_id: Node identifier
            
        Returns:
            dict: Blockchain status information
        """
        blockchain_status = {
            "blockchain_file_exists": False,
            "block_count": 0,
            "last_block_time": None,
            "file_size_bytes": 0,
            "sync_status": "unknown"
        }
        
        try:
            # Check for blockchain file
            blockchain_file = f"nodes/rpki_nodes/{node_id}/blockchain_node/local_blockchain/blockchain.json"
            
            if os.path.exists(blockchain_file):
                blockchain_status["blockchain_file_exists"] = True
                
                # Get file stats
                stat_info = os.stat(blockchain_file)
                blockchain_status["file_size_bytes"] = stat_info.st_size
                blockchain_status["last_modified"] = stat_info.st_mtime
                
                # Try to read blockchain data
                with open(blockchain_file, 'r') as f:
                    blockchain_data = json.load(f)
                
                if isinstance(blockchain_data, list):
                    blockchain_status["block_count"] = len(blockchain_data)
                    if blockchain_data:
                        last_block = blockchain_data[-1]
                        blockchain_status["last_block_time"] = last_block.get("timestamp")
                elif isinstance(blockchain_data, dict) and "blocks" in blockchain_data:
                    blocks = blockchain_data["blocks"]
                    blockchain_status["block_count"] = len(blocks)
                    if blocks:
                        last_block = blocks[-1]
                        blockchain_status["last_block_time"] = last_block.get("timestamp")
                
                blockchain_status["sync_status"] = "synced"
        
        except Exception as e:
            blockchain_status["error"] = str(e)
            blockchain_status["sync_status"] = "error"
        
        return blockchain_status
    
    def _check_network_connectivity(self):
        """Check network connectivity between nodes."""
        connectivity_matrix = {}
        
        for source_node in self.node_configs.keys():
            connectivity_matrix[source_node] = {}
            
            for target_node, target_config in self.node_configs.items():
                if source_node == target_node:
                    connectivity_matrix[source_node][target_node] = "self"
                    continue
                
                # Check if target node's port is reachable
                target_port = target_config.get("port")
                if target_port:
                    is_reachable = self._check_port_connectivity(target_port, timeout=1)
                    connectivity_matrix[source_node][target_node] = "connected" if is_reachable else "unreachable"
                else:
                    connectivity_matrix[source_node][target_node] = "no_port"
        
        self.network_topology = {
            "connectivity_matrix": connectivity_matrix,
            "last_updated": time.time()
        }
    
    def _update_performance_metrics(self):
        """Update performance metrics history."""
        current_time = time.time()
        
        for node_id, health_data in self.node_health_data.items():
            if node_id not in self.performance_history:
                self.performance_history[node_id] = []
            
            # Extract performance metrics
            if health_data.get("resource_usage"):
                metrics = {
                    "timestamp": current_time,
                    "cpu_percent": health_data["resource_usage"].get("cpu_percent", 0),
                    "memory_percent": health_data["resource_usage"].get("memory_percent", 0),
                    "memory_mb": health_data["resource_usage"].get("memory_mb", 0),
                    "port_responsive": health_data.get("port_responsive", False),
                    "block_count": health_data.get("blockchain_status", {}).get("block_count", 0)
                }
                
                self.performance_history[node_id].append(metrics)
                
                # Keep only last hour of data
                one_hour_ago = current_time - 3600
                self.performance_history[node_id] = [
                    m for m in self.performance_history[node_id] 
                    if m["timestamp"] > one_hour_ago
                ]
    
    def _check_alert_conditions(self):
        """Check for conditions that should trigger alerts."""
        current_time = time.time()
        
        for node_id, health_data in self.node_health_data.items():
            # Check if node is down
            if not health_data.get("process_running", False):
                self