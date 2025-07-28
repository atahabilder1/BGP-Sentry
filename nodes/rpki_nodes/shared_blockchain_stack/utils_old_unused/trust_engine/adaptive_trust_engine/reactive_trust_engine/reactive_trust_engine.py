# =============================================================================
# File: reactive_trust_engine/reactive_trust_engine.py  
# Location: trust_engine/reactive_trust_engine/reactive_trust_engine.py
# Called by: main_trust_coordinator.py
# Calls: event_processor.py, penalty_calculator.py, trust_updater.py
# Input: Violation events from RPKI nodes
# Output: Immediate trust score updates
# =============================================================================

from .event_processor import EventProcessor
from .penalty_calculator import PenaltyCalculator
from .trust_updater import TrustUpdater
from ..shared.config import Config

class ReactiveTrustEngine:
    """
    Reactive Trust Engine - handles immediate penalty enforcement
    Processes violation events in real-time with sub-second response
    """
    
    def __init__(self):
        self.config = Config()
        self.event_processor = EventProcessor()
        self.penalty_calculator = PenaltyCalculator()
        self.trust_updater = TrustUpdater()
        
    def process_violation(self, violation_data):
        """
        Main method to process violation and apply penalty
        Input: violation_data dict with AS info and violation details
        Output: New trust score after penalty
        """
        try:
            # Step 1: Process and validate the event
            processed_event = self.event_processor.validate_event(violation_data)
            
            # Step 2: Calculate penalty amount
            penalty_amount = self.penalty_calculator.calculate_penalty(processed_event)
            
            # Step 3: Update trust score
            new_score = self.trust_updater.apply_penalty(
                processed_event['as_number'], 
                penalty_amount
            )
            
            return new_score
            
        except Exception as e:
            print(f"RTE Error: {e}")
            return None