# =============================================================================
# File: adaptive_trust_engine/adaptive_trust_engine.py
# Location: trust_engine/adaptive_trust_engine/adaptive_trust_engine.py
# Called by: main_trust_coordinator.py (monthly)
# Calls: periodic_evaluator.py, behavioral_metrics.py, trust_score_calculator.py
# Input: Monthly evaluation trigger
# Output: Updated trust scores for all ASes
# =============================================================================

from .periodic_evaluator import PeriodicEvaluator
from .behavioral_metrics import BehavioralMetrics
from .trust_score_calculator import TrustScoreCalculator
from ..shared.config import Config

class AdaptiveTrustEngine:
    """
    Adaptive Trust Engine - handles monthly comprehensive behavioral assessment
    Can increase trust scores based on good long-term behavior
    """
    
    def __init__(self):
        self.config = Config()
        self.evaluator = PeriodicEvaluator()
        self.metrics = BehavioralMetrics()
        self.calculator = TrustScoreCalculator()
        
    def run_monthly_evaluation(self):
        """
        Run monthly evaluation for all ASes
        This is the only method that can increase trust scores
        """
        try:
            # Get list of all ASes to evaluate
            as_list = self.evaluator.get_evaluation_targets()
            
            print(f"Starting monthly evaluation for {len(as_list)} ASes")
            
            # Process each AS
            for as_number in as_list:
                self._evaluate_single_as(as_number)
                
            print("Monthly evaluation completed")
            
        except Exception as e:
            print(f"ATE Error during monthly evaluation: {e}")
    
    def _evaluate_single_as(self, as_number):
        """
        Evaluate single AS using 5 behavioral metrics
        """
        # Calculate all 5 behavioral metrics
        metrics_scores = self.metrics.calculate_all_metrics(as_number)
        
        # Calculate new periodic trust score
        new_score = self.calculator.calculate_periodic_score(
            as_number, 
            metrics_scores
        )
        
        print(f"AS{as_number}: New trust score = {new_score}")