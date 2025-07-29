# =============================================================================
# File: reactive_trust_engine/trust_updater.py
# Location: trust_engine/reactive_trust_engine/trust_updater.py
# Called by: reactive_trust_engine.py
# Calls: shared/trust_utils.py, shared/blockchain_interface.py
# Input: AS number and penalty amount
# Output: New trust score after penalty
# =============================================================================

from ..shared.trust_utils import TrustUtils
from ..shared.blockchain_interface import BlockchainInterface

class TrustUpdater:
    """
    Updates trust scores after penalty calculation
    Handles score persistence and validation
    """
    
    def __init__(self):
        self.utils = TrustUtils()
        self.blockchain = BlockchainInterface()
        
    def apply_penalty(self, as_number, penalty_amount):
        """
        Apply penalty to AS trust score
        Input: as_number (int), penalty_amount (float)
        Output: New trust score
        """
        # Get current trust score
        current_score = self.utils.get_trust_score(as_number)
        
        # Calculate new score (minimum 0)
        new_score = max(0, current_score - penalty_amount)
        
        # Update trust score in cache and blockchain
        self.utils.update_trust_score(as_number, new_score)
        
        # Record violation timestamp
        self.utils.record_violation_time(as_number)
        
        return new_score