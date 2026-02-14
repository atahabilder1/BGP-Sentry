import subprocess
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SimulationOrchestrator:
    """
    Orchestrates the BGP-Sentry simulation.

    Supports two modes:
      1. Legacy mode: discovers AS directories on disk, starts subprocesses
      2. Virtual mode: accepts a NodeManager, runs virtual nodes in-process
    """

    def __init__(self, node_manager=None):
        self.node_manager = node_manager
        self.running_processes = []

        if node_manager:
            # Virtual mode: use node manager
            self.rpki_node_configs = [
                f"AS{asn}" for asn in sorted(node_manager.nodes.keys())
            ]
        else:
            # Legacy mode: discover from filesystem
            self.rpki_node_configs = self._discover_nodes()

    def _discover_nodes(self):
        nodes_dir = Path("nodes/rpki_nodes")
        if not nodes_dir.exists():
            return []
        return [d.name for d in nodes_dir.iterdir() if d.is_dir() and d.name.startswith("as")]

    def validate_prerequisites(self):
        if self.node_manager:
            return len(self.node_manager.nodes) > 0
        return len(self.rpki_node_configs) > 0

    def start_all_nodes(self, config=None):
        if self.node_manager:
            logger.info(f"Starting {len(self.node_manager.nodes)} virtual nodes...")
            self.node_manager.start_all()
            return True

        # Legacy subprocess mode
        for node in self.rpki_node_configs:
            node_path = f"nodes/rpki_nodes/{node}/blockchain_node/node.py"
            if Path(node_path).exists():
                proc = subprocess.Popen(["python3", node_path])
                self.running_processes.append(proc)
        return True

    def wait_for_node_convergence(self, timeout=60):
        if self.node_manager:
            # Virtual nodes are ready immediately
            return True
        time.sleep(5)
        return True

    def start_monitoring(self):
        pass

    def get_active_nodes(self):
        if self.node_manager:
            return [
                asn for asn, node in self.node_manager.nodes.items()
                if node.running or not node.is_done()
            ]
        return [p for p in self.running_processes if p.poll() is None]

    def stop_all_nodes(self):
        if self.node_manager:
            self.node_manager.stop_all()
            return

        for proc in self.running_processes:
            proc.terminate()

    def get_simulation_summary(self):
        if self.node_manager:
            return self.node_manager.get_summary()
        return {
            "total_nodes": len(self.rpki_node_configs),
            "active_nodes": len(self.get_active_nodes())
        }

    def save_simulation_results(self, results_dir):
        pass
