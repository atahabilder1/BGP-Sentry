"""
Reactive Trust Engine (RTE)
Real-time penalty enforcement for BGP violations
"""

from .reactive_trust_engine import ReactiveTrustEngine
from .penalty_calculator import PenaltyCalculator
from .attack_classifier import AttackClassifier
from .event_processor import EventProcessor
from .trust_updater import TrustUpdater

# Make ReactiveTrustEngine available as ReactiveEngine for consistency
ReactiveEngine = ReactiveTrustEngine

__all__ = ['ReactiveTrustEngine', 'ReactiveEngine', 'PenaltyCalculator', 'AttackClassifier', 'EventProcessor', 'TrustUpdater']
