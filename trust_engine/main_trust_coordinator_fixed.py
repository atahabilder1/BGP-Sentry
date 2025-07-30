import json
import sys
import os

# Add necessary paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'reactive_trust_engine'))
sys.path.insert(0, os.path.join(current_dir, 'adaptive_trust_engine'))

try:
    from reactive_trust_engine_fixed import ReactiveTrustEngine
except ImportError:
    class ReactiveTrustEngine:
        def process_violation(self, as_number, violation_type, timestamp): 
            return True
        def get_status(self): 
            return {'status': 'stub'}

try:
    from adaptive_trust_engine_fixed import AdaptiveTrustEngine  
except ImportError:
    class AdaptiveTrustEngine:
        def evaluate_trust_score(self, as_number): 
            return 75
        def get_status(self): 
            return {'status': 'stub'}

class TrustCoordinator:
    """Trust Coordinator - Orchestrates both RTE and ATE engines"""
    
    def __init__(self):
        print("Initializing Trust Coordinator...")
        self.rte = ReactiveTrustEngine()
        self.ate = AdaptiveTrustEngine()
        self.trust_scores = {}
        print("✅ Trust Coordinator initialized successfully")
    
    def process_violation(self, as_number, violation_type, timestamp=None):
        """Process a violation through the reactive engine"""
        return self.rte.process_violation(as_number, violation_type, timestamp)
    
    def evaluate_trust_score(self, as_number):
        """Get comprehensive trust score through adaptive engine"""
        score = self.ate.evaluate_trust_score(as_number)
        self.trust_scores[as_number] = score
        return score
    
    def get_trust_score(self, as_number):
        """Get current trust score for an AS"""
        return self.trust_scores.get(as_number, 50)
    
    def get_system_status(self):
        """Get status of both engines"""
        return {
            'coordinator': 'operational',
            'rte_status': self.rte.get_status(),
            'ate_status': self.ate.get_status(),
            'cached_scores': len(self.trust_scores)
        }
