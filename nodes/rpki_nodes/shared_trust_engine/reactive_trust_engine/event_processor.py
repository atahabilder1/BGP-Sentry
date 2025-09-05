# =============================================================================
# File: reactive_trust_engine/event_processor.py
# Location: trust_engine/reactive_trust_engine/event_processor.py  
# Called by: reactive_trust_engine.py
# Calls: attack_classifier.py, shared/trust_utils.py
# Input: Raw violation events
# Output: Validated and classified events
# =============================================================================

import json
from datetime import datetime
from .attack_classifier import AttackClassifier
from ..shared.trust_utils import TrustUtils

class EventProcessor:
    """
    Processes and validates incoming violation events
    Ensures data integrity and proper formatting
    """
    
    def __init__(self):
        self.classifier = AttackClassifier()
        self.utils = TrustUtils()
        
    def validate_event(self, violation_data):
        """
        Validate and process incoming violation event
        Input: Raw violation data from RPKI observer
        Output: Processed event with attack classification
        """
        # Validate required fields
        required_fields = ['as_number', 'attack_type', 'timestamp', 'prefix']
        for field in required_fields:
            if field not in violation_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Classify attack type and get severity
        attack_info = self.classifier.classify_attack(
            violation_data['attack_type'],
            violation_data.get('prefix_info', {})
        )
        
        # Add classification to event data
        processed_event = violation_data.copy()
        processed_event.update(attack_info)
        processed_event['processed_timestamp'] = datetime.now()
        
        return processed_event