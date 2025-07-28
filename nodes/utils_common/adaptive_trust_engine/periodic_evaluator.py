# =============================================================================
# File: adaptive_trust_engine/periodic_evaluator.py
# Location: trust_engine/adaptive_trust_engine/periodic_evaluator.py
# Called by: adaptive_trust_engine.py
# Calls: shared/blockchain_interface.py, shared/trust_utils.py
# Input: Monthly evaluation trigger
# Output: List of ASes to evaluate
# =============================================================================

from datetime import datetime, timedelta
from ..shared.blockchain_interface import BlockchainInterface
from ..shared.trust_utils import TrustUtils

class PeriodicEvaluator:
    """
    Manages periodic evaluation cycles for ATE
    Determines which ASes need evaluation and schedules assessments
    """
    
    def __init__(self):
        self.blockchain = BlockchainInterface()
        self.utils = TrustUtils()
        
    def get_evaluation_targets(self):
        """
        Get list of all ASes that need periodic evaluation
        Returns: List of AS numbers to evaluate
        """
        # Get all ASes that have been active in the network
        active_ases = self._get_active_ases()
        
        # Filter ASes that need evaluation (haven't been evaluated recently)
        evaluation_targets = []
        
        for as_number in active_ases:
            if self._needs_evaluation(as_number):
                evaluation_targets.append(as_number)
                
        print(f"Found {len(evaluation_targets)} ASes needing evaluation out of {len(active_ases)} active ASes")
        return evaluation_targets
    
    def _get_active_ases(self):
        """
        Get all ASes that have shown activity in the past 30 days
        """
        # Get ASes from blockchain records
        violations = self.blockchain.blockchain_data.get('violations', [])
        trust_scores = self.blockchain.blockchain_data.get('trust_scores', {})
        
        # Combine ASes from violations and trust scores
        active_ases = set()
        
        # Add ASes with violations in last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        for violation in violations:
            violation_time = datetime.fromisoformat(violation['timestamp'])
            if violation_time >= thirty_days_ago:
                active_ases.add(violation['as_number'])
            
        # Add ASes with recorded trust scores (they've participated)
        for as_str in trust_scores.keys():
            active_ases.add(int(as_str))
        
        # Add some default ASes for testing (AS 10-18 from your simulation)
        for as_num in range(10, 19):
            active_ases.add(as_num)
        
        return list(active_ases)
    
    def _needs_evaluation(self, as_number):
        """
        Check if AS needs evaluation (hasn't been evaluated in last 30 days)
        """
        last_evaluation = self.blockchain.get_last_evaluation_time(as_number)
        
        if last_evaluation is None:
            return True  # Never evaluated - needs evaluation
            
        # Check if 30 days have passed since last evaluation
        time_since_eval = datetime.now() - last_evaluation
        days_since_eval = time_since_eval.days
        
        print(f"AS{as_number}: Last evaluated {days_since_eval} days ago")
        return days_since_eval >= 30  # Evaluate if 30+ days old
    
    def mark_evaluation_complete(self, as_number):
        """
        Mark that AS has been evaluated (called after successful evaluation)
        """
        # This would typically be handled by trust_score_calculator
        # but we can add explicit tracking here
        current_time = datetime.now()
        
        if 'evaluation_timestamps' not in self.blockchain.blockchain_data:
            self.blockchain.blockchain_data['evaluation_timestamps'] = {}
            
        self.blockchain.blockchain_data['evaluation_timestamps'][str(as_number)] = current_time.isoformat()
        print(f"Marked AS{as_number} evaluation complete at {current_time}")
