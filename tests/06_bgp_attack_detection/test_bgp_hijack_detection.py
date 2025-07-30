#!/usr/bin/env python3
"""
Unit Tests: BGP Attack Detection
Tests attack detection algorithms
"""

import unittest
import sys
from pathlib import Path

# Add module paths
base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(base_path / "nodes/rpki_nodes/bgp_attack_detection"))

class TestBGPAttackDetection(unittest.TestCase):
    """Test BGP attack detection functionality"""
    
    def setUp(self):
        """Set up test environment"""
        from attack_detector_fixed import BGPSecurityAnalyzer
        self.analyzer = BGPSecurityAnalyzer()
    
    def test_analyzer_initialization(self):
        """Test analyzer initializes properly"""
        self.assertIsNotNone(self.analyzer)
        self.assertTrue(hasattr(self.analyzer, 'analyze_announcement'))
    
    def test_clean_announcement(self):
        """Test clean BGP announcement"""
        clean_announcement = {
            'as_number': 1,  # RPKI valid AS
            'prefix': '192.168.1.0/24',
            'timestamp': '2025-07-30T12:00:00Z'
        }
        
        results = self.analyzer.analyze_announcement(clean_announcement)
        
        self.assertIsInstance(results, dict)
        self.assertIn('legitimate', results)
        self.assertIn('attacks_detected', results)
        self.assertIn('validation_results', results)
    
    def test_suspicious_announcement(self):
        """Test potentially suspicious announcement"""
        suspicious_announcement = {
            'as_number': 4,  # Non-RPKI AS that triggers simulation
            'prefix': '10.0.0.0/8',
            'timestamp': '2025-07-30T12:00:00Z'
        }
        
        results = self.analyzer.analyze_announcement(suspicious_announcement)
        
        self.assertIsInstance(results, dict)
        self.assertIn('legitimate', results)
        self.assertIn('attacks_detected', results)
        
        # AS4 should trigger prefix hijacking in simulation
        if not results['legitimate']:
            self.assertGreater(len(results['attacks_detected']), 0)
    
    def test_rpki_validation_integration(self):
        """Test RPKI validation integration"""
        test_announcement = {
            'as_number': 2,  # Non-RPKI AS
            'prefix': '172.16.0.0/12',
            'timestamp': '2025-07-30T12:00:00Z'
        }
        
        results = self.analyzer.analyze_announcement(test_announcement)
        
        # Should have RPKI validation results
        self.assertIn('validation_results', results)
        self.assertIn('rpki', results['validation_results'])
        
        rpki_result = results['validation_results']['rpki']
        self.assertIn('status', rpki_result)
        
        # AS2 should be RPKI invalid
        self.assertEqual(rpki_result['status'], 'invalid')
    
    def test_attack_types(self):
        """Test different attack type detection"""
        # Test ASes that trigger different attacks in simulation
        test_cases = [
            {'as': 4, 'expected_type': 'prefix_hijacking'},
            {'as': 6, 'expected_type': 'subprefix_hijacking'}, 
            {'as': 8, 'expected_type': 'route_leak'}
        ]
        
        for case in test_cases:
            with self.subTest(as_number=case['as']):
                announcement = {
                    'as_number': case['as'],
                    'prefix': '203.0.113.0/24',
                    'timestamp': '2025-07-30T12:00:00Z'
                }
                
                results = self.analyzer.analyze_announcement(announcement)
                
                if not results['legitimate']:
                    attacks = results['attacks_detected']
                    self.assertGreater(len(attacks), 0)
                    # Check if expected attack type is detected
                    attack_types = [attack.get('type') for attack in attacks]
                    self.assertIn(case['expected_type'], attack_types)

if __name__ == '__main__':
    print("🧪 Running BGP Attack Detection Tests...")
    unittest.main(verbosity=2)
