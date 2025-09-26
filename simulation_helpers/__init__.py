from .timing.shared_clock import SharedClockManager
from .coordination.orchestrator import SimulationOrchestrator
from .coordination.health_monitor import NodeHealthMonitor, HealthDashboard

def create_default_experiment_config():
    return {
        "time_scale": 1.0,
        "max_duration": 300,
        "expected_nodes": 9,
        "processing_interval": 30
    }
