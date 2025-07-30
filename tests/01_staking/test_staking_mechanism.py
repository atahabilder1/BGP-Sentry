#!/usr/bin/env python3
"""
Unit Tests: Staking Mechanism
Tests economic compensation logic
"""

import unittest
import sys
from pathlib import Path

# Add module paths
base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(base_path / "nodes/rpki_nodes/staking_amount_interface"))

class TestStakingMechanism(unittest.TestCase):
    """Test staking and economic compensation"""
    
    def setUp(self):
        """Set up test environment"""
        from staking_amountchecker import StakingAmountChecker
        self.checker = StakingAmountChecker()
    
    def test_compensation_tiers(self):
        """Test compensation tier calculation"""
        # High trust (80+) -> 0.04 ETH
        required = self.checker.calculate_required_stake_for_compensation(85)
        self.assertEqual(required, 0.04)
        
        # Medium trust (50-79) -> 0.2 ETH
        required = self.checker.calculate_required_stake_for_compensation(65)
        self.assertEqual(required, 0.2)
        
        # Low trust (30-49) -> 0.5 ETH  
        required = self.checker.calculate_required_stake_for_compensation(35)
        self.assertEqual(required, 0.5)
        
        # Very low trust (0-29) -> 1.0 ETH
        required = self.checker.calculate_required_stake_for_compensation(15)
        self.assertEqual(required, 1.0)
    
    def test_wallet_address_mapping(self):
        """Test AS to wallet address mapping"""
        # Test known mappings
        wallet = self.checker.get_wallet_address(2)
        self.assertIsNotNone(wallet, "AS02 should have wallet address")
        self.assertTrue(wallet.startswith('0x'), "Should be valid Ethereum address")
        
        wallet = self.checker.get_wallet_address(4)
        self.assertIsNotNone(wallet, "AS04 should have wallet address")
    
    def test_participation_eligibility(self):
        """Test participation eligibility logic"""
        # Test with known AS
        eligibility = self.checker.check_participation_eligibility(2)
        
        self.assertIsInstance(eligibility, dict)
        self.assertIn('can_participate', eligibility)
        self.assertIn('trust_score', eligibility)
        self.assertIn('current_stake', eligibility)
        self.assertIn('required_stake', eligibility)
        
        # Trust score should be reasonable
        self.assertGreaterEqual(eligibility['trust_score'], 0)
        self.assertLessEqual(eligibility['trust_score'], 100)
    
    def test_trust_score_integration(self):
        """Test integration with trust score system"""
        trust_score = self.checker.get_trust_score(2)
        self.assertIsInstance(trust_score, (int, float))
        self.assertGreaterEqual(trust_score, 0)
        self.assertLessEqual(trust_score, 100)
    
    def test_stake_amount_retrieval(self):
        """Test stake amount retrieval (real or mock)"""
        stake = self.checker.get_current_stake_amount(2)
        self.assertIsInstance(stake, (int, float))
        self.assertGreaterEqual(stake, 0)
    
    def test_compensation_logic(self):
        """Test economic compensation logic"""
        # Low trust should require higher stake
        low_trust_stake = self.checker.calculate_required_stake_for_compensation(20)
        high_trust_stake = self.checker.calculate_required_stake_for_compensation(90)
        
        self.assertGreater(low_trust_stake, high_trust_stake, 
                          "Lower trust should require higher stake")

if __name__ == '__main__':
    print("�� Running Staking Mechanism Tests...")
    unittest.main(verbosity=2)
