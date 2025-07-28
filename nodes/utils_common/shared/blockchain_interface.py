# =============================================================================
# File: shared/blockchain_interface.py
# Location: trust_engine/shared/blockchain_interface.py
# Called by: Multiple files for data persistence
# Calls: External blockchain APIs
# Input: Trust scores, violations, timestamps
# Output: Blockchain transaction results
# =============================================================================

import json
from datetime import datetime

class BlockchainInterface:
    """
    Interface to blockchain for immutable logging
    Handles all blockchain read/write operations
    """
    
    def __init__(self):
        # Initialize blockchain connection
        self.blockchain_data = {}  # Simulated blockchain storage
        
    def log_violation(self, violation_data, new_trust_score):
        """
        Log violation event to blockchain
        Creates immutable audit trail
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'as_number': violation_data['as_number'],
            'attack_type': violation_data['attack_type'],
            'penalty_applied': violation_data.get('penalty_amount', 0),
            'new_trust_score': new_trust_score,
            'reporter': violation_data.get('reporter_node', 'unknown')
        }
        
        # Add to blockchain (simplified implementation)
        if 'violations' not in self.blockchain_data:
            self.blockchain_data['violations'] = []
        
        self.blockchain_data['violations'].append(log_entry)
        print(f"Logged violation to blockchain: AS{violation_data['as_number']}")
    
    def get_trust_score(self, as_number):
        """Retrieve trust score from blockchain"""
        trust_scores = self.blockchain_data.get('trust_scores', {})
        return trust_scores.get(str(as_number), None)
    
    def update_trust_score(self, as_number, new_score):
        """Update trust score on blockchain"""
        if 'trust_scores' not in self.blockchain_data:
            self.blockchain_data['trust_scores'] = {}
        
        self.blockchain_data['trust_scores'][str(as_number)] = new_score
    
    def get_last_violation_time(self, as_number):
        """Get timestamp of last violation"""
        violations = self.blockchain_data.get('violations', [])
        
        # Find most recent violation for this AS
        as_violations = [v for v in violations if v['as_number'] == as_number]
        
        if as_violations:
            latest = max(as_violations, key=lambda x: x['timestamp'])
            return datetime.fromisoformat(latest['timestamp'])
        
        return None
    
    def record_violation_time(self, as_number, timestamp):
        """Record violation timestamp"""
        # This is typically handled by log_violation method
        pass