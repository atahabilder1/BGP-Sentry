# =============================================================================
# File: shared/trust_utils.py
# Location: trust_engine/shared/trust_utils.py
# Called by: Multiple files (trust_updater, penalty_calculator, etc.)
# Calls: blockchain_interface.py
# Input: AS numbers, trust scores, timestamps
# Output: Trust data and utilities
# =============================================================================

import json
from datetime import datetime
from .blockchain_interface import BlockchainInterface

class TrustUtils:
    """
    Utility functions for trust score management
    Handles caching, persistence, and data retrieval
    """
    
    def __init__(self):
        self.blockchain = BlockchainInterface()
        self.trust_cache = {}  # In-memory cache for fast access
        self.violation_times = {}  # Track last violation times
        
    def get_trust_score(self, as_number):
        """
        Get current trust score for AS
        Input: as_number (int)
        Output: current trust score (float)
        """
        if as_number in self.trust_cache:
            return self.trust_cache[as_number]
        
        # Load from blockchain if not in cache
        score = self.blockchain.get_trust_score(as_number)
        if score is None:
            score = 100.0  # Default score for new AS
            
        self.trust_cache[as_number] = score
        return score
    
    def update_trust_score(self, as_number, new_score):
        """
        Update trust score in cache and blockchain
        """
        self.trust_cache[as_number] = new_score
        self.blockchain.update_trust_score(as_number, new_score)
    
    def get_last_violation_time(self, as_number):
        """
        Get timestamp of last violation for recency calculation
        """
        if as_number in self.violation_times:
            return self.violation_times[as_number]
        
        # Load from blockchain
        return self.blockchain.get_last_violation_time(as_number)
    
    def record_violation_time(self, as_number):
        """
        Record current time as last violation time
        """
        current_time = datetime.now()
        self.violation_times[as_number] = current_time
        self.blockchain.record_violation_time(as_number, current_time)