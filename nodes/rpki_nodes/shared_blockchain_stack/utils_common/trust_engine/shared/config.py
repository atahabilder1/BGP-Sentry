# =============================================================================
# File: shared/config.py
# Location: trust_engine/shared/config.py
# Called by: All other files
# Calls: None
# Input: None
# Output: Configuration parameters
# =============================================================================

class Config:
    """
    Central configuration for all trust engine parameters
    Contains all constants and thresholds
    """
    
    def __init__(self):
        # RTE Parameters
        self.RTE_BASE_PENALTIES = {
            'prefix_hijacking': 15,
            'subprefix_hijacking': 10,
            'route_leak': 5
        }
        
        self.RTE_SEVERITY_WEIGHTS = {
            'prefix_hijacking': 1.0,
            'subprefix_hijacking': 0.8,
            'route_leak': 0.6
        }
        
        # ATE Parameters
        self.ATE_METRIC_WEIGHTS = {
            'attack_frequency': 0.30,
            'announcement_stability': 0.25,
            'prefix_consistency': 0.20,
            'response_time': 0.15,
            'participation': 0.10
        }
        
        self.ATE_HISTORICAL_WEIGHT = 0.4
        self.ATE_BONUS_WEIGHT = 0.1
        
        # Trust Tiers
        self.TRUST_TIERS = {
            'green': 80,
            'yellow': 30,
            'red': 0
        }
    
    def get_rte_parameters(self):
        """Return RTE configuration"""
        return {
            'base_penalties': self.RTE_BASE_PENALTIES,
            'severity_weights': self.RTE_SEVERITY_WEIGHTS
        }
    
    def get_ate_parameters(self):
        """Return ATE configuration"""
        return {
            'metric_weights': self.ATE_METRIC_WEIGHTS,
            'historical_weight': self.ATE_HISTORICAL_WEIGHT,
            'bonus_weight': self.ATE_BONUS_WEIGHT
        }