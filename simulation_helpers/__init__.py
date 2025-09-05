"""
BGP-Sentry Simulation Helpers
============================

This package provides utility modules for orchestrating and monitoring
the distributed BGP-Sentry blockchain simulation.

Modules:
- timing: Time synchronization utilities
- coordination: Node orchestration and health monitoring

Author: Anik Tahabilder
Date: 2025-01-01
"""

from .timing.shared_clock import SharedClockManager, create_default_experiment_config
from .timing.time_synchronizer import NodeTimeSynchronizer, BGPTimeWindowManager
from .coordination.orchestrator import SimulationOrchestrator
from .coordination.health_monitor import NodeHealthMonitor, HealthDashboard

__version__ = "1.0.0"
__author__ = "Anik Tahabilder"

__all__ = [
    "SharedClockManager",
    "NodeTimeSynchronizer", 
    "BGPTimeWindowManager",
    "SimulationOrchestrator",
    "NodeHealthMonitor",
    "HealthDashboard",
    "create_default_experiment_config"
]
