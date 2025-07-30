#!/usr/bin/env python3
"""
Unit Tests: System Initialization
Tests all components can be imported and initialized properly
"""

import unittest
import sys
import os
from pathlib import Path

# Add module paths
base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(base_path / "nodes/rpki_nodes/rpki_verification_interface"))
sys.path.insert(0, str(base_path / "nodes/rpki_nodes/bgp_attack_detection"))
sys.path.insert(0, str(base_path / "nodes/rpki_nodes/trust_score_interface"))
sys.path.insert(0, str(base_path / "nodes/rpki_nodes/staking_amount_interface"))
sys.path.insert(0, str(base_path / "nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils"))

class TestSystemInitialization(unittest.TestCase):
    """Test system component initialization"""
    
    def test_rpki_verification_import(self):
        """Test RPKI verification can be imported"""
        try:
            from verifier import is_as_verified, get_all_unverified_ases
            self.assertTrue(callable(is_as_verified))
            self.assertTrue(callable(get_all_unverified_ases))
        except ImportError as e:
            self.fail(f"RPKI verification import failed: {e}")
    
    def test_bgp_attack_detection_import(self):
        """Test BGP attack detection can be imported"""
        try:
            from attack_detector_fixed import BGPSecurityAnalyzer
            analyzer = BGPSecurityAnalyzer()
            self.assertIsNotNone(analyzer)
        except ImportError as e:
            self.fail(f"BGP attack detection import failed: {e}")
    
    def test_trust_engine_import(self):
        """Test trust engine interface can be imported"""
        try:
            from trust_engine_interface import TrustEngineInterface
            interface = TrustEngineInterface()
            self.assertIsNotNone(interface)
        except ImportError as e:
            self.fail(f"Trust engine import failed: {e}")
    
    def test_staking_checker_import(self):
        """Test staking checker can be imported"""
        try:
            from staking_amountchecker import StakingAmountChecker
            checker = StakingAmountChecker()
            self.assertIsNotNone(checker)
        except ImportError as e:
            self.fail(f"Staking checker import failed: {e}")
    
    def test_blockchain_interface_import(self):
        """Test blockchain interface can be imported"""
        try:
            from integrated_trust_manager import IntegratedTrustManager
            manager = IntegratedTrustManager()
            self.assertIsNotNone(manager)
        except ImportError as e:
            self.fail(f"Blockchain interface import failed: {e}")

if __name__ == '__main__':
    print("🧪 Running System Initialization Tests...")
    unittest.main(verbosity=2)
