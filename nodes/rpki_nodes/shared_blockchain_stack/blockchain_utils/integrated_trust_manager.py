#!/usr/bin/env python3
"""
Integrated Trust Manager - Fixed Import Version
"""

import sys
import os
from pathlib import Path

class MockTrustManager:
    """Mock trust manager when real engines aren't available"""
    
    def __init__(self):
        self.trust_scores = {}
        print("✅ Mock Trust Manager initialized (fallback mode)")
    
    def get_trust_score(self, as_number):
        """Get current trust score"""
        return self.trust_scores.get(as_number, 50.0)  # Default 50
    
    def apply_trust_penalty(self, as_number, attack_type):
        """Apply trust penalty based on attack type"""
        current_score = self.get_trust_score(as_number)
        
        # Calculate penalty
        penalties = {
            'prefix_hijacking': 15.0,
            'subprefix_hijacking': 10.0, 
            'route_leak': 8.0
        }
        penalty = penalties.get(attack_type, 5.0)
        
        # Apply penalty
        new_score = max(0, current_score - penalty)
        self.trust_scores[as_number] = new_score
        
        print(f"🚨 TRUST PENALTY: AS{as_number} trust score "
              f"{current_score:.2f} → {new_score:.2f} "
              f"({attack_type}, penalty: -{penalty:.2f})")
        
        return new_score
    
    def get_trust_summary(self):
        """Get all trust scores"""
        return self.trust_scores

class IntegratedTrustManager:
    """Integrated trust manager with fallback to mock mode"""
    
    def __init__(self):
        # Use mock manager for now (we can enhance later)
        self.mock_manager = MockTrustManager()
    
    def process_attack_detection(self, announcement, detection_results, observer_asn):
        """Process attack detection and apply trust penalties"""
        
        if not detection_results['legitimate']:
            for attack in detection_results['attacks_detected']:
                attacker_asn = attack.get('hijacker_asn', attack.get('leaking_as'))
                attack_type = attack.get('attack_type', 'unknown')
                
                # Apply trust penalty
                self.mock_manager.apply_trust_penalty(attacker_asn, attack_type)
    
    def get_trust_score(self, as_number):
        """Get current trust score"""
        return self.mock_manager.get_trust_score(as_number)
    
    def get_trust_summary(self):
        """Get all trust scores"""
        return self.mock_manager.get_trust_summary()
    
    def run_periodic_evaluation(self):
        """Mock periodic evaluation"""
        print("📊 Mock periodic evaluation completed")
