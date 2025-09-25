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
from datetime import datetime
from typing import Dict, List, Any
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
        self._active_alerts = {}
        self.alert_cooldown_seconds = 30
        self.history_retention_seconds = 3600
        self.max_alerts = 200

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
                self._record_alert(
                    node_id,
                    alert_type="node_down",
                    severity="critical",
                    message="Node process is not running",
                    timestamp=current_time,
                )
                continue

            # Port responsiveness
            if not health_data.get("port_responsive", False):
                self._record_alert(
                    node_id,
                    alert_type="port_unresponsive",
                    severity="warning",
                    message="Node port is not accepting connections",
                    timestamp=current_time,
                )

            # Resource usage thresholds
            usage = health_data.get("resource_usage", {})
            cpu = usage.get("cpu_percent")
            if cpu is not None and cpu >= self.thresholds["cpu_usage_warning"]:
                self._record_alert(
                    node_id,
                    alert_type="high_cpu",
                    severity="warning",
                    message=f"CPU usage at {cpu:.1f}% exceeds threshold",
                    timestamp=current_time,
                )

            memory = usage.get("memory_percent")
            if memory is not None and memory >= self.thresholds["memory_usage_warning"]:
                self._record_alert(
                    node_id,
                    alert_type="high_memory",
                    severity="warning",
                    message=f"Memory usage at {memory:.1f}% exceeds threshold",
                    timestamp=current_time,
                )

            # Blockchain status parity
            blockchain_status = health_data.get("blockchain_status", {})
            if blockchain_status.get("sync_status") == "error":
                message = blockchain_status.get("error", "Blockchain status error detected")
                self._record_alert(
                    node_id,
                    alert_type="blockchain_error",
                    severity="error",
                    message=message,
                    timestamp=current_time,
                )

        # After processing individual nodes, compare block counts
        block_counts = [
            data.get("blockchain_status", {}).get("block_count", 0)
            for data in self.node_health_data.values()
            if data.get("process_running", False)
        ]
        if block_counts:
            max_blocks = max(block_counts)
            for node_id, health_data in self.node_health_data.items():
                blockchain_status = health_data.get("blockchain_status", {})
                block_count = blockchain_status.get("block_count", 0)
                if max_blocks - block_count >= self.thresholds["blockchain_sync_lag_warning"]:
                    self._record_alert(
                        node_id,
                        alert_type="blockchain_lag",
                        severity="warning",
                        message=(
                            f"Blockchain lag detected: {block_count} blocks vs {max_blocks} max"
                        ),
                        timestamp=current_time,
                    )

    def _record_alert(
        self,
        node_id: str,
        *,
        alert_type: str,
        severity: str,
        message: str,
        timestamp: float,
    ) -> None:
        """Record an alert with basic de-duplication semantics."""

        key = (node_id, alert_type)
        last_timestamp = self._active_alerts.get(key)
        if last_timestamp and timestamp - last_timestamp < self.alert_cooldown_seconds:
            return

        alert = {
            "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
            "node_id": node_id,
            "type": alert_type,
            "severity": severity,
            "message": message,
        }
        self.alerts.append(alert)
        self._active_alerts[key] = timestamp

        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]

        logger.warning(
            "Alert for %s [%s]: %s", node_id, alert_type, message
        )

    def _cleanup_old_data(self):
        """Trim alert history and drop stale node entries."""

        cutoff = time.time() - self.history_retention_seconds

        # Expire alerts beyond retention window
        def _alert_ts(alert: Dict[str, Any]) -> float:
            try:
                return datetime.fromisoformat(alert["timestamp"]).timestamp()
            except (KeyError, ValueError):
                return float("inf")

        self.alerts = [alert for alert in self.alerts if _alert_ts(alert) >= cutoff]

        # Release cooldown entries that are outside the retention window
        self._active_alerts = {
            key: ts for key, ts in self._active_alerts.items() if ts >= cutoff
        }

        # Drop node health entries we have not checked in a long time
        stale_nodes = [
            node_id
            for node_id, data in self.node_health_data.items()
            if cutoff > data.get("last_checked", 0)
        ]
        for node_id in stale_nodes:
            self.node_health_data.pop(node_id, None)

    def get_node_health_summary(self) -> Dict[str, Any]:
        """Return aggregated counts of node health states."""

        total_nodes = len(self.node_configs)
        running = sum(1 for data in self.node_health_data.values() if data.get("process_running"))
        responsive = sum(1 for data in self.node_health_data.values() if data.get("port_responsive"))
        nodes_with_issues = sum(
            1
            for data in self.node_health_data.values()
            if (not data.get("process_running", False))
            or (not data.get("port_responsive", False))
            or data.get("errors")
        )

        return {
            "total_nodes": total_nodes,
            "running_nodes": running,
            "responsive_nodes": responsive,
            "nodes_with_issues": nodes_with_issues,
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Aggregate CPU and memory stats for each node."""

        metrics: Dict[str, Any] = {}
        for node_id, history in self.performance_history.items():
            if not history:
                continue

            avg_cpu = sum(sample["cpu_percent"] for sample in history) / len(history)
            avg_mem = sum(sample["memory_percent"] for sample in history) / len(history)
            last_sample = history[-1]

            metrics[node_id] = {
                "average_cpu_percent": avg_cpu,
                "average_memory_percent": avg_mem,
                "latest": last_sample,
            }

        return metrics

    def get_blockchain_sync_status(self) -> Dict[str, Any]:
        """Summarise blockchain availability and synchronisation."""

        block_counts = []
        nodes_with_blockchain = 0

        for data in self.node_health_data.values():
            blockchain_status = data.get("blockchain_status", {})
            if blockchain_status.get("blockchain_file_exists"):
                nodes_with_blockchain += 1
                block_counts.append(blockchain_status.get("block_count", 0))

        average_block_count = sum(block_counts) / len(block_counts) if block_counts else 0.0

        return {
            "nodes_with_blockchain": nodes_with_blockchain,
            "average_block_count": average_block_count,
            "block_counts": block_counts,
        }

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the most recent alerts up to ``limit`` entries."""

        return self.alerts[-limit:]

    def export_health_report(self, output_path: str) -> None:
        """Persist a JSON health report for external analysis."""

        report = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": self.get_node_health_summary(),
            "node_health": self.node_health_data,
            "performance_metrics": self.get_performance_metrics(),
            "blockchain_status": self.get_blockchain_sync_status(),
            "alerts": self.get_recent_alerts(limit=100),
            "network_topology": self.network_topology,
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)


class HealthDashboard:
    """Lightweight console dashboard for experiment status output."""

    def __init__(self, monitor: NodeHealthMonitor) -> None:
        self._monitor = monitor

    def print_status_summary(self) -> None:
        summary = self._monitor.get_node_health_summary()
        print(
            f"Nodes running: {summary['running_nodes']}/{summary['total_nodes']} | "
            f"Responsive: {summary['responsive_nodes']} | "
            f"Issues: {summary['nodes_with_issues']}"
        )

        blockchain = self._monitor.get_blockchain_sync_status()
        print(
            f"Blockchain copies: {blockchain['nodes_with_blockchain']} | "
            f"Avg blocks: {blockchain['average_block_count']:.1f}"
        )

    def print_recent_alerts(self, max_alerts: int = 5) -> None:
        alerts = self._monitor.get_recent_alerts(limit=max_alerts)
        if not alerts:
            print("No recent alerts")
            return

        print("Recent alerts:")
        for alert in alerts:
            print(
                f"  [{alert['timestamp']}] {alert['node_id']} "
                f"({alert['severity']}): {alert['message']}"
            )
