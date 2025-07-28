# =============================================================================
# File: reactive_trust_engine/penalty_calculator.py
# Location: trust_engine/reactive_trust_engine/penalty_calculator.py
# Called by: reactive_trust_engine.py
# Calls: shared/trust_utils.py, shared/config.py
# Input: Processed violation event
# Output: Calculated penalty amount
# =============================================================================

from datetime import datetime, timedelta
from ..shared.config import Config
from ..shared.trust_utils import TrustUtils

class PenaltyCalculator:
    """
    Calculates penalty amounts based on attack type, severity, and recency
    Implements the RTE penalty formula
    """
    
    def __init__(self):
        self.config = Config()
        self.utils = TrustUtils()
        
    def calculate_penalty(self, processed_event):
        """
        Calculate penalty using RTE formula:
        T_instant = T_current - (P_base × S_weight × R_factor)
        
        Input: processed_event with attack classification
        Output: penalty amount to deduct
        """
        # Get recency factor based on last violation time
        recency_factor = self._get_recency_factor(processed_event['as_number'])
        
        # Calculate penalty
        penalty = (
            processed_event['base_penalty'] * 
            processed_event['severity_weight'] * 
            recency_factor
        )
        
        return round(penalty, 2)
    
    def _get_recency_factor(self, as_number):
        """
        Calculate recency factor based on time since last violation
        Returns: 1.0 (0-24h), 0.7 (24-72h), 0.4 (>72h)
        """
        last_violation = self.utils.get_last_violation_time(as_number)
        
        if last_violation is None:
            return 1.0  # First violation gets full penalty
            
        time_diff = datetime.now() - last_violation
        
        if time_diff <= timedelta(hours=24):
            return 1.0  # Recent violation
        elif time_diff <= timedelta(hours=72):
            return 0.7  # Medium time gap
        else:
            return 0.4  # Old violation
