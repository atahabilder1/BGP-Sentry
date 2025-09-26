import subprocess
import time
from pathlib import Path

class SimulationOrchestrator:
    def __init__(self):
        self.rpki_node_configs = self._discover_nodes()
        self.running_processes = []
    
    def _discover_nodes(self):
        nodes_dir = Path("nodes/rpki_nodes")
        return [d.name for d in nodes_dir.iterdir() if d.is_dir() and d.name.startswith("as")]
    
    def validate_prerequisites(self):
        return len(self.rpki_node_configs) > 0
    
    def start_all_nodes(self, config):
        for node in self.rpki_node_configs:
            node_path = f"nodes/rpki_nodes/{node}/blockchain_node/node.py"
            if Path(node_path).exists():
                proc = subprocess.Popen([
                    "python3", node_path
                ])
                self.running_processes.append(proc)
        return True
    
    def wait_for_node_convergence(self, timeout):
        time.sleep(5)
        return True
    
    def start_monitoring(self):
        pass
    
    def get_active_nodes(self):
        return [p for p in self.running_processes if p.poll() is None]
    
    def stop_all_nodes(self):
        for proc in self.running_processes:
            proc.terminate()
    
    def get_simulation_summary(self):
        return {
            "total_nodes": len(self.rpki_node_configs),
            "active_nodes": len(self.get_active_nodes())
        }
    
    def save_simulation_results(self, results_dir):
        pass
