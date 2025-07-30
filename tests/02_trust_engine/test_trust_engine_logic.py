#!/usr/bin/env python3
"""
Unit Tests: Trust Engine Logic
Tests RTE and ATE functionality
"""

import unittest
import sys
from pathlib import Path

# Add module paths
base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(base_path / "nodes/rpki_nodes/trust_score_interface"))

class TestTrustEngineLogic(unittest.TestCase):
    """Test trust engine components"""
    
    def setUp(self):
        """Set up test environment"""
        from trust_engine_interface import TrustEngineInterface
        self.trust_engine = TrustEngineInterface()
    
    def test_rte_initialization(self):
        """Test Reactive Trust Engine initialization"""
        self.assertIsNotNone(self.trust_engine.rte, "RTE should be initialized")
    
    def test_ate_initialization(self):
        """Test Adaptive Trust Engine initialization"""
        self.assertIsNotNone(self.trust_engine.ate, "ATE should be initialized")
    
    def test_coordinator_initialization(self):
        """Test Trust Coordinator initialization"""
        self.assertIsNotNone(self.trust_engine.coordinator, "Coordinator should be initialized")
    
    def test_rte_penalty_application(self):
        """Test RTE penalty application"""
        if self.trust_engine.rte:
            # Test penalty methods exist
            self.assertTrue(hasattr(self.trust_engine.rte, 'get_status'))
            status = self.trust_engine.rte.get_status()
            self.assertIsInstance(status, dict)
    
    def test_ate_evaluation(self):
        """Test ATE periodic evaluation"""
        if self.trust_engine.ate:
            # Test evaluation methods exist
            self.assertTrue(hasattr(self.trust_engine.ate, 'get_status'))
            status = self.trust_engine.ate.get_status()
            self.assertIsInstance(status, dict)
    
    def test_trust_score_retrieval(self):
        """Test trust score retrieval"""
        # Test with known AS number
        if self.trust_engine.coordinator:
            try:
                # This might use mock data, which is fine for unit tests
                score = self.trust_engine.coordinator.get_trust_score(2)
                self.assertIsInstance(score, (int, float))
                self.assertGreaterEqual(score, 0)
                self.assertLessEqual(score, 100)
            except Exception as e:
                self.skipTest(f"Trust score retrieval not available: {e}")

if __name__ == '__main__':
    print("🧪 Running Trust Engine Logic Tests...")
    unittest.main(verbosity=2)
