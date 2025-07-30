#!/usr/bin/env python3
"""
Main BGP Security Analyzer - Fixed Version
Coordinates all BGP attack detection and validation
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add necessary paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'detectors'))
sys.path.insert(0, os.path.join(current_dir, 'validators'))

# Add RPKI verification interface path
rpki_interface_path = os.path.join(current_dir, "..", "rpki_verification_interface")
sys.path.insert(0, rpki_interface_path)

# Add trust engine interface path  
trust_interface_path = os.path.join(current_dir, "..", "trust_score_interface")
sys.path.insert(0, trust_interface_path)

class BGPSecurityAnalyzer:
    """Main BGP security analysis coordinator"""
    
    def __init__(self, registry_path=None):
        print("Initializing BGP Security Analyzer...")
        
        # Set registry path
        if registry_path is None:
            registry_path = os.path.join(
                current_dir, "..", "shared_blockchain_stack", 
                "shared_data", "shared_registry"
            )
        
        self.registry_path = Path(registry_path)
        
        # Initialize detectors with stub implementations for now
        self.detectors = {
            'prefix_hijacking': self._create_prefix_detector(),
            'subprefix_hijacking': self._create_subprefix_detector(),
            'route_leak': self._create_route_leak_detector()
        }
        
        # Initialize validators
        self.validators = {
            'rpki': self._create_rpki_validator(),
            'irr': self._create_irr_validator()
        }
        
        # Initialize trust engine interface
        self.trust_engine = self._initialize_trust_engine()
        
        print("✅ BGP Security Analyzer initialized")
    
    def _create_prefix_detector(self):
        """Create prefix hijack detector"""
        class PrefixHijackDetector:
            def detect(self, announcement):
                # Simulate prefix hijack detection
                as_number = announcement.get('as_number')
                if as_number and as_number % 4 == 0:  # Simple simulation
                    return {
                        'type': 'prefix_hijacking',
                        'severity': 'high',
                        'confidence': 0.9,
                        'description': f'Potential prefix hijack by AS{as_number}'
                    }
                return None
        return PrefixHijackDetector()
    
    def _create_subprefix_detector(self):
        """Create subprefix hijack detector"""
        class SubprefixHijackDetector:
            def detect(self, announcement):
                # Simulate subprefix hijack detection
                as_number = announcement.get('as_number')
                if as_number and as_number % 6 == 0:  # Simple simulation
                    return {
                        'type': 'subprefix_hijacking',
                        'severity': 'medium',
                        'confidence': 0.8,
                        'description': f'Potential subprefix hijack by AS{as_number}'
                    }
                return None
        return SubprefixHijackDetector()
    
    def _create_route_leak_detector(self):
        """Create route leak detector"""
        class RouteLeakDetector:
            def detect(self, announcement):
                # Simulate route leak detection
                as_number = announcement.get('as_number')
                if as_number and as_number % 8 == 0:  # Simple simulation
                    return {
                        'type': 'route_leak',
                        'severity': 'low',
                        'confidence': 0.7,
                        'description': f'Potential route leak by AS{as_number}'
                    }
                return None
        return RouteLeakDetector()
    
    def _create_rpki_validator(self):
        """Create RPKI validator using working RPKI verification"""
        class RPKIValidator:
            def __init__(self):
                try:
                    # Import working RPKI verification
                    from verifier import is_as_verified
                    self.is_as_verified = is_as_verified
                    self.available = True
                except ImportError:
                    print("⚠️  RPKI verification not available")
                    self.available = False
            
            def validate(self, announcement):
                if not self.available:
                    return {'valid': False, 'status': 'unavailable', 'message': 'RPKI validator unavailable'}
                
                as_number = announcement.get('as_number')
                if as_number is None:
                    return {'valid': False, 'status': 'invalid', 'message': 'No AS number provided'}
                
                try:
                    is_valid = self.is_as_verified(as_number)
                    return {
                        'valid': is_valid,
                        'status': 'valid' if is_valid else 'invalid',
                        'message': f'AS{as_number} RPKI status: {"Valid" if is_valid else "Invalid"}'
                    }
                except Exception as e:
                    return {'valid': False, 'status': 'error', 'message': f'RPKI validation error: {e}'}
        
        return RPKIValidator()
    
    def _create_irr_validator(self):
        """Create IRR validator (placeholder)"""
        class IRRValidator:
            def validate(self, announcement):
                # Placeholder IRR validation
                return {
                    'valid': True,
                    'status': 'valid',
                    'message': 'IRR validation placeholder'
                }
        return IRRValidator()
    
    def _initialize_trust_engine(self):
        """Initialize trust engine interface"""
        try:
            from trust_engine_interface import TrustEngineInterface
            return TrustEngineInterface()
        except ImportError:
            print("⚠️  Trust engine interface not available")
            return None
    
    def analyze_announcement(self, announcement):
        """Complete security analysis of BGP announcement"""
        
        print(f"🔍 Analyzing BGP announcement from AS{announcement.get('as_number', 'Unknown')}")
        
        results = {
            'announcement': announcement,
            'legitimate': True,
            'attacks_detected': [],
            'validation_results': {},
            'severity': 'low',
            'analysis_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Step 1: RPKI/IRR Validation
        results['validation_results']['rpki'] = self.validators['rpki'].validate(announcement)
        results['validation_results']['irr'] = self.validators['irr'].validate(announcement)
        
        # Step 2: Attack Detection
        for attack_type, detector in self.detectors.items():
            try:
                attack = detector.detect(announcement)
                if attack:
                    results['attacks_detected'].append(attack)
                    results['legitimate'] = False
                    results['severity'] = self._update_severity(
                        results['severity'], 
                        attack.get('severity', 'medium')
                    )
                    
                    # Report to trust engine
                    self._report_to_trust_engine(announcement.get('as_number'), attack_type)
                    
            except Exception as e:
                print(f"❌ Error in {attack_type} detection: {e}")
        
        return results
    
    def _report_to_trust_engine(self, as_number, attack_type):
        """Report detected attack to trust engine"""
        if self.trust_engine and as_number:
            try:
                print(f"📨 Reporting {attack_type} by AS{as_number} to trust engine")
                self.trust_engine.coordinator.process_violation(as_number, attack_type)
            except Exception as e:
                print(f"❌ Failed to report to trust engine: {e}")
    
    def _update_severity(self, current, new):
        """Update severity level"""
        severity_levels = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        current_level = severity_levels.get(current, 1)
        new_level = severity_levels.get(new, 1)
        return new if new_level > current_level else current

# Make it available for import
BGPSecurityAnalyzer = BGPSecurityAnalyzer
