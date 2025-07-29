#=============================================================================
# File: main_trust_coordinator.py
# Location: trust_engine/main_trust_coordinator.py
# Called by: RPKI nodes (external), BGP-Sentry main system
# Calls: reactive_trust_engine.py, adaptive_trust_engine.py
# Input: BGP violation events, periodic evaluation triggers
# Output: Updated trust scores, staking requirements
# =============================================================================

import json
import threading
import time
from datetime import datetime
from reactive_trust_engine.reactive_trust_engine import ReactiveTrustEngine
from adaptive_trust_engine.adaptive_trust_engine import AdaptiveTrustEngine
from shared.blockchain_interface import BlockchainInterface
from shared.config import Config

class TrustCoordinator:
    """
    Main coordinator that manages both RTE and ATE engines
    Handles incoming violation events and periodic evaluations
    """
    
    def __init__(self):
        self.config = Config()
        self.rte = ReactiveTrustEngine()  # For instant penalties
        self.ate = AdaptiveTrustEngine()  # For periodic evaluation
        self.blockchain = BlockchainInterface()
        self.running = False
        
    def start_coordinator(self):
        """Start the trust coordinator service"""
        self.running = True
        print(f"[{datetime.now()}] Trust Coordinator started")
        
        # Start periodic ATE evaluation thread
        ate_thread = threading.Thread(target=self._periodic_ate_runner)
        ate_thread.daemon = True
        ate_thread.start()
        
    def process_violation_event(self, violation_data):
        """
        Process incoming violation events from RPKI nodes
        Input: violation_data = {
            'as_number': int,
            'attack_type': str,
            'timestamp': datetime,
            'prefix': str,
            'reporter_node': str
        }
        Output: Updated trust score
        """
        try:
            # Use RTE for immediate penalty
            new_trust_score = self.rte.process_violation(violation_data)
            
            # Log to blockchain
            self.blockchain.log_violation(violation_data, new_trust_score)
            
            print(f"[{datetime.now()}] AS{violation_data['as_number']} "
                  f"penalized for {violation_data['attack_type']}, "
                  f"new score: {new_trust_score}")
            
            return new_trust_score
            
        except Exception as e:
            print(f"Error processing violation: {e}")
            return None
    
    def _periodic_ate_runner(self):
        """Background thread for monthly ATE evaluations"""
        while self.running:
            # Sleep for monthly interval (30 days = 2592000 seconds)
            # For testing, use shorter interval like 3600 seconds (1 hour)
            time.sleep(3600)  # Change to 2592000 for production
            
            print(f"[{datetime.now()}] Starting monthly ATE evaluation")
            self.ate.run_monthly_evaluation()