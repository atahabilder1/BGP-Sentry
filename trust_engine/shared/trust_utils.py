#!/usr/bin/env python3
"""
Trust Utilities - Common utilities for trust score management
"""

import json
from datetime import datetime, timezone
from pathlib import Path

class TrustUtils:
    """Utilities for trust score management"""
    
    def __init__(self):
        self.trust_file = Path("../shared_data/state/trust_state.json")
        self.trust_file.parent.mkdir(exist_ok=True)
        
        # Initialize trust state file if it doesn't exist
        if not self.trust_file.exists():
            self._initialize_trust_state()
    
    def _initialize_trust_state(self):
        """Initialize trust state file"""
        initial_state = {
            "trust_scores": {},
            "last_violations": {},
            "last_evaluations": {},
            "created": datetime.now(timezone.utc).isoformat()
        }
        
        with open(self.trust_file, 'w') as f:
            json.dump(initial_state, f, indent=2)
    
    def get_trust_score(self, as_number):
        """Get current trust score for AS"""
        try:
            with open(self.trust_file, 'r') as f:
                data = json.load(f)
            
            return data.get('trust_scores', {}).get(str(as_number), 50.0)
        except:
            return 50.0  # Default score
    
    def update_trust_score(self, as_number, new_score):
        """Update trust score for AS"""
        try:
            with open(self.trust_file, 'r') as f:
                data = json.load(f)
        except:
            data = {"trust_scores": {}, "last_violations": {}, "last_evaluations": {}}
        
        data['trust_scores'][str(as_number)] = new_score
        data['last_updated'] = datetime.now(timezone.utc).isoformat()
        
        with open(self.trust_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def record_violation_time(self, as_number):
        """Record when AS had a violation"""
        try:
            with open(self.trust_file, 'r') as f:
                data = json.load(f)
        except:
            data = {"trust_scores": {}, "last_violations": {}, "last_evaluations": {}}
        
        data['last_violations'][str(as_number)] = datetime.now(timezone.utc).isoformat()
        
        with open(self.trust_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_last_violation_time(self, as_number):
        """Get when AS last had a violation"""
        try:
            with open(self.trust_file, 'r') as f:
                data = json.load(f)
            
            violation_str = data.get('last_violations', {}).get(str(as_number))
            if violation_str:
                return datetime.fromisoformat(violation_str.replace('Z', '+00:00'))
        except:
            pass
        
        return None
