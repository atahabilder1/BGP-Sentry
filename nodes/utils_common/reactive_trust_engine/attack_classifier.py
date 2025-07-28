# =============================================================================
# File: reactive_trust_engine/attack_classifier.py
# Location: trust_engine/reactive_trust_engine/attack_classifier.py
# Called by: event_processor.py
# Calls: shared/config.py
# Input: Attack type and prefix information
# Output: Attack classification with severity weights
# =============================================================================

from ..shared.config import Config

class AttackClassifier:
    """
    Classifies BGP attacks and determines severity weights
    Maps attack types to penalty parameters
    """
    
    def __init__(self):
        self.config = Config()
        
    def classify_attack(self, attack_type, prefix_info=None):
        """
        Classify attack and return severity parameters
        Input: attack_type (str), prefix_info (dict)
        Output: Classification with penalty parameters
        """
        # Get attack parameters from config
        attack_params = self.config.get_rte_parameters()
        
        attack_type_lower = attack_type.lower()
        
        if 'prefix_hijack' in attack_type_lower and 'sub' not in attack_type_lower:
            return {
                'classified_type': 'prefix_hijacking',
                'base_penalty': attack_params['base_penalties']['prefix_hijacking'],
                'severity_weight': attack_params['severity_weights']['prefix_hijacking'],
                'description': 'Complete unauthorized prefix announcement'
            }
        elif 'subprefix' in attack_type_lower or 'sub-prefix' in attack_type_lower:
            return {
                'classified_type': 'subprefix_hijacking', 
                'base_penalty': attack_params['base_penalties']['subprefix_hijacking'],
                'severity_weight': attack_params['severity_weights']['subprefix_hijacking'],
                'description': 'More-specific prefix announcement'
            }
        elif 'route_leak' in attack_type_lower or 'leak' in attack_type_lower:
            return {
                'classified_type': 'route_leak',
                'base_penalty': attack_params['base_penalties']['route_leak'], 
                'severity_weight': attack_params['severity_weights']['route_leak'],
                'description': 'Policy violation in route propagation'
            }
        else:
            # Default to route leak for unknown types
            return {
                'classified_type': 'unknown',
                'base_penalty': 5,
                'severity_weight': 0.5,
                'description': 'Unknown violation type'
            }
