#!/usr/bin/env python3
"""
Trust Engine Configuration

Provides configuration parameters for both RTE and ATE engines
"""

class Config:
    """Configuration parameters for trust engines"""
    
    def __init__(self):
        # ATE (Adaptive Trust Engine) parameters
        self.ate_parameters = {
            'historical_weight': 0.6,  # β - weight of current trust score
            'bonus_weight': 0.1,       # γ - weight of good behavior bonus
            'metric_weights': {        # w_i - weights for each behavioral metric
                'attack_frequency': 0.30,
                'announcement_stability': 0.20,
                'prefix_consistency': 0.20,
                'response_time': 0.15,
                'participation': 0.15
            }
        }
        
        # RTE (Reactive Trust Engine) parameters
        self.rte_parameters = {
            'base_penalties': {
                'prefix_hijacking': 15.0,
                'subprefix_hijacking': 10.0,
                'route_leak': 8.0
            },
            'severity_weights': {
                'prefix_hijacking': 1.0,
                'subprefix_hijacking': 0.7,
                'route_leak': 0.5
            }
        }
    
    def get_ate_parameters(self):
        """Get ATE configuration parameters"""
        return self.ate_parameters
    
    def get_rte_parameters(self):
        """Get RTE configuration parameters"""
        return self.rte_parameters
