#!/usr/bin/env python3
"""
Main BGP Security Analyzer

Coordinates all BGP attack detection and validation
"""

import sys
from pathlib import Path

# Add shared_data to path for registry access
shared_data_path = Path(__file__).parent.parent / "shared_blockchain_stack" / "shared_data"
sys.path.insert(0, str(shared_data_path.parent))

from .detectors.prefix_hijack_detector import PrefixHijackDetector
from .detectors.subprefix_detector import SubprefixHijackDetector
from .detectors.route_leak_detector import RouteLeakDetector
from .validators.rpki_validator import RPKIValidator
from .validators.irr_validator import IRRValidator

class BGPSecurityAnalyzer:
    """Main BGP security analysis coordinator"""
    
    def __init__(self, registry_path=None):
        if registry_path is None:
            registry_path = shared_data_path / "shared_registry"
        
        self.registry_path = Path(registry_path)
        
        # Initialize detectors
        self.prefix_hijack_detector = PrefixHijackDetector(self.registry_path)
        self.subprefix_detector = SubprefixHijackDetector(self.registry_path)
        self.route_leak_detector = RouteLeakDetector(self.registry_path)
        
        # Initialize validators
        self.rpki_validator = RPKIValidator(self.registry_path)
        self.irr_validator = IRRValidator(self.registry_path)
    
    def analyze_announcement(self, announcement):
        """Complete security analysis of BGP announcement"""
        
        results = {
            'announcement': announcement,
            'legitimate': True,
            'attacks_detected': [],
            'validation_results': {},
            'severity': 'low',
            'analysis_timestamp': self._get_timestamp()
        }
        
        # Step 1: RPKI/IRR Validation
        results['validation_results']['rpki'] = self.rpki_validator.validate(announcement)
        results['validation_results']['irr'] = self.irr_validator.validate(announcement)
        
        # Step 2: Attack Detection
        attack_detectors = [
            ('prefix_hijacking', self.prefix_hijack_detector),
            ('subprefix_hijacking', self.subprefix_detector),
            ('route_leak', self.route_leak_detector)
        ]
        
        for attack_type, detector in attack_detectors:
            try:
                attack = detector.detect(announcement)
                if attack:
                    results['attacks_detected'].append(attack)
                    results['legitimate'] = False
                    results['severity'] = self._update_severity(
                        results['severity'], 
                        attack.get('severity', 'medium')
                    )
            except Exception as e:
                print(f"Error in {attack_type} detection: {e}")
        
        return results
    
    def _update_severity(self, current, new):
        """Update severity level"""
        severity_levels = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        current_level = severity_levels.get(current, 1)
        new_level = severity_levels.get(new, 1)
        return new if new_level > current_level else current
    
    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
