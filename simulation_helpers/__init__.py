from .timing.shared_clock import SharedClockManager, SimulationClock
from .coordination.orchestrator import SimulationOrchestrator
from .coordination.health_monitor import NodeHealthMonitor, HealthDashboard

def create_default_experiment_config(expected_nodes=None):
    if expected_nodes is None:
        try:
            from nodes.rpki_nodes.shared_blockchain_stack.blockchain_utils.rpki_node_registry import RPKINodeRegistry
            expected_nodes = RPKINodeRegistry.get_node_count()
        except Exception:
            expected_nodes = 9  # legacy fallback
    return {
        "time_scale": 1.0,
        "max_duration": 300,
        "expected_nodes": expected_nodes,
        "processing_interval": 30
    }
