# =============================================================================
# File: adaptive_trust_engine/trust_score_calculator.py
# Location: trust_engine/adaptive_trust_engine/trust_score_calculator.py
# Called by: adaptive_trust_engine.py
# Calls: shared/config.py, shared/trust_utils.py, shared/blockchain_interface.py
# Input: AS number and behavioral metrics
# Output: New periodic trust score
# =============================================================================

from ..shared.config import Config
from ..shared.trust_utils import TrustUtils
from ..shared.blockchain_interface import BlockchainInterface

class TrustScoreCalculator:
    """
    Calculates new trust scores using ATE periodic formula
    Only component that can increase trust scores
    """
    
    def __init__(self):
        self.config = Config()
        self.utils = TrustUtils()
        self.blockchain = BlockchainInterface()
        
    def calculate_periodic_score(self, as_number, metrics_scores):
        """
        Calculate new trust score using ATE formula:
        T_periodic = β × T_historical + (1-β) × Σ(w_i × f_i) + γ × B_bonus
        
        Input: as_number (int), metrics_scores (dict)
        Output: New trust score
        """
        # Get configuration parameters
        ate_params = self.config.get_ate_parameters()
        
        # Get current trust score
        current_score = self.utils.get_trust_score(as_number)
        
        # Calculate weighted metric sum
        weighted_metrics = self._calculate_weighted_metrics(metrics_scores, ate_params)
        
        # Calculate sustained good behavior bonus
        bonus = self._calculate_bonus(as_number)
        
        # Apply ATE formula
        new_score = (
            ate_params['historical_weight'] * current_score +
            (1 - ate_params['historical_weight']) * weighted_metrics +
            ate_params['bonus_weight'] * bonus
        )
        
        # Ensure score stays within bounds (0-100)
        new_score = max(0, min(100, new_score))
        
        # Update trust score
        self.utils.update_trust_score(as_number, new_score)
        
        # Log evaluation to blockchain
        self._log_evaluation(as_number, metrics_scores, new_score)
        
        return new_score
    
    def _calculate_weighted_metrics(self, metrics_scores, ate_params):
        """
        Calculate Σ(w_i × f_i) - weighted sum of behavioral metrics
        """
        weights = ate_params['metric_weights']
        
        weighted_sum = (
            weights['attack_frequency'] * metrics_scores['attack_frequency'] +
            weights['announcement_stability'] * metrics_scores['announcement_stability'] +
            weights['prefix_consistency'] * metrics_scores['prefix_consistency'] +
            weights['response_time'] * metrics_scores['response_time'] +
            weights['participation'] * metrics_scores['participation']
        )
        
        return weighted_sum
    
    def _calculate_bonus(self, as_number):
        """
        Calculate sustained good behavior bonus (max 10 points)
        """
        # Check for sustained good behavior (no violations in 90+ days)
        last_violation = self.utils.get_last_violation_time(as_number)
        
        if last_violation is None:
            return 10  # Never violated = maximum bonus
            
        days_since_violation = (datetime.now() - last_violation).days
        
        if days_since_violation >= 90:
            return 10  # 90+ days clean = maximum bonus
        elif days_since_violation >= 60:
            return 7   # 60-89 days clean = good bonus
        elif days_since_violation >= 30:
            return 5   # 30-59 days clean = moderate bonus
        else:
            return 0   # Recent violation = no bonus
    
    def _log_evaluation(self, as_number, metrics_scores, new_score):
        """
        Log periodic evaluation to blockchain for audit trail
        """
        evaluation_log = {
            'timestamp': datetime.now().isoformat(),
            'as_number': as_number,
            'evaluation_type': 'monthly_ate',
            'metrics_scores': metrics_scores,
            'new_trust_score': new_score
        }
        
        # Add to blockchain evaluation logs
        if 'evaluations' not in self.blockchain.blockchain_data:
            self.blockchain.blockchain_data['evaluations'] = []
            
        self.blockchain.blockchain_data['evaluations'].append(evaluation_log)
