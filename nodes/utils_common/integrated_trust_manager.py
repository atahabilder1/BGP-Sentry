#!/usr/bin/env python3
"""
Integrated Trust Manager

Coordinates both Reactive and Adaptive Trust Engines with attack detection
"""

import sys
import os
from pathlib import Path

# Add trust engine paths
trust_engine_path = Path(__file__).parent / "trust_engine"
sys.path.insert(0, str(trust_engine_path))

from reactive_trust_engine.reactive_trust_engine import ReactiveTrustEngine
from adaptive_trust_engine.adaptive_trust_engine import AdaptiveTrustEngine
from trust_state import TrustState

class IntegratedTrustManager:
    """Manages both reactive and adaptive trust engines"""
    
    def __init__(self):
        self.reactive_engine = ReactiveTrustEngine()
        self.adaptive_engine = AdaptiveTrustEngine()
        self.trust_state = TrustState()
        
        print("✅ Integrated Trust Manager initialized")
    
    def process_attack_detection(self, announcement, detection_results, observer_asn):
        """
        Process attack detection results and trigger reactive trust updates
        Called when attacks are detected by BGP observer
        """
        
        if not detection_results['legitimate']:
            # Process each detected attack
            for attack in detection_results['attacks_detected']:
                
                # Prepare violation data for reactive engine
                violation_data = {
                    'as_number': attack.get('hijacker_asn', attack.get('leaking_as')),
                    'attack_type': attack['attack_type'],
                    'timestamp': announcement.get('timestamp'),
                    'prefix': attack.get('hijacked_prefix', attack.get('leaked_prefix')),
                    'observer_as': observer_asn,
                    'severity': attack.get('severity', 'medium'),
                    'confidence': attack.get('confidence', 0.8)
                }
                
                # Apply immediate penalty via reactive engine
                new_trust_score = self.reactive_engine.process_violation(violation_data)
                
                if new_trust_score is not None:
                    print(f"🚨 TRUST PENALTY: AS{violation_data['as_number']} "
                          f"trust score → {new_trust_score:.2f} "
                          f"({attack['attack_type']})")
                
                # Log trust change for analysis
                self._log_trust_change(violation_data, new_trust_score)
        
        else:
            # Record legitimate behavior (for adaptive engine analysis)
            self._record_legitimate_behavior(announcement['sender_asn'])
    
    def run_periodic_evaluation(self):
        """
        Run monthly adaptive trust evaluation
        Should be called periodically (monthly)
        """
        print("📊 Starting monthly adaptive trust evaluation...")
        self.adaptive_engine.run_monthly_evaluation()
        print("✅ Monthly evaluation completed")
    
    def get_trust_score(self, as_number):
        """Get current trust score for AS"""
        return self.trust_state.get_trust_score(as_number)
    
    def get_trust_summary(self):
        """Get summary of all trust scores"""
        return self.trust_state.get_all_trust_scores()
    
    def _log_trust_change(self, violation_data, new_score):
        """Log trust score changes for analysis"""
        log_entry = {
            'timestamp': violation_data['timestamp'],
            'as_number': violation_data['as_number'],
            'attack_type': violation_data['attack_type'],
            'new_trust_score': new_score,
            'engine': 'reactive'
        }
        
        # Add to trust change log (for Excel analysis)
        trust_log_file = Path("../shared_data/logs/trust_changes.csv")
        
        # Create header if file doesn't exist
        if not trust_log_file.exists():
            with open(trust_log_file, 'w') as f:
                f.write("Timestamp,AS_Number,Attack_Type,New_Trust_Score,Engine\n")
        
        # Append trust change
        with open(trust_log_file, 'a') as f:
            f.write(f"{log_entry['timestamp']},{log_entry['as_number']},"
                   f"{log_entry['attack_type']},{log_entry['new_trust_score']},"
                   f"{log_entry['engine']}\n")
    
    def _record_legitimate_behavior(self, as_number):
        """Record legitimate behavior for adaptive engine analysis"""
        # This data will be used by adaptive engine for positive scoring
        pass
